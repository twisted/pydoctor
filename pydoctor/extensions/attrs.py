
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

def is_attrib(expr: Optional[ast.expr], ctx: model.Documentable) -> bool:
    """Does this expression return an C{attr.ib}?"""
    return isinstance(expr, ast.Call) and astutils.node2fullname(expr.func, ctx) in (
        'attr.ib', 'attr.attrib', 'attr.attr'
        )

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
    if not is_attrib(expr, ctx):
        return None
    args = astutils.safe_bind_args(attrib_signature, expr, ctx.module)
    if args is not None:
        typ = args.arguments.get('type')
        if typ is not None:
            return astutils.unstring_annotation(typ, ctx)
        default = args.arguments.get('default')
        if default is not None:
            return astbuilder._infer_type(default)
    return None

class ModuleVisitor(DataclassLikeVisitor):

    DATACLASS_LIKE_KIND = 'attrs class'
    
    def visit_ClassDef(self, node:ast.ClassDef) -> None:
        """
        Called when a class definition is visited.
        """
        super().visit_ClassDef(node)

        cls = self.visitor.builder._stack[-1].contents.get(node.name)
        if not isinstance(cls, AttrsClass) or not cls.dataclassLike:
            return
        mod = cls.module
        try:
            attrs_deco = next(decnode for decnode in node.decorator_list 
                              if is_attrs_deco(decnode, mod))
        except StopIteration:
            return

        attrs_args = astutils.safe_bind_args(attrs_decorator_signature, attrs_deco, mod)
        if attrs_args:
            cls.auto_attribs = astutils.get_literal_arg(
                name='auto_attribs', default=False, typecheck=bool,
                args=attrs_args, lineno=attrs_deco.lineno, module=mod)
    
    def transformClassVar(self, cls: model.Class, 
                          attr: model.Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        assert isinstance(cls, AttrsClass)
        if is_attrib(value, cls) or (cls.auto_attribs and annotation is not None):
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
            if annotation is None and value is not None:
                attr.annotation = annotation_from_attrib(value, cls)
    
    def isDataclassLike(self, cls:ast.ClassDef, mod:model.Module) -> Optional[object]:
        if any(is_attrs_deco(dec, mod) for dec in cls.decorator_list):
            return self.DATACLASS_LIKE_KIND
        return None

class AttrsClass(DataclasLikeClass, model.Class):
    auto_attribs: bool = False
    """
    L{True} if this class uses the C{auto_attribs} feature of the L{attrs}
    library to automatically convert annotated fields into attributes.
    """

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
    r.register_mixin(AttrsClass)
