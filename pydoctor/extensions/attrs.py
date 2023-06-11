
"""
Support for L{attrs}.
"""

import ast
import inspect

from typing import Optional

from pydoctor import astbuilder, model, astutils, extensions
from pydoctor.extensions._dataclass_like import DataclasLikeClass, DataclassLikeVisitor

import attr

attrs_decorator_signature = inspect.signature(attr.s)
"""Signature of the L{attr.s} class decorator."""

attrib_signature = inspect.signature(attr.ib)
"""Signature of the L{attr.ib} function for defining class attributes."""

def is_attrs_deco(deco: ast.AST, module: model.Module) -> bool:
    if isinstance(deco, ast.Call):
        deco = deco.func
    return astutils.node2fullname(deco, module) in (
        'attr.s', 'attr.attrs', 'attr.attributes')

def uses_auto_attribs(call: ast.AST, module: model.Module) -> bool:
    """Does the given L{attr.s()} decoration contain C{auto_attribs=True}?
    @param call: AST of the call to L{attr.s()}.
        This function will assume that L{attr.s()} is called without
        verifying that.
    @param module: Module that contains the call, used for error reporting.
    @return: L{True} if L{True} is passed for C{auto_attribs},
        L{False} in all other cases: if C{auto_attribs} is not passed,
        if an explicit L{False} is passed or if an error was reported.
    """
    if not is_attrs_deco(call, module):
        return False
    if not isinstance(call, ast.Call):
        return False
    try:
        args = astutils.bind_args(attrs_decorator_signature, call)
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
    return isinstance(expr, ast.Call) and astutils.node2fullname(expr.func, ctx) in (
        'attr.ib', 'attr.attrib', 'attr.attr'
        )

def attrib_args(expr: ast.expr, ctx: model.Documentable) -> Optional[inspect.BoundArguments]:
    """Get the arguments passed to an C{attr.ib} definition.
    @return: The arguments, or L{None} if C{expr} does not look like
        an C{attr.ib} definition or the arguments passed to it are invalid.
    """
    if is_attrib(expr, ctx):
        assert isinstance(expr, ast.Call)
        try:
            return astutils.bind_args(attrib_signature, expr)
        except TypeError as ex:
            message = str(ex).replace("'", '"')
            ctx.module.report(
                f"Invalid arguments for attr.ib(): {message}",
                lineno_offset=expr.lineno
                )
    return None

def annotation_from_attrib(
        expr: ast.expr,
        ctx: model.Documentable
        ) -> Optional[ast.expr]:
    """Get the type of an C{attr.ib} definition.
    @param expr: The L{ast.Call} expression's AST.
    @param ctx: The context in which this expression is evaluated.
    @return: A type annotation, or None if the expression is not
                an C{attr.ib} definition or contains no type information.
    """
    args = attrib_args(expr, ctx)
    if args is not None:
        typ = args.arguments.get('type')
        if typ is not None:
            return astutils.unstring_annotation(typ, ctx)
        default = args.arguments.get('default')
        if default is not None:
            return astbuilder._infer_type(default)
    return None

class ModuleVisitor(DataclassLikeVisitor):
    
    def visit_ClassDef(self, node:ast.ClassDef) -> None:
        """
        Called when a class definition is visited.
        """
        super().visit_ClassDef(node)

        cls = self.visitor.builder._stack[-1].contents.get(node.name)
        if not isinstance(cls, AttrsClass):
            return

        cls.auto_attribs = any(uses_auto_attribs(decnode, cls.module) for decnode in node.decorator_list)
    
    def transformClassVar(self, cls: model.Class, 
                          attr: model.Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        assert isinstance(cls, AttrsClass)
        if is_attrib(value, cls) or (cls.auto_attribs and annotation is not None):
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
            if annotation is None and value is not None:
                attr.annotation = annotation_from_attrib(value, cls)
    
    def isDataclassLike(self, cls:ast.ClassDef, mod:model.Module) -> bool:
        return any(is_attrs_deco(dec, mod) for dec in cls.decorator_list)

class AttrsClass(DataclasLikeClass, model.Class):
    
    auto_attribs: bool = False
    """
    L{True} if this class uses the C{auto_attribs} feature of the L{attrs}
    library to automatically convert annotated fields into attributes.
    """

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
    r.register_mixin(AttrsClass)
