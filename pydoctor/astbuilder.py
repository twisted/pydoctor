"""Convert ASTs into L{pydoctor.model.Documentable} instances."""
from __future__ import annotations

import ast
import contextlib
import sys

from functools import partial
from inspect import Parameter, Signature
from pathlib import Path
from typing import (
    Any, Callable, Collection, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple,
    Type, TypeVar, Union, Set, cast
)

from pydoctor import epydoc2stan, model, node2stan, extensions, linker
from pydoctor.epydoc.markup._pyval_repr import colorize_inline_pyval
from pydoctor.astutils import (is_none_literal, is_typing_annotation, is_using_annotations, is_using_typing_final, node2dottedname, node2fullname, 
                               is__name__equals__main__, unstring_annotation, upgrade_annotation, iterassign, extract_docstring_linenum, infer_type, get_parents,
                               get_docstring_node, get_assign_docstring_node, unparse, NodeVisitor, Parentage, Str)


def parseFile(path: Path) -> ast.Module:
    """Parse the contents of a Python source file."""
    with open(path, 'rb') as f:
        src = f.read() + b'\n'
    return _parse(src, filename=str(path))

if sys.version_info >= (3,8):
    _parse = partial(ast.parse, type_comments=True)
else:
    _parse = ast.parse

def _maybeAttribute(cls: model.Class, name: str) -> bool:
    """Check whether a name is a potential attribute of the given class.
    This is used to prevent an assignment that wraps a method from
    creating an attribute that would overwrite or shadow that method.

    @return: L{True} if the name does not exist or is an existing (possibly
        inherited) attribute, L{False} if this name defines something else than an L{Attribute}. 
    """
    obj = cls.find(name)
    return obj is None or isinstance(obj, model.Attribute)

class IgnoreAssignment(Exception):
    """
    A control flow exception meaning that the assignment should not be further proccessed.
    """

def _handleAliasing(
        ctx: model.CanContainImportsDocumentable,
        target: str,
        expr: Optional[ast.expr]
        ) -> bool:
    """If the given expression is a name assigned to a target that is not yet
    in use, create an alias.
    @return: L{True} iff an alias was created.
    """
    if target in ctx.contents:
        return False
    full_name = node2fullname(expr, ctx)
    if full_name is None:
        return False
    ctx._localNameToFullName_map[target] = full_name
    return True


_CONTROL_FLOW_BLOCKS:Tuple[Type[ast.stmt],...] = (ast.If, ast.While, ast.For, ast.Try, 
                                            ast.AsyncFor, ast.With, ast.AsyncWith)
"""
AST types that introduces a new control flow block, potentially conditionnal.
"""
if sys.version_info >= (3, 10):
    _CONTROL_FLOW_BLOCKS += (ast.Match,)
if sys.version_info >= (3, 11):
    _CONTROL_FLOW_BLOCKS += (ast.TryStar,)

def is_constant(obj: model.Attribute, 
                annotation:Optional[ast.expr], 
                value:Optional[ast.expr]) -> bool:
    """
    Detect if the given assignment is a constant. 

    For an assignment to be detected as constant, it should: 
        - have all-caps variable name or using L{typing.Final} annotation
        - not be overriden
        - not be defined in a conditionnal block or any other kind of control flow blocks
    
    @note: Must be called after setting obj.annotation to detect variables using Final.
    """
    if is_using_typing_final(annotation, obj):
        return True
    if not is_attribute_overridden(obj, value) and value:
        if not any(isinstance(n, _CONTROL_FLOW_BLOCKS) for n in get_parents(value)):
            return obj.name.isupper()
    return False

class TypeAliasVisitorExt(extensions.ModuleVisitorExt):
    """
    This visitor implements the handling of type aliases and type variables.
    """
    def _isTypeVariable(self, ob: model.Attribute) -> bool:
        if ob.value is not None:
            if isinstance(ob.value, ast.Call) and \
                node2fullname(ob.value.func, ob) in ('typing.TypeVar', 
                                                     'typing_extensions.TypeVar',
                                                     'typing.TypeVarTuple', 
                                                     'typing_extensions.TypeVarTuple'):
                return True
        return False
    
    def _isTypeAlias(self, ob: model.Attribute) -> bool:
        """
        Return C{True} if the Attribute is a type alias.
        """
        if ob.value is not None:
            if is_using_annotations(ob.annotation, ('typing.TypeAlias', 
                                                    'typing_extensions.TypeAlias'), ob):
                return True
            if is_typing_annotation(ob.value, ob.parent):
                return True
        return False

    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        current = self.visitor.builder.current
        for dottedname in iterassign(node): 
            if dottedname and len(dottedname)==1:
                attr = current.contents.get(dottedname[0])
                if attr is None:
                    return
                if not isinstance(attr, model.Attribute):
                    return
                if self._isTypeAlias(attr) is True:
                    attr.kind = model.DocumentableKind.TYPE_ALIAS
                    # unstring type aliases
                    attr.value = upgrade_annotation(unstring_annotation(
                        # this cast() is safe because _isTypeAlias() return True only if value is not None
                        cast(ast.expr, attr.value), attr, section='type alias'), attr, section='type alias')
                elif self._isTypeVariable(attr) is True:
                    # TODO: unstring bound argument of type variables
                    attr.kind = model.DocumentableKind.TYPE_VARIABLE
    
    visit_AnnAssign = visit_Assign

def is_attribute_overridden(obj: model.Attribute, new_value: Optional[ast.expr]) -> bool:
    """
    Detect if the optional C{new_value} expression override the one already stored in the L{Attribute.value} attribute.
    """
    return obj.value is not None and new_value is not None

def _extract_annotation_subscript(annotation: ast.Subscript) -> ast.AST:
    """
    Extract the "str, bytes" part from annotations like  "Union[str, bytes]".
    """
    ann_slice = annotation.slice
    if sys.version_info < (3,9) and isinstance(ann_slice, ast.Index):
        return ann_slice.value
    else:
        return ann_slice

def extract_final_subscript(annotation: ast.Subscript) -> ast.expr:
    """
    Extract the "str" part from annotations like  "Final[str]".

    @raises ValueError: If the "Final" annotation is not valid.
    """ 
    ann_slice = _extract_annotation_subscript(annotation)
    if isinstance(ann_slice, (ast.ExtSlice, ast.Slice, ast.Tuple)):
        raise ValueError("Annotation is invalid, it should not contain slices.")
    else:
        assert isinstance(ann_slice, ast.expr)
        return ann_slice

class ModuleVistor(NodeVisitor):

    def __init__(self, builder: 'ASTBuilder', module: model.Module):
        super().__init__()
        self.builder = builder
        self.system = builder.system
        self.module = module
        self._override_guard_state: Tuple[Optional[model.Documentable], Set[str]] = (None, set())
    
    @contextlib.contextmanager
    def override_guard(self) -> Iterator[None]:
        """
        Returns a context manager that will make the builder ignore any new 
        assigments to existing names within the same context.  Currently used to visit C{If.orelse} and C{Try.handlers}.
        
        @note: The list of existing names is generated at the moment of
            calling the function, such that new names defined inside these blocks follows the usual override rules.
        """
        ctx = self.builder.current
        while not isinstance(ctx, model.CanContainImportsDocumentable):
            assert ctx.parent
            ctx = ctx.parent
        ignore_override_init = self._override_guard_state
        # we list names only once to ignore new names added inside the block,
        # they should be overriden as usual.
        self._override_guard_state = (ctx, set(ctx.localNames()))
        yield
        self._override_guard_state = ignore_override_init
    
    def _ignore_name(self, ob: model.Documentable, name:str) -> bool:
        """
        Should this C{name} be ignored because it matches 
        the override guard in the context of C{ob}?
        """
        ctx, names = self._override_guard_state
        return ctx is ob and name in names

    def _infer_attr_annotations(self, scope: model.Documentable) -> None:
        # Infer annotation when leaving scope so explicit
        # annotations take precedence.
        for attrib in scope.contents.values():
            if not isinstance(attrib, model.Attribute):
                continue
            # If this attribute has not explicit annotation, 
            # infer its type from it's ast expression.
            if attrib.annotation is None and attrib.value is not None:
                # do not override explicit annotation
                attrib.annotation = infer_type(attrib.value)
    
    def _tweak_constants_annotations(self, scope: model.Documentable) -> None:
        # tweak constants annotations when we leave the scope so we can still
        # check whether the annotation uses Final while we're visiting other nodes.
        for attrib in scope.contents.values():
            if not isinstance(attrib, model.Attribute) or attrib.kind is not model.DocumentableKind.CONSTANT :
                continue
            self._tweak_constant_annotation(attrib)

    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Compare):
            if is__name__equals__main__(node.test):
                # skip if __name__ == '__main__': blocks since
                # whatever is declared in them cannot be imported
                # and thus is not part of the API
                raise self.SkipChildren()
    
    def depart_If(self, node: ast.If) -> None:
        # At this point the body of the If node has already been visited
        # Visit the 'orelse' block of the If node, with override guard
        with self.override_guard():
            for n in node.orelse:
                self.walkabout(n)
    
    def depart_Try(self, node: ast.Try) -> None:
        # At this point the body of the Try node has already been visited
        # Visit the 'orelse' and 'finalbody' blocks of the Try node.
        
        for n in node.orelse:
            self.walkabout(n)
        for n in node.finalbody:
            self.walkabout(n)
        
        # Visit the handlers with override guard 
        with self.override_guard():
            for h in node.handlers:
                for n in h.body:
                    self.walkabout(n)

    def visit_Module(self, node: ast.Module) -> None:
        assert self.module.docstring is None
        Parentage().visit(node)

        self.builder.push(self.module, 0)
        doc_node = get_docstring_node(node)
        if doc_node is not None:
            self.module.setDocstring(doc_node)
            epydoc2stan.extract_fields(self.module)

    def depart_Module(self, node: ast.Module) -> None:
        self._tweak_constants_annotations(self.builder.current)
        self._infer_attr_annotations(self.builder.current)
        self.builder.pop(self.module)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Ignore classes within functions.
        parent = self.builder.current
        if isinstance(parent, model.Function):
            raise self.SkipNode()
        # Ignore in override guard
        if self._ignore_name(parent, node.name):
            raise self.IgnoreNode()

        rawbases = []
        initialbases = []
        initialbaseobjects = []

        for base_node in node.bases:
            # This handles generics in MRO, by extracting the first
            # subscript value::
            #   class Visitor(MyGeneric[T]):...
            # 'MyGeneric' will be added to rawbases instead 
            # of 'MyGeneric[T]' which cannot resolve to anything.
            name_node = base_node
            if isinstance(base_node, ast.Subscript):
                name_node = base_node.value
            
            str_base = '.'.join(node2dottedname(name_node) or \
                # Fallback on unparse() if the expression is unknown by node2dottedname().
                [unparse(base_node).strip()]) 
                
            # Store the base as string and as ast.expr in rawbases list.
            rawbases += [(str_base, base_node)]
            
            # Try to resolve the base, put None if could not resolve it,
            # if we can't resolve it now, it most likely mean that there are
            # import cycles (maybe in TYPE_CHECKING blocks). 
            # None bases will be re-resolved in post-processing.
            expandbase = parent.expandName(str_base)
            baseobj = self.system.objForFullName(expandbase)
            
            if not isinstance(baseobj, model.Class):
                baseobj = None
                
            initialbases.append(expandbase)
            initialbaseobjects.append(baseobj)

        lineno = node.lineno
        if node.decorator_list:
            lineno = node.decorator_list[0].lineno

        cls: model.Class = self.builder.pushClass(node.name, lineno)
        cls.decorators = []
        cls.rawbases = rawbases
        cls._initialbaseobjects = initialbaseobjects
        cls._initialbases = initialbases

        doc_node = get_docstring_node(node)
        if doc_node is not None:
            cls.setDocstring(doc_node)
            epydoc2stan.extract_fields(cls)

        if node.decorator_list:
            
            cls.raw_decorators = node.decorator_list
        
            for decnode in node.decorator_list:
                args: Optional[Sequence[ast.expr]]
                if isinstance(decnode, ast.Call):
                    base = node2fullname(decnode.func, parent)
                    args = decnode.args
                else:
                    base = node2fullname(decnode, parent)
                    args = None
                if base is None:  # pragma: no cover
                    # There are expressions for which node2data() returns None,
                    # but I cannot find any that don't lead to a SyntaxError
                    # when used in a decorator.
                    cls.report("cannot make sense of class decorator")
                else:
                    cls.decorators.append((base, args))

            
        # We're not resolving the subclasses at this point yet because all 
        # modules might not have been processed, and since subclasses are only used in the presentation,
        # it's better to resolve them in the post-processing instead.


    def depart_ClassDef(self, node: ast.ClassDef) -> None:
        self._tweak_constants_annotations(self.builder.current)
        self._infer_attr_annotations(self.builder.current)
        self.builder.popClass()


    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        ctx = self.builder.current
        if not isinstance(ctx, model.CanContainImportsDocumentable):
            # processing import statement in odd context
            return

        modname = node.module
        level = node.level
        if level:
            # Relative import.
            parent: Optional[model.Documentable] = ctx.parentMod
            if isinstance(ctx.module, model.Package):
                level -= 1
            for _ in range(level):
                if parent is None:
                    break
                parent = parent.parent
            if parent is None:
                assert ctx.parentMod is not None
                ctx.parentMod.report(
                    "relative import level (%d) too high" % node.level,
                    lineno_offset=node.lineno
                    )
                return
            if modname is None:
                modname = parent.fullName()
            else:
                modname = f'{parent.fullName()}.{modname}'
        else:
            # The module name can only be omitted on relative imports.
            assert modname is not None

        if node.names[0].name == '*':
            self._importAll(modname)
        else:
            self._importNames(modname, node.names)

    def _importAll(self, modname: str) -> None:
        """Handle a C{from <modname> import *} statement."""

        current = self.builder.current

        mod = self.system.getProcessedModule(modname)
        if mod is None:
            # We don't have any information about the module, so we don't know
            # what names to import.
            current.report(f"import * from unknown {modname}", thresh=1)
            return

        current.report(f"import * from {modname}", thresh=1)

        # Get names to import: use __all__ if available, otherwise take all
        # names that are not private.
        names = mod.all
        if names is None:
            names = [ name for name in mod.localNames() 
                     if not name.startswith('_') ]

        # Fetch names to export.
        exports = self._getCurrentModuleExports()

        # Add imported names to our module namespace.
        assert isinstance(current, model.CanContainImportsDocumentable)
        _localNameToFullName = current._localNameToFullName_map
        expandName = mod.expandName
        for name in names:

            # # Ignore in override guard
            if self._ignore_name(current, name):
                continue

            if self._handleReExport(exports, name, name, mod) is True:
                continue

            _localNameToFullName[name] = expandName(name)

    def _getCurrentModuleExports(self) -> Collection[str]:
        # Fetch names to export.
        current = self.builder.current
        if isinstance(current, model.Module):
            exports = current.all
            if exports is None:
                exports = []
        else:
            # Don't export names imported inside classes or functions.
            exports = []
        return exports

    def _handleReExport(self, curr_mod_exports:Collection[str], 
                        origin_name:str, as_name:str,
                        origin_module:model.Module) -> bool:
        """
        Move re-exported objects into current module.

        @returns: True if the imported name has been sucessfully re-exported.
        """
        # Move re-exported objects into current module.
        current = self.builder.current
        modname = origin_module.fullName()
        if as_name in curr_mod_exports:
            # In case of duplicates names, we can't rely on resolveName,
            # So we use content.get first to resolve non-alias names. 
            ob = origin_module.contents.get(origin_name) or origin_module.resolveName(origin_name)
            if ob is None:
                current.report("cannot resolve re-exported name :"
                                        f'{modname}.{origin_name}', thresh=1)
            else:
                if origin_module.all is None or origin_name not in origin_module.all:
                    self.system.msg(
                        "astbuilder",
                        "moving %r into %r" % (ob.fullName(), current.fullName())
                        )
                    # Must be a Module since the exports is set to an empty list if it's not.
                    assert isinstance(current, model.Module)
                    ob.reparent(current, as_name)
                    return True
        return False

    def _importNames(self, modname: str, names: Iterable[ast.alias]) -> None:
        """Handle a C{from <modname> import <names>} statement."""

        # Process the module we're importing from.
        mod = self.system.getProcessedModule(modname)

        # Fetch names to export.
        exports = self._getCurrentModuleExports()

        current = self.builder.current
        assert isinstance(current, model.CanContainImportsDocumentable)
        _localNameToFullName = current._localNameToFullName_map
        for al in names:
            orgname, asname = al.name, al.asname
            if asname is None:
                asname = orgname
            
            # Ignore in override guard
            if self._ignore_name(current, asname):
                continue
            
            # If we're importing from a package, make sure imported modules
            # are processed (getProcessedModule() ignores non-modules).
            if isinstance(mod, model.Package):
                self.system.getProcessedModule(f'{modname}.{orgname}')
            if mod is not None and self._handleReExport(exports, orgname, asname, mod) is True:
                continue

            _localNameToFullName[asname] = f'{modname}.{orgname}'

    def visit_Import(self, node: ast.Import) -> None:
        """Process an import statement.

        The grammar for the statement is roughly:

        mod_as := DOTTEDNAME ['as' NAME]
        import_stmt := 'import' mod_as (',' mod_as)*

        and this is translated into a node which is an instance of Import wih
        an attribute 'names', which is in turn a list of 2-tuples
        (dotted_name, as_name) where as_name is None if there was no 'as foo'
        part of the statement.
        """
        current = self.builder.current
        if not isinstance(current, model.CanContainImportsDocumentable):
            # processing import statement in odd context
            return
        _localNameToFullName = current._localNameToFullName_map
        
        for al in node.names:
            targetname, asname = al.name, al.asname
            if asname is None:
                # we're keeping track of all defined names
                asname = targetname = targetname.split('.')[0]
            # Ignore in override guard
            if self._ignore_name(current, asname):
                continue
            _localNameToFullName[asname] = targetname

    def _handleOldSchoolMethodDecoration(self, target: str, expr: Optional[ast.expr]) -> bool:
        if not isinstance(expr, ast.Call):
            return False
        func = expr.func
        if not isinstance(func, ast.Name):
            return False
        func_name = func.id
        args = expr.args
        if len(args) != 1:
            return False
        arg, = args
        if not isinstance(arg, ast.Name):
            return False
        if target == arg.id and func_name in ['staticmethod', 'classmethod']:
            target_obj = self.builder.current.contents.get(target)
            if isinstance(target_obj, model.Function):

                # _handleOldSchoolMethodDecoration must only be called in a class scope.
                assert target_obj.kind is model.DocumentableKind.METHOD

                if func_name == 'staticmethod':
                    target_obj.kind = model.DocumentableKind.STATIC_METHOD
                elif func_name == 'classmethod':
                    target_obj.kind = model.DocumentableKind.CLASS_METHOD
                return True
        return False

    @classmethod
    def _handleConstant(cls, obj:model.Attribute, 
                             annotation:Optional[ast.expr], 
                             value:Optional[ast.expr],
                             lineno:int, 
                             defaultKind:model.DocumentableKind) -> None:
        if is_constant(obj, annotation=annotation, value=value):
            obj.kind = model.DocumentableKind.CONSTANT
            # do not call tweak annotation just yet...
        elif obj.kind is model.DocumentableKind.CONSTANT:
            # reset to the default kind only for attributes that were heuristically
            # declared as constants
            if not is_using_typing_final(obj.annotation, obj):
                obj.kind = defaultKind
    
    @staticmethod
    def _tweak_constant_annotation(obj: model.Attribute) -> None:
        # Display variables annotated with Final with the real type instead.
        annotation = obj.annotation
        if is_using_typing_final(annotation, obj):
            if isinstance(annotation, ast.Subscript):
                try:
                    annotation = extract_final_subscript(annotation)
                except ValueError as e:
                    obj.report(str(e), section='ast', lineno_offset=annotation.lineno-obj.linenumber)
                    obj.annotation = infer_type(obj.value) if obj.value else None
                else:
                    # Will not display as "Final[str]" but rather only "str"
                    obj.annotation = annotation
            else:
                # Just plain "Final" annotation.
                # Simply ignore it because it's duplication of information.
                obj.annotation = infer_type(obj.value) if obj.value else None

    @staticmethod
    def _setAttributeAnnotation(obj: model.Attribute, 
                                annotation: Optional[ast.expr],) -> None:
        if annotation is not None:
            # TODO: What to do when an attribute has several explicit annotations?
            # (mypy reports a warning in these kind of cases)
            obj.annotation = annotation

    @staticmethod
    def _storeAttrValue(obj:model.Attribute, new_value:Optional[ast.expr], 
                        augassign:Optional[ast.operator]=None) -> None:
        if new_value:
            if augassign: 
                if obj.value:
                    # We're storing the value of augmented assignemnt value as binop for the sake 
                    # of correctness, but we're not doing anything special with it at the
                    # moment, nonethless this could be useful for future developments.
                    # We don't bother reporting warnings, pydoctor is not a checker.
                    obj.value = ast.BinOp(left=obj.value, op=augassign, right=new_value)
            else:
                obj.value = new_value
    

    def _handleModuleVar(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int,
            augassign:Optional[ast.operator],
            ) -> None:
        if target in MODULE_VARIABLES_META_PARSERS:
            # This is metadata, not a variable that needs to be documented,
            # and therefore doesn't need an Attribute instance.
            raise IgnoreAssignment()
        parent = self.builder.current
        obj = parent.contents.get(target)
        if obj is None:
            if augassign:
                return
            obj = self.builder.addAttribute(name=target, 
                                            kind=model.DocumentableKind.VARIABLE, 
                                            parent=parent, 
                                            lineno=lineno)
        
        # If it's not an attribute it means that the name is already denifed as function/class 
        # probably meaning that this attribute is a bound callable. 
        #
        #   def func(value, stock) -> int:...
        #   var = 2
        #   func = partial(func, value=var)
        #
        # We don't know how to handle this,
        # so we ignore it to document the original object. This means that we might document arguments 
        # that are in reality not existing because they have values in a partial() call for instance.

        if not isinstance(obj, model.Attribute):
            raise IgnoreAssignment()
        
        self._setAttributeAnnotation(obj, annotation)
        
        obj.setLineNumber(lineno)
        
        self._handleConstant(obj, annotation, expr, lineno, 
                                  model.DocumentableKind.VARIABLE)
        self._storeAttrValue(obj, expr, augassign)

    def _handleAssignmentInModule(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int,
            augassign:Optional[ast.operator],
            ) -> None:
        module = self.builder.current
        assert isinstance(module, model.Module)
        if not _handleAliasing(module, target, expr):
            self._handleModuleVar(target, annotation, expr, lineno, augassign=augassign)
        else:
            raise IgnoreAssignment()

    def _handleClassVar(self,
            name: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int,
            augassign:Optional[ast.operator],
            ) -> None:
        
        cls = self.builder.current
        assert isinstance(cls, model.Class)
        if not _maybeAttribute(cls, name):
            raise IgnoreAssignment()

        # Class variables can only be Attribute, so it's OK to cast
        obj = cast(Optional[model.Attribute], cls.contents.get(name))

        if obj is None:
            if augassign:
                return
            obj = self.builder.addAttribute(name=name, kind=None, parent=cls, lineno=lineno)

        if obj.kind is None:
            obj.kind = model.DocumentableKind.CLASS_VARIABLE

        self._setAttributeAnnotation(obj, annotation)
        
        obj.setLineNumber(lineno)

        self._handleConstant(obj, annotation, expr, lineno, 
                                  model.DocumentableKind.CLASS_VARIABLE)
        self._storeAttrValue(obj, expr, augassign)

       
    def _handleInstanceVar(self,
            name: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        if not (cls:=self._getClassFromMethodContext()):
            raise IgnoreAssignment()
        if not _maybeAttribute(cls, name):
            raise IgnoreAssignment()
        if self._ignore_name(cls, name):
            raise IgnoreAssignment()

        # Class variables can only be Attribute, so it's OK to cast because we used _maybeAttribute() above.
        obj = cast(Optional[model.Attribute], cls.contents.get(name))
        if obj is None:
            obj = self.builder.addAttribute(name=name, kind=None, parent=cls, lineno=lineno)

        self._setAttributeAnnotation(obj, annotation)

        obj.setLineNumber(lineno)
        # undonditionnaly set the kind to ivar
        obj.kind = model.DocumentableKind.INSTANCE_VARIABLE
        self._storeAttrValue(obj, expr)

    def _handleAssignmentInClass(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int,
            augassign:Optional[ast.operator],
            ) -> None:
        cls = self.builder.current
        assert isinstance(cls, model.Class)
        if not _handleAliasing(cls, target, expr):
            self._handleClassVar(target, annotation, expr, lineno, augassign=augassign)
        else:
            raise IgnoreAssignment()

    def _handleDocstringUpdate(self,
            targetNode: ast.expr,
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        def warn(msg: str) -> None:
            module = self.builder.currentMod
            assert module is not None
            module.report(msg, section='ast', lineno_offset=lineno)

        # Ignore docstring updates in functions.
        scope = self.builder.current
        if isinstance(scope, model.Function):
            return

        # Figure out target object.
        full_name = node2fullname(targetNode, scope)
        if full_name is None:
            warn("Unable to figure out target for __doc__ assignment")
            # Don't return yet: we might have to warn about the value too.
            obj = None
        else:
            obj = self.system.objForFullName(full_name)
            if obj is None:
                warn("Unable to figure out target for __doc__ assignment: "
                     "computed full name not found: " + full_name)

        # Determine docstring value.
        try:
            if expr is None:
                # The expr is None for detupling assignments, which can
                # be described as "too complex".
                raise ValueError()
            docstring: object = ast.literal_eval(expr)
        except ValueError:
            warn("Unable to figure out value for __doc__ assignment, "
                 "maybe too complex")
            return
        if not isinstance(docstring, str):
            warn("Ignoring value assigned to __doc__: not a string")
            return

        if obj is not None:
            obj._setDocstringValue(docstring, expr.lineno)
            # TODO: It might be better to not perform docstring parsing until
            #       we have the final docstrings for all objects.
            obj.parsed_docstring = None

    def _handleAssignment(self,
            targetNode: ast.expr,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int,
            augassign:Optional[ast.operator]=None,
            ) -> None:
        """
        @raises IgnoreAssignment: If the assignemnt should not be further processed.
        """
        if isinstance(targetNode, ast.Name):
            target = targetNode.id
            scope = self.builder.current
            if self._ignore_name(scope, target):
                raise IgnoreAssignment()
            if isinstance(scope, model.Module):
                self._handleAssignmentInModule(target, annotation, expr, lineno, augassign=augassign)
            elif isinstance(scope, model.Class):
                if augassign or not self._handleOldSchoolMethodDecoration(target, expr):
                    self._handleAssignmentInClass(target, annotation, expr, lineno, augassign=augassign)
        elif isinstance(targetNode, ast.Attribute) and not augassign:
            value = targetNode.value
            if targetNode.attr == '__doc__':
                self._handleDocstringUpdate(value, expr, lineno)
                raise IgnoreAssignment()
            elif isinstance(value, ast.Name) and value.id == 'self':
                self._handleInstanceVar(targetNode.attr, annotation, expr, lineno)
        else:
            raise IgnoreAssignment()

    def visit_Assign(self, node: ast.Assign) -> None:
        lineno = node.lineno
        expr = node.value

        type_comment: Optional[str] = getattr(node, 'type_comment', None)
        if type_comment is None:
            annotation = None
        else:
            annotation = upgrade_annotation(unstring_annotation(
                ast.Constant(type_comment, lineno=lineno), self.builder.current), self.builder.current)

        for target in node.targets:
            try:
                if isTupleAssignment:=isinstance(target, ast.Tuple):
                    # TODO: Only one level of nested tuple is taken into account...
                    # ideally we would extract al the names declared in the lhs, not
                    # only the first level ones.
                    for elem in target.elts:
                        # Note: We skip type and aliasing analysis for this case,
                        #       but we do record line numbers.
                        self._handleAssignment(elem, None, None, lineno)
                else:
                    self._handleAssignment(target, annotation, expr, lineno)
            except IgnoreAssignment:
                continue
            else:
                if not isTupleAssignment:
                    self._handleInlineDocstrings(node, target)
                else:
                    for elem in cast(ast.Tuple, target).elts: # mypy is not as smart as pyright yet.
                        self._handleInlineDocstrings(node, elem)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        annotation = upgrade_annotation(unstring_annotation(
            node.annotation, self.builder.current), self.builder.current)
        try:
            self._handleAssignment(node.target, annotation, node.value, node.lineno)
        except IgnoreAssignment:
            return
        else:
            self._handleInlineDocstrings(node, node.target)

    def _getClassFromMethodContext(self) -> Optional[model.Class]:
        func = self.builder.current
        if not isinstance(func, model.Function):
            return None
        cls = func.parent
        if not isinstance(cls, model.Class):
            return None
        return cls
    
    def _contextualizeTarget(self, target:ast.expr) -> Tuple[model.Documentable, str]:
        """
        Find out the documentatble wich is the parent of the assignment's target as well as it's name. 

        @returns: Tuple C{parent, name}. 
        @raises ValueError: if the target does not bind a new variable.
        """
        dottedname = node2dottedname(target)
        if not dottedname or len(dottedname) > 2:
            raise ValueError('does not bind a new variable')
        parent: model.Documentable
        if len(dottedname) == 2 and dottedname[0] == 'self':
            # an instance variable.
            # TODO: This currently only works if the first argument of methods
            # is named 'self'.
            if (maybe_cls:=self._getClassFromMethodContext()) is None:
                raise ValueError('using self in unsupported context')
            dottedname = dottedname[1:]
            parent = maybe_cls
        elif len(dottedname) != 1:
            raise ValueError('does not bind a new variable')
        else:
            parent = self.builder.current
        return parent, dottedname[0]

    def _handleInlineDocstrings(self, assign:Union[ast.Assign, ast.AnnAssign], target:ast.expr) -> None:
        # Process the inline docstrings
        try:
            parent, name = self._contextualizeTarget(target)
        except ValueError:
            return
        
        docstring_node = get_assign_docstring_node(assign)
        if docstring_node:
            # fetch the target of the inline docstring
            attr = parent.contents.get(name)
            if attr:
                attr.setDocstring(docstring_node)
    
    def visit_AugAssign(self, node:ast.AugAssign) -> None:
        try:
            self._handleAssignment(node.target, None, node.value, 
                                node.lineno, augassign=node.op)
        except IgnoreAssignment:
            pass

    
    def visit_Expr(self, node: ast.Expr) -> None:
        # Visit's ast.Expr.value with the visitor, used by extensions to visit top-level calls.
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handleFunctionDef(node, is_async=True)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handleFunctionDef(node, is_async=False)

    def _handleFunctionDef(self,
            node: Union[ast.AsyncFunctionDef, ast.FunctionDef],
            is_async: bool
            ) -> None:
        # Ignore inner functions.
        parent = self.builder.current
        if isinstance(parent, model.Function):
            raise self.SkipNode()
        # Ignore in override guard
        if self._ignore_name(parent, node.name):
            raise self.IgnoreNode()

        lineno = node.lineno

        # setting linenumber from the start of the decorations
        if node.decorator_list:
            lineno = node.decorator_list[0].lineno

        # extracting docstring
        doc_node = get_docstring_node(node)
        func_name = node.name

        # determine the function's kind
        is_property = False
        is_classmethod = False
        is_staticmethod = False
        is_overload_func = False
        if node.decorator_list:
            for d in node.decorator_list:
                if isinstance(d, ast.Call):
                    deco_name = node2dottedname(d.func)
                else:
                    deco_name = node2dottedname(d)
                if deco_name is None:
                    continue
                if isinstance(parent, model.Class):
                    if deco_name[-1].endswith('property') or deco_name[-1].endswith('Property'):
                        is_property = True
                    elif deco_name == ['classmethod']:
                        is_classmethod = True
                    elif deco_name == ['staticmethod']:
                        is_staticmethod = True
                    elif len(deco_name) >= 2 and deco_name[-1] in ('setter', 'deleter'):
                        # Rename the setter/deleter, so it doesn't replace
                        # the property object.
                        func_name = '.'.join(deco_name[-2:])
                # Determine if the function is decorated with overload
                if parent.expandName('.'.join(deco_name)) in ('typing.overload', 'typing_extensions.overload'):
                    is_overload_func = True

        if is_property:
            # handle property and skip child nodes.
            attr = self._handlePropertyDef(node, doc_node, lineno)
            if is_classmethod:
                attr.report(f'{attr.fullName()} is both property and classmethod')
            if is_staticmethod:
                attr.report(f'{attr.fullName()} is both property and staticmethod')
            raise self.SkipNode() # visitor extensions will still be called.

        # Check if it's a new func or exists with an overload
        existing_func = parent.contents.get(func_name)
        if isinstance(existing_func, model.Function) and existing_func.overloads:
            # If the existing function has a signature and this function is an
            # overload, then the overload came _after_ the primary function
            # which we do not allow. This also ensures that func will have
            # properties set for the primary function and not overloads.
            if existing_func.signature and is_overload_func:
                existing_func.report(f'{existing_func.fullName()} overload appeared after primary function', lineno_offset=lineno-existing_func.linenumber)
                raise self.IgnoreNode()
            # Do not recreate function object, just re-push it
            self.builder.push(existing_func, lineno)
            func = existing_func
        else:
            func = self.builder.pushFunction(func_name, lineno)

        func.is_async = is_async
        if doc_node is not None:
            # Docstring not allowed on overload
            if is_overload_func:
                docline = extract_docstring_linenum(doc_node)
                func.report(f'{func.fullName()} overload has docstring, unsupported', lineno_offset=docline-func.linenumber)
            else:
                func.setDocstring(doc_node)
        func.decorators = node.decorator_list
        if is_staticmethod:
            if is_classmethod:
                func.report(f'{func.fullName()} is both classmethod and staticmethod')
            else:
                func.kind = model.DocumentableKind.STATIC_METHOD
        elif is_classmethod:
            func.kind = model.DocumentableKind.CLASS_METHOD

        # Position-only arguments were introduced in Python 3.8.
        posonlyargs: Sequence[ast.arg] = getattr(node.args, 'posonlyargs', ())

        num_pos_args = len(posonlyargs) + len(node.args.args)
        defaults = node.args.defaults
        default_offset = num_pos_args - len(defaults)
        annotations = self._annotations_from_function(node)

        def get_default(index: int) -> Optional[ast.expr]:
            assert 0 <= index < num_pos_args, index
            index -= default_offset
            return None if index < 0 else defaults[index]

        parameters: List[Parameter] = []
        def add_arg(name: str, kind: Any, default: Optional[ast.expr]) -> None:
            default_val = Parameter.empty if default is None else _ValueFormatter(default, ctx=func)
                                                                               # this cast() is safe since we're checking if annotations.get(name) is None first
            annotation = Parameter.empty if annotations.get(name) is None else _AnnotationValueFormatter(cast(ast.expr, annotations[name]), ctx=func)
            parameters.append(Parameter(name, kind, default=default_val, annotation=annotation))

        for index, arg in enumerate(posonlyargs):
            add_arg(arg.arg, Parameter.POSITIONAL_ONLY, get_default(index))

        for index, arg in enumerate(node.args.args, start=len(posonlyargs)):
            add_arg(arg.arg, Parameter.POSITIONAL_OR_KEYWORD, get_default(index))

        vararg = node.args.vararg
        if vararg is not None:
            add_arg(vararg.arg, Parameter.VAR_POSITIONAL, None)

        assert len(node.args.kwonlyargs) == len(node.args.kw_defaults)
        for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
            add_arg(arg.arg, Parameter.KEYWORD_ONLY, default)

        kwarg = node.args.kwarg
        if kwarg is not None:
            add_arg(kwarg.arg, Parameter.VAR_KEYWORD, None)

        return_type = annotations.get('return')
        return_annotation = Parameter.empty if return_type is None or is_none_literal(return_type) else _AnnotationValueFormatter(return_type, ctx=func)
        try:
            signature = Signature(parameters, return_annotation=return_annotation)
        except ValueError as ex:
            func.report(f'{func.fullName()} has invalid parameters: {ex}')
            signature = Signature()

        func.annotations = annotations

        # Only set main function signature if it is a non-overload
        if is_overload_func:
            func.overloads.append(model.FunctionOverload(primary=func, signature=signature, decorators=node.decorator_list))
        else:
            func.signature = signature

    def depart_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.builder.popFunction()

    def depart_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.builder.popFunction()

    def _handlePropertyDef(self,
            node: Union[ast.AsyncFunctionDef, ast.FunctionDef],
            doc_node: Optional[Str],
            lineno: int
            ) -> model.Attribute:

        attr = self.builder.addAttribute(name=node.name, 
                                         kind=model.DocumentableKind.PROPERTY, 
                                         parent=self.builder.current, 
                                         lineno=lineno)
        attr.setLineNumber(lineno)

        if doc_node is not None:
            attr.setDocstring(doc_node)
            assert attr.docstring is not None
            pdoc = epydoc2stan.parse_docstring(attr, attr.docstring, attr)
            other_fields = []
            for field in pdoc.fields:
                tag = field.tag()
                if tag == 'return':
                    if not pdoc.has_body:
                        pdoc = field.body()

                elif tag == 'rtype':
                    attr.parsed_type = field.body()
                else:
                    other_fields.append(field)
            pdoc.fields = other_fields
            attr.parsed_docstring = pdoc

        if node.returns is not None:
            attr.annotation = upgrade_annotation(unstring_annotation(node.returns, attr), attr)
        attr.decorators = node.decorator_list

        return attr

    def _annotations_from_function(
            self, func: Union[ast.AsyncFunctionDef, ast.FunctionDef]
            ) -> Mapping[str, Optional[ast.expr]]:
        """Get annotations from a function definition.
        @param func: The function definition's AST.
        @return: Mapping from argument name to annotation.
            The name C{return} is used for the return type.
            Unannotated arguments are omitted.
        """
        def _get_all_args() -> Iterator[ast.arg]:
            base_args = func.args
            # New on Python 3.8 -- handle absence gracefully
            try:
                yield from base_args.posonlyargs
            except AttributeError:
                pass
            yield from base_args.args
            varargs = base_args.vararg
            if varargs:
                varargs.arg = epydoc2stan.VariableArgument(varargs.arg)
                yield varargs
            yield from base_args.kwonlyargs
            kwargs = base_args.kwarg
            if kwargs:
                kwargs.arg = epydoc2stan.KeywordArgument(kwargs.arg)
                yield kwargs
        def _get_all_ast_annotations() -> Iterator[Tuple[str, Optional[ast.expr]]]:
            for arg in _get_all_args():
                yield arg.arg, arg.annotation
            returns = func.returns
            if returns:
                yield 'return', returns
        return {
            # Include parameter names even if they're not annotated, so that
            # we can use the key set to know which parameters exist and warn
            # when non-existing parameters are documented.
            name: None if value is None else upgrade_annotation(unstring_annotation(
                value, self.builder.current), self.builder.current)
            for name, value in _get_all_ast_annotations()
            }
    
class _ValueFormatter:
    """
    Class to encapsulate a python value and translate it to HTML when calling L{repr()} on the L{_ValueFormatter}.
    Used for presenting default values of parameters.
    """

    def __init__(self, value: ast.expr, ctx: model.Documentable):
        self._colorized = colorize_inline_pyval(value)
        """
        The colorized value as L{ParsedDocstring}.
        """

        self._linker = ctx.docstring_linker
        """
        Linker.
        """

    def __repr__(self) -> str:
        """
        Present the python value as HTML. 
        Without the englobing <code> tags.
        """
        # Using node2stan.node2html instead of flatten(to_stan()). 
        # This avoids calling flatten() twice, 
        # but potential XML parser errors caused by XMLString needs to be handled later.
        return ''.join(node2stan.node2html(self._colorized.to_node(), self._linker))

class _AnnotationValueFormatter(_ValueFormatter):
    """
    Special L{_ValueFormatter} for function annotations.
    """
    def __init__(self, value: ast.expr, ctx: model.Function):
        super().__init__(value, ctx)
        self._linker = linker._AnnotationLinker(ctx)
    
    def __repr__(self) -> str:
        """
        Present the annotation wrapped inside <code> tags.
        """
        return '<code>%s</code>' % super().__repr__()

DocumentableT = TypeVar('DocumentableT', bound=model.Documentable)

class ASTBuilder:
    """
    Keeps tracks of the state of the AST build, creates documentable and adds objects to the system.
    """
    ModuleVistor = ModuleVistor

    def __init__(self, system: model.System):
        self.system = system
        
        self.current = cast(model.Documentable, None) # current visited object.
        self.currentMod: Optional[model.Module] = None # current module, set when visiting ast.Module.
        
        self._stack: List[model.Documentable] = []
        self.ast_cache: Dict[Path, Optional[ast.Module]] = {}

    def _push(self, 
              cls: Type[DocumentableT], 
              name: str, 
              lineno: int, 
              parent:Optional[model.Documentable]=None) -> DocumentableT:
        """
        Create and enter a new object of the given type and add it to the system.

        @param parent: Parent of the new documentable instance, it will use self.current if unspecified.
            Used for attributes declared in methods, typically ``__init__``.
        """
        obj = cls(self.system, name, parent or self.current)
        self.push(obj, lineno) 
        # make sure push() is called before addObject() since addObject() can trigger a warning for duplicates
        # and this relies on the correct parentMod attribute, which is set in push().
        self.system.addObject(obj)
        return obj

    def _pop(self, cls: Type[model.Documentable]) -> None:
        assert isinstance(self.current, cls)
        self.pop(self.current)

    def push(self, obj: model.Documentable, lineno: int) -> None:
        """
        Enter a documentable.
        """
        self._stack.append(self.current)
        self.current = obj
        if isinstance(obj, model.Module):
            assert self.currentMod is None
            obj.parentMod = self.currentMod = obj
        elif self.currentMod is not None:
            if obj.parentMod is not None:
                assert obj.parentMod is self.currentMod
            else:
                obj.parentMod = self.currentMod
        else:
            assert obj.parentMod is None
        if lineno:
            obj.setLineNumber(lineno)

    def pop(self, obj: model.Documentable) -> None:
        """
        Leave a documentable.
        """
        assert self.current is obj, f"{self.current!r} is not {obj!r}"
        self.current = self._stack.pop()
        if isinstance(obj, model.Module):
            self.currentMod = None

    def pushClass(self, name: str, lineno: int) -> model.Class:
        """
        Create and a new class in the system.
        """
        return self._push(self.system.Class, name, lineno)

    def popClass(self) -> None:
        """
        Leave a class.
        """
        self._pop(self.system.Class)

    def pushFunction(self, name: str, lineno: int) -> model.Function:
        """
        Create and enter a new function in the system.
        """
        return self._push(self.system.Function, name, lineno)

    def popFunction(self) -> None:
        """
        Leave a function.
        """
        self._pop(self.system.Function)

    def addAttribute(self,
            name: str, 
            kind: Optional[model.DocumentableKind], 
            parent: model.Documentable, 
            lineno: int
            ) -> model.Attribute:
        """
        Add a new attribute to the system.
        """
        attr = self._push(self.system.Attribute, name, lineno, parent=parent)
        self._pop(self.system.Attribute)
        attr.kind = kind
        return attr


    def processModuleAST(self, mod_ast: ast.Module, mod: model.Module) -> None:

        for name, node in findModuleLevelAssign(mod_ast):
            try:
                module_var_parser = MODULE_VARIABLES_META_PARSERS[name]
            except KeyError:
                continue
            else:
                module_var_parser(node, mod)

        vis = self.ModuleVistor(self, mod)
        vis.extensions.add(*self.system._astbuilder_visitors)
        vis.extensions.attach_visitor(vis)
        vis.walkabout(mod_ast)

    def parseFile(self, path: Path, ctx: model.Module) -> Optional[ast.Module]:
        try:
            return self.ast_cache[path]
        except KeyError:
            mod: Optional[ast.Module] = None
            try:
                mod = parseFile(path)
            except (SyntaxError, ValueError) as e:
                ctx.report(f"cannot parse file, {e}")

            self.ast_cache[path] = mod
            return mod
    
    def parseString(self, py_string:str, ctx: model.Module) -> Optional[ast.Module]:
        mod = None
        try:
            mod = _parse(py_string)
        except (SyntaxError, ValueError):
            ctx.report("cannot parse string")
        return mod

model.System.defaultBuilder = ASTBuilder

def findModuleLevelAssign(mod_ast: ast.Module) -> Iterator[Tuple[str, ast.Assign]]:
    """
    Find module level Assign. 
    Yields tuples containing the assigment name and the Assign node.
    """
    for node in mod_ast.body:
        if isinstance(node, ast.Assign) and \
            len(node.targets) == 1 and \
            isinstance(node.targets[0], ast.Name):
                yield (node.targets[0].id, node)

def parseAll(node: ast.Assign, mod: model.Module) -> None:
    """Find and attempt to parse into a list of names the 
    C{__all__} variable of a module's AST and set L{Module.all} accordingly."""

    if not isinstance(node.value, (ast.List, ast.Tuple)):
        mod.report(
            'Cannot parse value assigned to "__all__"',
            section='all', lineno_offset=node.lineno)
        return

    names = []
    for idx, item in enumerate(node.value.elts):
        try:
            name: object = ast.literal_eval(item)
        except ValueError:
            mod.report(
                f'Cannot parse element {idx} of "__all__"',
                section='all', lineno_offset=node.lineno)
        else:
            if isinstance(name, str):
                names.append(name)
            else:
                mod.report(
                    f'Element {idx} of "__all__" has '
                    f'type "{type(name).__name__}", expected "str"',
                    section='all', lineno_offset=node.lineno)

    if mod.all is not None:
        mod.report(
            'Assignment to "__all__" overrides previous assignment',
            section='all', lineno_offset=node.lineno)
    mod.all = names

def parseDocformat(node: ast.Assign, mod: model.Module) -> None:
    """
    Find C{__docformat__} variable of this 
    module's AST and set L{Module.docformat} accordingly.
        
    This is all valid::

        __docformat__ = "reStructuredText en"
        __docformat__ = "epytext"
        __docformat__ = "restructuredtext"
    """

    try:
        value = ast.literal_eval(node.value)
    except ValueError:
        mod.report(
            'Cannot parse value assigned to "__docformat__": not a string',
            section='docformat', lineno_offset=node.lineno)
        return
    
    if not isinstance(value, str):
        mod.report(
            'Cannot parse value assigned to "__docformat__": not a string',
            section='docformat', lineno_offset=node.lineno)
        return
        
    if not value.strip():
        mod.report(
            'Cannot parse value assigned to "__docformat__": empty value',
            section='docformat', lineno_offset=node.lineno)
        return
    
    # Language is ignored and parser name is lowercased.
    value = value.split(" ", 1)[0].lower()

    if mod._docformat is not None:
        mod.report(
            'Assignment to "__docformat__" overrides previous assignment',
            section='docformat', lineno_offset=node.lineno)

    mod.docformat = value

MODULE_VARIABLES_META_PARSERS: Mapping[str, Callable[[ast.Assign, model.Module], None]] = {
    '__all__': parseAll,
    '__docformat__': parseDocformat
}


def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(TypeAliasVisitorExt)
    r.register_post_processor(model.defaultPostProcess, priority=200)
