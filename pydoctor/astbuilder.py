"""Convert ASTs into L{pydoctor.model.Documentable} instances."""

import ast
import sys
from attr import attrs, attrib
from functools import partial
from inspect import BoundArguments, Parameter, Signature, signature
from itertools import chain
from pathlib import Path
from typing import (
    Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple,
    Type, TypeVar, Union, cast
)

import astor
from pydoctor import epydoc2stan, model


def parseFile(path: Path) -> ast.Module:
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
    parts.reverse()
    return parts


def node2fullname(expr: Optional[ast.expr], ctx: model.Documentable) -> Optional[str]:
    dottedname = node2dottedname(expr)
    if dottedname is None:
        return None
    return ctx.expandName('.'.join(dottedname))


def _maybeAttribute(cls: model.Class, name: str) -> bool:
    """Check whether a name is a potential attribute of the given class.
    This is used to prevent an assignment that wraps a method from
    creating an attribute that would overwrite or shadow that method.

    @return: L{True} if the name does not exist or is an existing (possibly
        inherited) attribute, L{False} otherwise
    """
    obj = cls.find(name)
    return obj is None or isinstance(obj, model.Attribute)


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


def bind_args(sig: Signature, call: ast.Call) -> BoundArguments:
    """Binds the arguments of a function call to that function's signature.
    @raise TypeError: If the arguments do not match the signature.
    """
    kwargs = {
        kw.arg: kw.value
        for kw in call.keywords
        # When keywords are passed using '**kwargs', the 'arg' field will
        # be None. We don't currently support keywords passed that way.
        if kw.arg is not None
        }
    return sig.bind(*call.args, **kwargs)


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


class ModuleVistor(ast.NodeVisitor):
    currAttr: Optional[model.Documentable]
    newAttr: Optional[model.Documentable]

    def __init__(self, builder: 'ASTBuilder', module: model.Module):
        self.builder = builder
        self.system = builder.system
        self.module = module

    def default(self, node: ast.AST) -> None:
        body: Optional[Sequence[ast.stmt]] = getattr(node, 'body', None)
        if body is not None:
            self.currAttr = None
            for child in body:
                self.newAttr = None
                self.visit(child)
                self.currAttr = self.newAttr
            self.newAttr = None

    def visit_Module(self, node: ast.Module) -> None:
        assert self.module.docstring is None

        self.builder.push(self.module, 0)
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            self.module.setDocstring(node.body[0].value)
            epydoc2stan.extract_fields(self.module)
        self.default(node)
        self.builder.pop(self.module)

    def visit_ClassDef(self, node: ast.ClassDef) -> Optional[model.Class]:
        # Ignore classes within functions.
        parent = self.builder.current
        if isinstance(parent, model.Function):
            return None

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
        self.default(node)
        self.builder.popClass()

        return cls

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        ctx = self.builder.current
        if not isinstance(ctx, model.CanContainImportsDocumentable):
            self.builder.warning("processing import statement in odd context", str(ctx))
            return

        modname = node.module
        if node.level:
            # Relative import.
            parent: Optional[model.Documentable] = ctx.parentMod
            for _ in range(node.level):
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

        # Add imported names to our module namespace.
        assert isinstance(self.builder.current, model.CanContainImportsDocumentable)
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
            assert isinstance(current, model.CanContainImportsDocumentable)
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


    def _handleOldSchoolDecoration(self, target: str, expr: Optional[ast.expr]) -> bool:
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
                if target_obj.kind != 'Method':
                    self.system.msg('ast', 'XXX')
                else:
                    target_obj.kind = func_name.title().replace('m', ' M')
                    return True
        return False

    def _handleModuleVar(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
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
            if annotation is None and expr is not None:
                annotation = _infer_type(expr)
            obj.annotation = annotation
            obj.setLineNumber(lineno)
            self.newAttr = obj

    def _handleAssignmentInModule(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        module = self.builder.current
        assert isinstance(module, model.Module)
        if not _handleAliasing(module, target, expr):
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
        obj: Optional[model.Attribute] = cls.contents.get(name)
        if obj is None:
            obj = self.builder.addAttribute(name, None, cls)
        if obj.kind is None:
            instance = is_attrib(expr, cls) or (
                cls.auto_attribs and annotation is not None and not (
                    isinstance(annotation, ast.Subscript) and
                    node2fullname(annotation.value, cls) == 'typing.ClassVar'
                    )
                )
            obj.kind = 'Instance Variable' if instance else 'Class Variable'
        if expr is not None:
            if annotation is None:
                annotation = self._annotation_from_attrib(expr, cls)
            if annotation is None:
                annotation = _infer_type(expr)
        obj.annotation = annotation
        obj.setLineNumber(lineno)
        self.newAttr = obj

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
        obj = cls.contents.get(name)
        if obj is None:
            obj = self.builder.addAttribute(name, None, cls)
        obj.kind = 'Instance Variable'
        if annotation is None and expr is not None:
            annotation = _infer_type(expr)
        obj.annotation = annotation
        obj.setLineNumber(lineno)
        self.newAttr = obj

    def _handleAssignmentInClass(self,
            target: str,
            annotation: Optional[ast.expr],
            expr: Optional[ast.expr],
            lineno: int
            ) -> None:
        cls = self.builder.current
        assert isinstance(cls, model.Class)
        if not _handleAliasing(cls, target, expr):
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
                if not self._handleOldSchoolDecoration(target, expr):
                    self._handleAssignmentInClass(target, annotation, expr, lineno)
        elif isinstance(targetNode, ast.Attribute):
            value = targetNode.value
            if targetNode.attr == '__doc__':
                self._handleDocstringUpdate(value, expr, lineno)
            elif isinstance(value, ast.Name) and value.id == 'self':
                self._handleInstanceVar(targetNode.attr, annotation, expr, lineno)

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
            module = self.builder.currentMod
            assert module is not None
            module.report(f'syntax error in annotation: {ex}', lineno_offset=node.lineno)
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
    ModuleVistor = ModuleVistor

    def __init__(self, system: model.System):
        self.system = system
        self.current = cast(model.Documentable, None)
        self.currentMod: Optional[model.Module] = None
        self._stack: List[model.Documentable] = []
        self.ast_cache: Dict[Path, Optional[ast.Module]] = {}

    def _push(self, cls: Type[DocumentableT], name: str, lineno: int) -> DocumentableT:
        obj = cls(self.system, name, self.current)
        self.system.addObject(obj)
        self.push(obj, lineno)
        return obj

    def _pop(self, cls: Type[model.Documentable]) -> None:
        assert isinstance(self.current, cls)
        self.pop(self.current)

    def push(self, obj: model.Documentable, lineno: int) -> None:
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
        assert self.current is obj, f"{self.current!r} is not {obj!r}"
        self.current = self._stack.pop()
        if isinstance(obj, model.Module):
            self.currentMod = None

    def pushClass(self, name: str, lineno: int) -> model.Class:
        return self._push(self.system.Class, name, lineno)
    def popClass(self) -> None:
        self._pop(self.system.Class)

    def pushFunction(self, name: str, lineno: int) -> model.Function:
        return self._push(self.system.Function, name, lineno)
    def popFunction(self) -> None:
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

    def warning(self, message: str, detail: str) -> None:
        self.system._warning(self.current, message, detail)

    def processModuleAST(self, mod_ast: ast.Module, mod: model.Module) -> None:
        findAll(mod_ast, mod)

        self.ModuleVistor(self, mod).visit(mod_ast)

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

model.System.defaultBuilder = ASTBuilder

def findAll(mod_ast: ast.Module, mod: model.Module) -> None:
    """Find and attempt to parse into a list of names the __all__ of a module's AST."""
    for node in mod_ast.body:
        if isinstance(node, ast.Assign) and \
               len(node.targets) == 1 and \
               isinstance(node.targets[0], ast.Name) and \
               node.targets[0].id == '__all__':
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                mod.report(
                    'Cannot parse value assigned to "__all__"',
                    section='all', lineno_offset=node.lineno)
                continue

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
