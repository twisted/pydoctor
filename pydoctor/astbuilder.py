"""Convert ASTs into L{pydoctor.model.Documentable} instances."""

import ast
import sys
from attr import attrs, attrib
from functools import partial
from inspect import BoundArguments, Parameter, Signature, signature
from itertools import chain
from pathlib import Path
from typing import (
    Any, Callable, Collection, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple,
    Type, TypeVar, Union, cast
)

import astor
from pydoctor import epydoc2stan, model, node2stan
from pydoctor.epydoc.markup._pyval_repr import colorize_inline_pyval
from pydoctor.astutils import bind_args, node2dottedname, node2fullname, is__name__equals__main__, NodeVisitor

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

_attrs_decorator_signature = signature(attrs)
"""Signature of the L{attr.s} class decorator."""

def _uses_auto_attribs(call: ast.Call, module: model.Module) -> bool:
    """Does the given L{attr.s()} decoration contain C{auto_attribs=True}?
    @param call: AST of the call to L{attr.s()}.
        This function will assume that L{attr.s()} is called without
        verifying that.
    @param module: Module that contains the call, used for error reporting.
    @return: L{True} if L{True} is passed for C{auto_attribs},
        L{False} in all other cases: if C{auto_attribs} is not passed,
        if an explicit L{False} is passed or if an error was reported.
    """
    try:
        args = bind_args(_attrs_decorator_signature, call)
    except TypeError as ex:
        message = str(ex).replace("'", '"')
        module.report(
            f"Invalid arguments for attr.s(): {message}",
            lineno_offset=call.lineno
            )
        return False

    auto_attribs_expr = args.arguments.get('auto_attribs')
    if auto_attribs_expr is None:
        return False

    try:
        value = ast.literal_eval(auto_attribs_expr)
    except ValueError:
        module.report(
            'Unable to figure out value for "auto_attribs" argument '
            'to attr.s(), maybe too complex',
            lineno_offset=call.lineno
            )
        return False

    if not isinstance(value, bool):
        module.report(
            f'Value for "auto_attribs" argument to attr.s() '
            f'has type "{type(value).__name__}", expected "bool"',
            lineno_offset=call.lineno
            )
        return False

    return value


def is_attrib(expr: Optional[ast.expr], ctx: model.Documentable) -> bool:
    """Does this expression return an C{attr.ib}?"""
    return isinstance(expr, ast.Call) and node2fullname(expr.func, ctx) in (
        'attr.ib', 'attr.attrib', 'attr.attr'
        )


_attrib_signature = signature(attrib)
"""Signature of the L{attr.ib} function for defining class attributes."""

def attrib_args(expr: ast.expr, ctx: model.Documentable) -> Optional[BoundArguments]:
    """Get the arguments passed to an C{attr.ib} definition.
    @return: The arguments, or L{None} if C{expr} does not look like
        an C{attr.ib} definition or the arguments passed to it are invalid.
    """
    if isinstance(expr, ast.Call) and node2fullname(expr.func, ctx) in (
            'attr.ib', 'attr.attrib', 'attr.attr'
            ):
        try:
            return bind_args(_attrib_signature, expr)
        except TypeError as ex:
            message = str(ex).replace("'", '"')
            ctx.module.report(
                f"Invalid arguments for attr.ib(): {message}",
                lineno_offset=expr.lineno
                )
    return None

def is_using_typing_final(obj: model.Attribute) -> bool:
    """
    Detect if C{obj}'s L{Attribute.annotation} is using L{typing.Final}.
    """
    final_qualifiers = ("typing.Final", "typing_extensions.Final")
    fullName = node2fullname(obj.annotation, obj)
    if fullName in final_qualifiers:
        return True
    if isinstance(obj.annotation, ast.Subscript):
        # Final[...] or typing.Final[...] expressions
        if isinstance(obj.annotation.value, (ast.Name, ast.Attribute)):
            value = obj.annotation.value
            fullName = node2fullname(value, obj)
            if fullName in final_qualifiers:
                return True

    return False

def is_constant(obj: model.Attribute) -> bool:
    """
    Detect if the given assignment is a constant. 

    To detect whether a assignment is a constant, this checks two things:
        - all-caps variable name
        - typing.Final annotation
    
    @note: Must be called after setting obj.annotation to detect variables using Final.
    """

    return obj.name.isupper() or is_using_typing_final(obj)

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

def is_alias(value: Optional[ast.expr]) -> bool:
    return node2dottedname(value) is not None


class ModuleVistor(NodeVisitor):

    def __init__(self, builder: 'ASTBuilder', module: model.Module):
        super().__init__()
        self.builder = builder
        self.system = builder.system
        self.module = module
        self._moduleLevelAssigns: List[str] = []


    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Compare):
            if is__name__equals__main__(node.test):
                # skip if __name__ == '__main__': blocks since
                # whatever is declared in them cannot be imported
                # and thus is not part of the API
                raise self.SkipNode()

    def visit_Module(self, node: ast.Module) -> None:
        assert self.module.docstring is None

        self.builder.push(self.module, 0)
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            self.module.setDocstring(node.body[0].value)
            epydoc2stan.extract_fields(self.module)

    def depart_Module(self, node: ast.Module) -> None:
        self.builder.pop(self.module)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Ignore classes within functions.
        parent = self.builder.current
        if isinstance(parent, model.Function):
            raise self.SkipNode()

        rawbases = []
        bases = []
        baseobjects = []

        for n in node.bases:
            if isinstance(n, ast.Name):
                str_base = n.id
            else:
                str_base = astor.to_source(n).strip()

            rawbases.append(str_base)
            full_name = parent.expandName(str_base)
            bases.append(full_name)
            baseobj = self.system.objForFullName(full_name)
            if not isinstance(baseobj, model.Class):
                baseobj = None
            baseobjects.append(baseobj)

        lineno = node.lineno
        if node.decorator_list:
            lineno = node.decorator_list[0].lineno

        cls: model.Class = self.builder.pushClass(node.name, lineno)
        cls.decorators = []
        cls.rawbases = rawbases
        cls.bases = bases
        cls.baseobjects = baseobjects

        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            cls.setDocstring(node.body[0].value)
            epydoc2stan.extract_fields(cls)

        if node.decorator_list:
            for decnode in node.decorator_list:
                args: Optional[Sequence[ast.expr]]
                if isinstance(decnode, ast.Call):
                    base = node2fullname(decnode.func, parent)
                    args = decnode.args
                    if base in ('attr.s', 'attr.attrs', 'attr.attributes'):
                        cls.auto_attribs |= _uses_auto_attribs(decnode, parent.module)
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
        cls.raw_decorators = node.decorator_list if node.decorator_list else []

        for b in cls.baseobjects:
            if b is not None:
                b.subclasses.append(cls)

    def depart_ClassDef(self, node: ast.ClassDef) -> None:
        self.builder.popClass()


    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        ctx = self.builder.current
        if not isinstance(ctx, model.CanContainImportsDocumentable):
            self.builder.warning("processing import statement in odd context", str(ctx))
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

        mod = self.system.getProcessedModule(modname)
        if mod is None:
            # We don't have any information about the module, so we don't know
            # what names to import.
            self.builder.warning("import * from unknown", modname)
            return

        self.builder.warning("import *", modname)

        # Get names to import: use __all__ if available, otherwise take all
        # names that are not private.
        names = mod.all
        if names is None:
            names = [
                name
                for name in chain(mod.contents.keys(),
                                  mod._localNameToFullName_map.keys())
                if not name.startswith('_')
                ]

        # Fetch names to export.
        exports = self._getCurrentModuleExports()

        # Add imported names to our module namespace.
        assert isinstance(self.builder.current, model.CanContainImportsDocumentable)
        _localNameToFullName = self.builder.current._localNameToFullName_map
        expandName = mod.expandName
        for name in names:

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
                        origin_module:Union[model.Module, str]) -> bool:
        """
        Move re-exported objects into current module.

        @param origin_module: None if the module is unknown to this system.
        @returns: True if the imported name has been sucessfully re-exported.
        """
        # Move re-exported objects into current module.
        current = self.builder.current
        if isinstance(origin_module, model.Module):
            modname = origin_module.fullName()
            known_module = True
        else:
            modname = origin_module
            known_module = False
        if as_name in curr_mod_exports:
            # In case of duplicates names, we can't rely on resolveName,
            # So we use content.get first to resolve non-alias names. 
            if known_module:
                ob = origin_module.contents.get(origin_name) or origin_module.resolveName(origin_name)
                if ob is None:
                    self.builder.warning("cannot resolve re-exported name",
                                            f'{modname}.{origin_name}')
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
            else:
                # re-export names that are not part of the current system with an alias
                attr = current.contents.get(as_name)
                if not attr:
                    attr = self.builder.addAttribute(name=as_name, kind=model.DocumentableKind.ALIAS, parent=current)
                assert isinstance(attr, model.Attribute)
                attr._alias_to = f'{modname}.{origin_name}'
                # This is only for the HTML repr
                attr.value=ast.Name(attr._alias_to)
                return True
            
            # if mod is None: 
            #         # re-export names that are not part of the current system with an alias
            #         attr = current.contents.get(asname)
            #         if not attr:
            #             attr = self.builder.addAttribute(name=asname, kind=model.DocumentableKind.ALIAS, parent=current)
            #         assert isinstance(attr, model.Attribute)
            #         attr._alias_to = f'{modname}.{orgname}'
            #         # This is only for the HTML repr
            #         attr.value=ast.Name(attr._alias_to)
            #         continue
            #     else:
            #         try:
            #             ob = mod.contents[orgname]
            #         except KeyError:
            #             self.builder.warning("cannot find re-exported name",
            #                                 f'{modname}.{orgname}')
            #         else:
            #             if mod.all is None or orgname not in mod.all:
            #                 self.system.msg(
            #                     "astbuilder",
            #                     "moving %r into %r" % (ob.fullName(), current.fullName())
            #                     )
            #                 # Must be a Module since the exports is set to an empty list if it's not.
            #                 assert isinstance(current, model.Module)
            #                 ob.reparent(current, asname)
            #                 continue
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

            if self._handleReExport(exports, orgname, asname, mod or modname) is True:
                continue

            # If we're importing from a package, make sure imported modules
            # are processed (getProcessedModule() ignores non-modules).
            if isinstance(mod, model.Package):
                self.system.getProcessedModule(f'{modname}.{orgname}')

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
        if not isinstance(self.builder.current, model.CanContainImportsDocumentable):
            self.builder.warning("processing import statement in odd context",
                                 str(self.builder.current))
            return
        _localNameToFullName = self.builder.current._localNameToFullName_map
        for al in node.names:
            fullname, asname = al.name, al.asname
            if asname is not None:
                _localNameToFullName[asname] = fullname


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
    
    def _warnsConstantAssigmentOverride(self, obj: model.Attribute, lineno_offset: int) -> None:
        obj.report(f'Assignment to constant "{obj.name}" overrides previous assignment '
                    f'at line {obj.linenumber}, the original value will not be part of the docs.', 
                            section='ast', lineno_offset=lineno_offset)
                            
    def _warnsConstantReAssigmentInInstance(self, obj: model.Attribute, lineno_offset: int = 0) -> None:
        obj.report(f'Assignment to constant "{obj.name}" inside an instance is ignored, this value will not be part of the docs.', 
                        section='ast', lineno_offset=lineno_offset)

    def _handleConstant(self, obj: model.Attribute, value: Optional[ast.expr], lineno: int) -> None:
        """Must be called after obj.setLineNumber() to have the right line number in the warning."""
        
        if is_attribute_overridden(obj, value):
            
            if obj.kind in (model.DocumentableKind.CONSTANT, 
                                model.DocumentableKind.VARIABLE, 
                                model.DocumentableKind.CLASS_VARIABLE):
                # Module/Class level warning, regular override.
                self._warnsConstantAssigmentOverride(obj=obj, lineno_offset=lineno-obj.linenumber)
            else:
                # Instance level warning caught at the time of the constant detection.
                self._warnsConstantReAssigmentInInstance(obj)

        obj.value = value
        
        obj.kind = model.DocumentableKind.CONSTANT

        # A hack to to display variables annotated with Final with the real type instead.
        if is_using_typing_final(obj):
            if isinstance(obj.annotation, ast.Subscript):
                try:
                    annotation = extract_final_subscript(obj.annotation)
                except ValueError as e:
                    obj.report(str(e), section='ast', lineno_offset=lineno-obj.linenumber)
                    obj.annotation = _infer_type(value) if value else None
                else:
                    # Will not display as "Final[str]" but rather only "str"
                    obj.annotation = annotation
            else:
                # Just plain "Final" annotation.
                # Simply ignore it because it's duplication of information.
                obj.annotation = _infer_type(value) if value else None
    
    def _handleAlias(self, obj: model.Attribute, value: Optional[ast.expr], lineno: int) -> None:
        """
        Must be called after obj.setLineNumber() to have the right line number in the warning.

        Create an alias or update an alias.
        """
        
        if is_attribute_overridden(obj, value) and is_alias(obj.value):
            obj.report(f'Assignment to alias "{obj.name}" overrides previous alias '
                    f'at line {obj.linenumber}.', 
                            section='ast', lineno_offset=lineno-obj.linenumber)
        obj.system.msg(msg=f'Processing alias {obj.name!r} at {obj.module.name}:{obj.linenumber}.', 
                    section='ast', 
                    thresh=2)

        obj.kind = model.DocumentableKind.ALIAS
        # This will be used for HTML repr of the alias.
        obj.value = value
        dottedname = node2dottedname(value)
        # It cannot be None, because we call _handleAlias() only if is_alias() is True.
        assert dottedname is not None
        name = '.'.join(dottedname)
        # Store the alias value as string now, this avoids doing it in _resolveAlias().
        obj._alias_to = name


    def _handleModuleVar(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        if target in MODULE_VARIABLES_META_PARSERS:
            # This is metadata, not a variable that needs to be documented,
            # and therefore doesn't need an Attribute instance.
            return
        parent = self.builder.current
        obj = parent.contents.get(target)
        
        if obj is None:
            obj = self.builder.addAttribute(name=target, kind=None, parent=parent)
        
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
            return
            
        if annotation is None and expr is not None:
            annotation = _infer_type(expr)
        
        obj.annotation = annotation
        obj.setLineNumber(lineno)
        
        if is_alias(expr):
            self._handleAlias(obj=obj, value=expr, lineno=lineno)
        elif is_constant(obj):
            self._handleConstant(obj=obj, value=expr, lineno=lineno)
        else:
            obj.kind = model.DocumentableKind.VARIABLE
            # We store the expr value for all Attribute in order to be able to 
            # check if they have been initialized or not.
            obj.value = expr

        self.builder.currentAttr = obj

    def _handleAssignmentInModule(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        module = self.builder.current
        assert isinstance(module, model.Module)
        self._handleModuleVar(target, annotation, expr, lineno)

    def _handleClassVar(self,
            name: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        cls = self.builder.current
        assert isinstance(cls, model.Class)
        if not _maybeAttribute(cls, name):
            return

        # Class variables can only be Attribute, so it's OK to cast
        obj = cast(Optional[model.Attribute], cls.contents.get(name))

        if obj is None:
            obj = self.builder.addAttribute(name=name, kind=None, parent=cls)

        if obj.kind is None:
            instance = is_attrib(expr, cls) or (
                cls.auto_attribs and annotation is not None and not (
                    isinstance(annotation, ast.Subscript) and
                    node2fullname(annotation.value, cls) == 'typing.ClassVar'
                    )
                )
            obj.kind = model.DocumentableKind.INSTANCE_VARIABLE if instance else model.DocumentableKind.CLASS_VARIABLE

        if expr is not None:
            if annotation is None:
                annotation = self._annotation_from_attrib(expr, cls)
            if annotation is None:
                annotation = _infer_type(expr)
        
        obj.annotation = annotation
        obj.setLineNumber(lineno)

        if is_alias(expr):
            self._handleAlias(obj=obj, value=expr, lineno=lineno)
        elif is_constant(obj):
            self._handleConstant(obj=obj, value=expr, lineno=lineno)
        else:
            obj.value = expr

        self.builder.currentAttr = obj

    def _handleInstanceVar(self,
            name: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        func = self.builder.current
        if not isinstance(func, model.Function):
            return
        cls = func.parent
        if not isinstance(cls, model.Class):
            return
        if not _maybeAttribute(cls, name):
            return

        # Class variables can only be Attribute, so it's OK to cast because we used _maybeAttribute() above.
        obj = cast(Optional[model.Attribute], cls.contents.get(name))
        if obj is None:

            obj = self.builder.addAttribute(name=name, kind=None, parent=cls)

        if annotation is None and expr is not None:
            annotation = _infer_type(expr)
        
        obj.annotation = annotation
        obj.setLineNumber(lineno)

        # Maybe an instance variable overrides a constant, 
        # so we check before setting the kind to INSTANCE_VARIABLE.
        if obj.kind is model.DocumentableKind.CONSTANT:
            self._warnsConstantReAssigmentInInstance(obj, lineno_offset=lineno-obj.linenumber)
        else:
            obj.kind = model.DocumentableKind.INSTANCE_VARIABLE
            obj.value = expr
        
        self.builder.currentAttr = obj

    def _handleAssignmentInClass(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        cls = self.builder.current
        assert isinstance(cls, model.Class)
        self._handleClassVar(target, annotation, expr, lineno)

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
            obj.docstring = docstring
            # TODO: It might be better to not perform docstring parsing until
            #       we have the final docstrings for all objects.
            obj.parsed_docstring = None

    def _handleAssignment(self,
            targetNode: ast.expr,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        if isinstance(targetNode, ast.Name):
            target = targetNode.id
            scope = self.builder.current
            if isinstance(scope, model.Module):
                self._handleAssignmentInModule(target, annotation, expr, lineno)
            elif isinstance(scope, model.Class):
                if not self._handleOldSchoolMethodDecoration(target, expr):
                    self._handleAssignmentInClass(target, annotation, expr, lineno)
        elif isinstance(targetNode, ast.Attribute):
            value = targetNode.value
            if targetNode.attr == '__doc__':
                self._handleDocstringUpdate(value, expr, lineno)
            elif isinstance(value, ast.Name) and value.id == 'self':
                self._handleInstanceVar(targetNode.attr, annotation, expr, lineno)
            # TODO: Fix https://github.com/twisted/pydoctor/issues/13

    def visit_Assign(self, node: ast.Assign) -> None:
        lineno = node.lineno
        expr = node.value

        type_comment: Optional[str] = getattr(node, 'type_comment', None)
        if type_comment is None:
            annotation = None
        else:
            annotation = self._unstring_annotation(ast.Str(type_comment, lineno=lineno))

        for target in node.targets:
            if isinstance(target, ast.Tuple):
                for elem in target.elts:
                    # Note: We skip type and aliasing analysis for this case,
                    #       but we do record line numbers.
                    self._handleAssignment(elem, None, None, lineno)
            else:
                self._handleAssignment(target, annotation, expr, lineno)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        annotation = self._unstring_annotation(node.annotation)
        self._handleAssignment(node.target, annotation, node.value, node.lineno)

    def visit_Expr(self, node: ast.Expr) -> None:
        value = node.value
        if isinstance(value, ast.Str):
            attr = self.builder.currentAttr
            if attr is not None:
                attr.setDocstring(value)
                self.builder.currentAttr = None
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

        lineno = node.lineno

        # setting linenumber from the start of the decorations
        if node.decorator_list:
            lineno = node.decorator_list[0].lineno

        # extracting docstring
        docstring: Optional[ast.Str] = None
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) \
                              and isinstance(node.body[0].value, ast.Str):
            docstring = node.body[0].value

        func_name = node.name

        # determine the function's kind
        is_property = False
        is_classmethod = False
        is_staticmethod = False
        if isinstance(parent, model.Class) and node.decorator_list:
            for d in node.decorator_list:
                if isinstance(d, ast.Call):
                    deco_name = node2dottedname(d.func)
                else:
                    deco_name = node2dottedname(d)
                if deco_name is None:
                    continue
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

        if is_property:
            # handle property and skip child nodes.
            attr = self._handlePropertyDef(node, docstring, lineno)
            if is_classmethod:
                attr.report(f'{attr.fullName()} is both property and classmethod')
            if is_staticmethod:
                attr.report(f'{attr.fullName()} is both property and staticmethod')
            raise self.SkipNode()

        func = self.builder.pushFunction(func_name, lineno)
        func.is_async = is_async
        if docstring is not None:
            func.setDocstring(docstring)
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
        def get_default(index: int) -> Optional[ast.expr]:
            assert 0 <= index < num_pos_args, index
            index -= default_offset
            return None if index < 0 else defaults[index]

        parameters: List[Parameter] = []
        def add_arg(name: str, kind: Any, default: Optional[ast.expr]) -> None:
            default_val = Parameter.empty if default is None else _ValueFormatter(default, ctx=func)
            parameters.append(Parameter(name, kind, default=default_val))

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

        try:
            signature = Signature(parameters)
        except ValueError as ex:
            func.report(f'{func.fullName()} has invalid parameters: {ex}')
            signature = Signature()

        func.signature = signature
        func.annotations = self._annotations_from_function(node)
    
    def depart_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.builder.popFunction()

    def depart_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.builder.popFunction()

    def _handlePropertyDef(self,
            node: Union[ast.AsyncFunctionDef, ast.FunctionDef],
            docstring: Optional[ast.Str],
            lineno: int
            ) -> model.Attribute:

        attr = self.builder.addAttribute(name=node.name, kind=model.DocumentableKind.PROPERTY, parent=self.builder.current)
        attr.setLineNumber(lineno)

        if docstring is not None:
            attr.setDocstring(docstring)
            assert attr.docstring is not None
            pdoc = epydoc2stan.parse_docstring(attr, attr.docstring, attr)
            other_fields = []
            for field in pdoc.fields:
                tag = field.tag()
                if tag == 'return':
                    if not pdoc.has_body:
                        pdoc = field.body()
                        # Avoid format_summary() going back to the original
                        # empty-body docstring.
                        attr.docstring = ''
                elif tag == 'rtype':
                    attr.parsed_type = field.body()
                else:
                    other_fields.append(field)
            pdoc.fields = other_fields
            attr.parsed_docstring = pdoc

        if node.returns is not None:
            attr.annotation = self._unstring_annotation(node.returns)
        attr.decorators = node.decorator_list

        return attr

    def _annotation_from_attrib(self,
            expr: ast.expr,
            ctx: model.Documentable
            ) -> Optional[ast.expr]:
        """Get the type of an C{attr.ib} definition.
        @param expr: The expression's AST.
        @param ctx: The context in which this expression is evaluated.
        @return: A type annotation, or None if the expression is not
                 an C{attr.ib} definition or contains no type information.
        """
        args = attrib_args(expr, ctx)
        if args is not None:
            typ = args.arguments.get('type')
            if typ is not None:
                return self._unstring_annotation(typ)
            default = args.arguments.get('default')
            if default is not None:
                return _infer_type(default)
        return None

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
            name: None if value is None else self._unstring_annotation(value)
            for name, value in _get_all_ast_annotations()
            }

    def _unstring_annotation(self, node: ast.expr) -> ast.expr:
        """Replace all strings in the given expression by parsed versions.
        @return: The unstringed node. If parsing fails, an error is logged
            and the original node is returned.
        """
        try:
            expr = _AnnotationStringParser().visit(node)
        except SyntaxError as ex:
            module = self.builder.currentMod
            assert module is not None
            module.report(f'syntax error in annotation: {ex}', lineno_offset=node.lineno)
            return node
        else:
            assert isinstance(expr, ast.expr), expr
            return expr

class _ValueFormatter:
    """
    Class to encapsulate a python value and translate it to HTML when calling L{repr()} on the L{_ValueFormatter}.
    Used for presenting default values of parameters.
    """

    def __init__(self, value: Any, ctx: model.Documentable):
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
        # This avoids calling flatten() twice.
        return ''.join(node2stan.node2html(self._colorized.to_node(), self._linker))

class _AnnotationStringParser(ast.NodeTransformer):
    """Implementation of L{ModuleVistor._unstring_annotation()}.

    When given an expression, the node returned by L{ast.NodeVisitor.visit()}
    will also be an expression.
    If any string literal contained in the original expression is either
    invalid Python or not a singular expression, L{SyntaxError} is raised.
    """

    def _parse_string(self, value: str) -> ast.expr:
        statements = ast.parse(value).body
        if len(statements) != 1:
            raise SyntaxError("expected expression, found multiple statements")
        stmt, = statements
        if isinstance(stmt, ast.Expr):
            # Expression wrapped in an Expr statement.
            expr = self.visit(stmt.value)
            assert isinstance(expr, ast.expr), expr
            return expr
        else:
            raise SyntaxError("expected expression, found statement")

    def visit_Subscript(self, node: ast.Subscript) -> ast.Subscript:
        value = self.visit(node.value)
        if isinstance(value, ast.Name) and value.id == 'Literal':
            # Literal[...] expression; don't unstring the arguments.
            slice = node.slice
        elif isinstance(value, ast.Attribute) and value.attr == 'Literal':
            # typing.Literal[...] expression; don't unstring the arguments.
            slice = node.slice
        else:
            # Other subscript; unstring the slice.
            slice = self.visit(node.slice)
        return ast.copy_location(ast.Subscript(value, slice, node.ctx), node)

    # For Python >= 3.8:

    def visit_Constant(self, node: ast.Constant) -> ast.expr:
        value = node.value
        if isinstance(value, str):
            return ast.copy_location(self._parse_string(value), node)
        else:
            const = self.generic_visit(node)
            assert isinstance(const, ast.Constant), const
            return const

    # For Python < 3.8:

    def visit_Str(self, node: ast.Str) -> ast.expr:
        return ast.copy_location(self._parse_string(node.s), node)

def _infer_type(expr: ast.expr) -> Optional[ast.expr]:
    """Infer an expression's type.
    @param expr: The expression's AST.
    @return: A type annotation, or None if the expression has no obvious type.
    """
    try:
        value: object = ast.literal_eval(expr)
    except ValueError:
        return None
    else:
        ann = _annotation_for_value(value)
        if ann is None:
            return None
        else:
            return ast.fix_missing_locations(ast.copy_location(ann, expr))

def _annotation_for_value(value: object) -> Optional[ast.expr]:
    if value is None:
        return None
    name = type(value).__name__
    if isinstance(value, (dict, list, set, tuple)):
        ann_elem = _annotation_for_elements(value)
        if isinstance(value, dict):
            ann_value = _annotation_for_elements(value.values())
            if ann_value is None:
                ann_elem = None
            elif ann_elem is not None:
                ann_elem = ast.Tuple(elts=[ann_elem, ann_value])
        if ann_elem is not None:
            if name == 'tuple':
                ann_elem = ast.Tuple(elts=[ann_elem, ast.Ellipsis()])
            return ast.Subscript(value=ast.Name(id=name),
                                 slice=ast.Index(value=ann_elem))
    return ast.Name(id=name)

def _annotation_for_elements(sequence: Iterable[object]) -> Optional[ast.expr]:
    names = set()
    for elem in sequence:
        ann = _annotation_for_value(elem)
        if isinstance(ann, ast.Name):
            names.add(ann.id)
        else:
            # Nested sequences are too complex.
            return None
    if len(names) == 1:
        name = names.pop()
        return ast.Name(id=name)
    else:
        # Empty sequence or no uniform type.
        return None


DocumentableT = TypeVar('DocumentableT', bound=model.Documentable)

class ASTBuilder:
    """
    Keeps tracks of the state of the AST build, creates documentable and adds objects to the system.
    """
    ModuleVistor = ModuleVistor

    def __init__(self, system: model.System):
        self.system = system
        
        self.current = cast(model.Documentable, None) # current visited object
        self.currentMod: Optional[model.Module] = None # module, set when visiting ast.Module
        self.currentAttr: Optional[model.Documentable] = None # recently visited attribute object
        
        self._stack: List[model.Documentable] = []
        self.ast_cache: Dict[Path, Optional[ast.Module]] = {}


    def _push(self, cls: Type[DocumentableT], name: str, lineno: int) -> DocumentableT:
        """
        Create and enter a new object of the given type and add it to the system.
        """
        obj = cls(self.system, name, self.current)
        self.system.addObject(obj)
        self.push(obj, lineno)
        self.currentAttr = None
        return obj

    def _pop(self, cls: Type[model.Documentable]) -> None:
        assert isinstance(self.current, cls)
        self.pop(self.current)
        self.currentAttr = None

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
            name: str, kind: Optional[model.DocumentableKind], parent: model.Documentable
            ) -> model.Attribute:
        """
        Add a new attribute to the system, attributes cannot be "entered".
        """
        system = self.system
        parentMod = self.currentMod
        attr = system.Attribute(system, name, parent)
        attr.kind = kind
        attr.parentMod = parentMod
        system.addObject(attr)
        self.currentAttr = attr
        return attr

    def warning(self, message: str, detail: str) -> None:
        self.system._warning(self.current, message, detail)

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

    def parseFile(self, path: Path) -> Optional[ast.Module]:
        try:
            return self.ast_cache[path]
        except KeyError:
            mod: Optional[ast.Module] = None
            try:
                mod = parseFile(path)
            except (SyntaxError, ValueError):
                self.warning("cannot parse", str(path))
            self.ast_cache[path] = mod
            return mod
    
    def parseString(self, py_string:str) -> Optional[ast.Module]:
        mod = None
        try:
            mod = _parse(py_string)
        except (SyntaxError, ValueError):
            self.warning("cannot parse string: ", py_string)
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
