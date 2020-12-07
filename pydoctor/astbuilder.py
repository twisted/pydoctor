"""Convert ASTs into L{pydoctor.model.Documentable} instances."""

import ast
import sys
from functools import partial
from inspect import Parameter, Signature
from itertools import chain
from pathlib import Path
from typing import (
    Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union
)

import astor
from pydoctor import epydoc2stan, model


def parseFile(path: Path) -> ast.AST:
    """Parse the contents of a Python source file."""
    with open(path, 'rb') as f:
        src = f.read() + b'\n'
    return _parse(src)

if sys.version_info >= (3,8):
    _parse = partial(ast.parse, type_comments=True)
else:
    _parse = ast.parse


def node2dottedname(node: Optional[ast.expr]) -> Optional[List[str]]:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    else:
        return None
    if len(parts) == 1 and parts[0] in ('True', 'False', 'None'):
        # On Python 3, these are NameConstant nodes, but on Python 2
        # they are Name nodes.
        return None
    parts.reverse()
    return parts


def node2fullname(expr: Optional[ast.expr], ctx: model.Documentable) -> Optional[str]:
    dottedname = node2dottedname(expr)
    if dottedname is None:
        return None
    base = ctx.expandName(dottedname[0])
    if base:
        return '.'.join([base] + dottedname[1:])
    else:
        return None


class ModuleVistor(ast.NodeVisitor):
    def __init__(self, builder: 'ASTBuilder', module: model.Module):
        self.builder = builder
        self.system = builder.system
        self.module = module

    def default(self, node):
        self.currAttr = None
        for child in node.body:
            self.newAttr = None
            self.visit(child)
            self.currAttr = self.newAttr
        self.newAttr = None

    def visit_Module(self, node):
        assert self.module.docstring is None

        self.builder.push(self.module, 0)
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            self.module.setDocstring(node.body[0].value)
            epydoc2stan.extract_fields(self.module)
        self.default(node)
        self.builder.pop(self.module)

    def visit_ClassDef(self, node):
        # Ignore classes within functions.
        parent = self.builder.current
        if isinstance(parent, model.Function):
            return

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

        cls = self.builder.pushClass(node.name, lineno)
        cls.decorators = []
        cls.rawbases = rawbases
        cls.bases = bases
        cls.baseobjects = baseobjects

        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            cls.setDocstring(node.body[0].value)
            epydoc2stan.extract_fields(cls)

        def node2data(node):
            dotted_name = node2dottedname(node)
            if dotted_name is None:
                return None
            dotted_name = '.'.join(dotted_name)
            full_name = self.builder.current.expandName(dotted_name)
            obj = self.system.objForFullName(full_name)
            return (dotted_name, full_name, obj)

        if node.decorator_list:
            for decnode in node.decorator_list:
                if isinstance(decnode, ast.Call):
                    args = []
                    for arg in decnode.args:
                        args.append(node2data(arg))
                    base = node2data(decnode.func)
                else:
                    base = node2data(decnode)
                    args = None
                cls.decorators.append((base, args))
        cls.raw_decorators = node.decorator_list if node.decorator_list else []

        for b in cls.baseobjects:
            if b is not None:
                b.subclasses.append(cls)
        self.default(node)
        self.builder.popClass()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not isinstance(self.builder.current, model.CanContainImportsDocumentable):
            self.builder.warning("processing import statement in odd context",
                                 str(self.builder.current))
            return

        modname = node.module
        if modname is None:
            return

        if node.level:
            # Relative import.
            parent: Optional[model.Documentable] = self.builder.current.parentMod
            for _ in range(node.level):
                if parent is None:
                    self.builder.warning("relative import level too high",
                                         str(node.level))
                    return
                parent = parent.parent
            if parent is not None:
                modname = f'{parent.fullName()}.{modname}'

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

        # Add imported names to our module namespace.
        _localNameToFullName = self.builder.current._localNameToFullName_map
        expandName = mod.expandName
        for name in names:
            _localNameToFullName[name] = expandName(name)

    def _importNames(self, modname: str, names: Iterable[ast.alias]) -> None:
        """Handle a C{from <modname> import <names>} statement."""

        # Process the module we're importing from.
        # If we're importing from a package, 'mod' will be the __init__ module.
        mod = self.system.getProcessedModule(modname)
        obj = self.system.objForFullName(modname)

        # Are we importing from a package?
        is_package = isinstance(obj, model.Package)
        assert is_package or obj is mod or mod is None

        # Fetch names to export.
        current = self.builder.current
        if isinstance(current, model.Module):
            exports = current.all
            if exports is None:
                exports = []
        else:
            # Don't export names imported inside classes or functions.
            exports = []

        _localNameToFullName = current._localNameToFullName_map
        for al in names:
            orgname, asname = al.name, al.asname
            if asname is None:
                asname = orgname

            # Move re-exported objects into current module.
            if asname in exports and mod is not None:
                try:
                    ob = mod.contents[orgname]
                except KeyError:
                    self.builder.warning("cannot find re-exported name",
                                         f'{modname}.{orgname}')
                else:
                    if mod.all is None or orgname not in mod.all:
                        self.system.msg(
                            "astbuilder",
                            "moving %r into %r" % (ob.fullName(), current.fullName())
                            )
                        ob.reparent(current, asname)
                        continue

            # If we're importing from a package, make sure imported modules
            # are processed (getProcessedModule() ignores non-modules).
            if is_package:
                self.system.getProcessedModule(f'{modname}.{orgname}')

            _localNameToFullName[asname] = f'{modname}.{orgname}'

    def visit_Import(self, node):
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


    def _handleOldSchoolDecoration(self, target, expr):
        if not isinstance(expr, ast.Call):
            return False
        func = expr.func
        if not isinstance(func, ast.Name):
            return False
        func = func.id
        args = expr.args
        if len(args) != 1:
            return False
        arg, = args
        if not isinstance(arg, ast.Name):
            return False
        arg = arg.id
        if target == arg and func in ['staticmethod', 'classmethod']:
            target = self.builder.current.contents.get(target)
            if isinstance(target, model.Function):
                if target.kind != 'Method':
                    self.system.msg('ast', 'XXX')
                else:
                    target.kind = func.title().replace('m', ' M')
                    return True
        return False

    def _handleAliasing(self, target, expr):
        if target in self.builder.current.contents:
            return False
        ctx = self.builder.current
        full_name = node2fullname(expr, ctx)
        if full_name is None:
            return False
        ctx._localNameToFullName_map[target] = full_name
        return True

    def _handleModuleVar(self, target, annotation, lineno):
        if target == '__all__':
            # This is metadata, not a variable that needs to be documented.
            # It is handled by findAll(), which operates on the AST and
            # therefore doesn't need an Attribute instance.
            return
        parent = self.builder.current
        obj = parent.resolveName(target)
        if obj is None:
            obj = self.builder.addAttribute(target, None, parent)
        if isinstance(obj, model.Attribute):
            obj.kind = 'Variable'
            obj.annotation = annotation
            obj.setLineNumber(lineno)
            self.newAttr = obj

    def _handleAssignmentInModule(self, target, annotation, expr, lineno):
        if not self._handleAliasing(target, expr):
            self._handleModuleVar(target, annotation, lineno)

    def _maybeAttribute(self, cls: model.Class, name: str) -> bool:
        """Check whether a name is a potential attribute of the given class.
        This is used to prevent an assignment that wraps a method from
        creating an attribute that would overwrite or shadow that method.

        @return: L{True} if the name does not exist or is an existing (possibly
            inherited) attribute, L{False} otherwise
        """
        obj = cls.find(name)
        return obj is None or isinstance(obj, model.Attribute)

    def _handleClassVar(self, name: str, annotation: Optional[ast.expr], lineno: int) -> None:
        cls = self.builder.current
        if not self._maybeAttribute(cls, name):
            return
        obj = cls.contents.get(name)
        if obj is None:
            obj = self.builder.addAttribute(name, None, cls)
        if obj.kind is None:
            obj.kind = 'Class Variable'
        obj.annotation = annotation
        obj.setLineNumber(lineno)
        self.newAttr = obj

    def _handleInstanceVar(self, name: str, annotation: Optional[ast.expr], lineno: int) -> None:
        func = self.builder.current
        if not isinstance(func, model.Function):
            return
        cls = func.parent
        if not isinstance(cls, model.Class):
            return
        if not self._maybeAttribute(cls, name):
            return
        obj = cls.contents.get(name)
        if obj is None:
            obj = self.builder.addAttribute(name, None, cls)
        obj.kind = 'Instance Variable'
        obj.annotation = annotation
        obj.setLineNumber(lineno)
        self.newAttr = obj

    def _handleAssignmentInClass(self, target, annotation, expr, lineno):
        if not self._handleAliasing(target, expr):
            self._handleClassVar(target, annotation, lineno)

    def _handleDocstringUpdate(self, targetNode, expr, lineno):
        def warn(msg):
            self.system.msg('ast', "%s:%d: %s" % (
                    self.builder.currentMod.description, lineno, msg))

        # Figure out target object.
        full_name = node2fullname(targetNode, self.builder.current)
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
            docstring = ast.literal_eval(expr)
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

    def _handleAssignment(self, targetNode, annotation, expr, lineno):
        if isinstance(targetNode, ast.Name):
            target = targetNode.id
            scope = self.builder.current
            if isinstance(scope, model.Module):
                self._handleAssignmentInModule(target, annotation, expr, lineno)
            elif isinstance(scope, model.Class):
                if not self._handleOldSchoolDecoration(target, expr):
                    self._handleAssignmentInClass(target, annotation, expr, lineno)
        elif isinstance(targetNode, ast.Attribute):
            value = targetNode.value
            if targetNode.attr == '__doc__':
                self._handleDocstringUpdate(value, expr, lineno)
            elif isinstance(value, ast.Name) and value.id == 'self':
                self._handleInstanceVar(targetNode.attr, annotation, lineno)

    def visit_Assign(self, node):
        lineno = node.lineno
        expr = node.value
        annotation = self._annotation_from_attrib(expr, self.builder.current)
        if annotation is None:
            type_comment = getattr(node, 'type_comment', None)
            if type_comment is not None:
                annotation = self._unstring_annotation(ast.Str(type_comment,
                                                               lineno=lineno))
        if annotation is None:
            annotation = _infer_type(expr)
        for target in node.targets:
            if isinstance(target, ast.Tuple):
                for elem in target.elts:
                    # Note: We skip type and aliasing analysis for this case,
                    #       but we do record line numbers.
                    self._handleAssignment(elem, None, None, lineno)
            else:
                self._handleAssignment(target, annotation, expr, lineno)

    def visit_AnnAssign(self, node):
        annotation = self._unstring_annotation(node.annotation)
        self._handleAssignment(node.target, annotation, node.value, node.lineno)

    def visit_Expr(self, node):
        value = node.value
        if isinstance(value, ast.Str):
            attr = self.currAttr
            if attr is not None:
                attr.setDocstring(value)

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
            return

        lineno = node.lineno
        if node.decorator_list:
            lineno = node.decorator_list[0].lineno

        docstring: Optional[ast.Str] = None
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) \
                              and isinstance(node.body[0].value, ast.Str):
            docstring = node.body[0].value

        func_name = node.name
        is_property = False
        is_classmethod = False
        is_staticmethod = False
        if isinstance(parent, model.Class) and node.decorator_list:
            for d in node.decorator_list:
                if isinstance(d, ast.Name):
                    name = d.id
                    if name == 'property':
                        is_property = True
                    elif name.endswith('property') or name.endswith('Property'):
                        is_property = True
                    elif name == 'classmethod':
                        is_classmethod = True
                    elif name == 'staticmethod':
                        is_staticmethod = True
                elif isinstance(d, ast.Attribute):
                    if d.attr in ('setter', 'deleter'):
                        # Rename the setter/deleter, so it doesn't replace
                        # the property object.
                        func_name = f'{func_name}.{d.attr}'
                elif isinstance(d, ast.Call):
                    deco_name = node2fullname(d.func, parent)
                    if deco_name is not None and (
                            deco_name.endswith('property') or
                            deco_name.endswith('Property')
                            ):
                        is_property = True

        if is_property:
            attr = self._handlePropertyDef(node, docstring, lineno)
            if is_classmethod:
                attr.report(f'{attr.fullName()} is both property and classmethod')
            if is_staticmethod:
                attr.report(f'{attr.fullName()} is both property and staticmethod')
            return

        func = self.builder.pushFunction(func_name, lineno)
        func.is_async = is_async
        if docstring is not None:
            func.setDocstring(docstring)
        func.decorators = node.decorator_list
        if is_staticmethod:
            if is_classmethod:
                func.report(f'{func.fullName()} is both classmethod and staticmethod')
            else:
                func.kind = 'Static Method'
        elif is_classmethod:
            func.kind = 'Class Method'

        # Position-only arguments were introduced in Python 3.8.
        posonlyargs: Sequence[ast.arg] = getattr(node.args, 'posonlyargs', ())

        num_pos_args = len(posonlyargs) + len(node.args.args)
        defaults = node.args.defaults
        default_offset = num_pos_args - len(defaults)
        def get_default(index: int) -> Optional[ast.expr]:
            assert 0 <= index < num_pos_args, index
            index -= default_offset
            return None if index < 0 else defaults[index]

        parameters = []
        def add_arg(name: str, kind: Any, default: Optional[ast.expr]) -> None:
            default_val = Parameter.empty if default is None else _ValueFormatter(default)
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
        self.default(node)
        self.builder.popFunction()

    def _handlePropertyDef(self,
            node: Union[ast.AsyncFunctionDef, ast.FunctionDef],
            docstring: Optional[ast.Str],
            lineno: int
            ) -> model.Attribute:

        attr = self.builder.addAttribute(node.name, 'Property', self.builder.current)
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
        if isinstance(expr, ast.Call) \
                and node2fullname(expr.func, ctx) in ('attr.ib', 'attr.attrib'):
            keywords = {kw.arg: kw.value for kw in expr.keywords}
            typ = keywords.get('type')
            if typ is not None:
                return self._unstring_annotation(typ)
            default = keywords.get('default')
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
                yield varargs
            yield from base_args.kwonlyargs
            kwargs = base_args.kwarg
            if kwargs:
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
            self.builder.currentMod.report(
                    f'syntax error in annotation: {ex}',
                    lineno_offset=node.lineno)
            return node
        else:
            assert isinstance(expr, ast.expr), expr
            return expr


class _ValueFormatter:
    """Formats values stored in AST expressions.
    Used for presenting default values of parameters.
    """

    def __init__(self, value: ast.expr):
        self.value = value

    def __repr__(self) -> str:
        value = self.value
        if isinstance(value, ast.Num):
            return str(value.n)
        if isinstance(value, ast.Str):
            return repr(value.s)
        if isinstance(value, ast.Constant):
            return repr(value.value)
        if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
            operand = value.operand
            if isinstance(operand, ast.Num):
                return f'-{operand.n}'
            if isinstance(operand, ast.Constant):
                return f'-{operand.value}'
        source: str = astor.to_source(value)
        return source.strip()


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
        value = ast.literal_eval(expr)
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


class ASTBuilder:
    ModuleVistor = ModuleVistor

    system: model.System
    ast_cache: Dict[Path, Optional[ast.AST]]

    def __init__(self, system):
        self.system = system
        self.current = None
        self.currentMod = None
        self._stack = []
        self.ast_cache = {}

    def _push(self, cls, name, lineno):
        obj = cls(self.system, name, self.current)
        self.system.addObject(obj)
        self.push(obj, lineno)
        return obj

    def _pop(self, cls):
        assert isinstance(self.current, cls)
        self.pop(self.current)

    def push(self, obj, lineno):
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

    def pop(self, obj):
        assert self.current is obj, f"{self.current!r} is not {obj!r}"
        self.current = self._stack.pop()
        if isinstance(obj, model.Module):
            self.currentMod = None

    def pushClass(self, name, lineno):
        return self._push(self.system.Class, name, lineno)
    def popClass(self):
        self._pop(self.system.Class)

    def pushFunction(self, name, lineno):
        return self._push(self.system.Function, name, lineno)
    def popFunction(self):
        self._pop(self.system.Function)

    def addAttribute(self,
            name: str, kind: Optional[str], parent: model.Documentable
            ) -> model.Attribute:
        system = self.system
        parentMod = self.currentMod
        attr = system.Attribute(system, name, parent)
        attr.kind = kind
        attr.parentMod = parentMod
        system.addObject(attr)
        return attr

    def warning(self, message, detail):
        self.system._warning(self.current, message, detail)

    def processModuleAST(self, ast, mod):
        findAll(ast, mod)

        self.ModuleVistor(self, mod).visit(ast)

    def parseFile(self, path: Path) -> Optional[ast.AST]:
        try:
            return self.ast_cache[path]
        except KeyError:
            mod: Optional[ast.AST] = None
            try:
                mod = parseFile(path)
            except (SyntaxError, ValueError):
                self.warning("cannot parse", str(path))
            self.ast_cache[path] = mod
            return mod

model.System.defaultBuilder = ASTBuilder

def findAll(modast, mod):
    """Find and attempt to parse into a list of names the __all__ of a module's AST."""
    for node in modast.body:
        if isinstance(node, ast.Assign) and \
               len(node.targets) == 1 and \
               isinstance(node.targets[0], ast.Name) and \
               node.targets[0].id == '__all__':
            if mod.all is not None:
                mod.system.msg('all', "multiple assignments to %s.__all__ ??"%(mod.fullName(),))
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                mod.system.msg('all', "couldn't parse %s.__all__"%(mod.fullName(),))
                continue
            items = node.value.elts
            names = []
            for item in items:
                if not isinstance(item, ast.Str):
                    mod.system.msg('all', "couldn't parse %s.__all__"%(mod.fullName(),))
                    continue
                names.append(item.s)
                mod.all = names
