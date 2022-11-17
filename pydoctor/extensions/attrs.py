
"""
Support for L{attrs <attr>}.
"""

import ast
import inspect

from typing import Optional, Union

from pydoctor import astbuilder, model, astutils, extensions

import attr

attrs_decorator_signature = inspect.signature(attr.s)
"""Signature of the L{attr.s} class decorator."""

attrib_signature = inspect.signature(attr.ib)
"""Signature of the L{attr.ib} function for defining class attributes."""

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
    if not isinstance(call, ast.Call):
        return False
    if not astutils.node2fullname(call.func, module) in ('attr.s', 'attr.attrs', 'attr.attributes'):
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
    if isinstance(expr, ast.Call) and astutils.node2fullname(expr.func, ctx) in (
            'attr.ib', 'attr.attrib', 'attr.attr'
            ):
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
        self: astbuilder.ModuleVistor,
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

class ModuleVisitor(extensions.ModuleVisitorExt):
    
    def visit_ClassDef(self, node:ast.ClassDef) -> None:
        """
        Called when a class definition is visited.
        """
        cls = self.visitor.builder.current
        if not isinstance(cls, model.Class) or cls.name!=node.name:
            return

        assert isinstance(cls, AttrsClass)
        cls.auto_attribs = any(uses_auto_attribs(decnode, cls.module) for decnode in node.decorator_list)

    def _handleAttrsAssignmentInClass(self, target:str, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        cls = self.visitor.builder.current
        assert isinstance(cls, AttrsClass)

        attr: Optional[model.Documentable] = cls.contents.get(target)
        if attr is None:
            return
        if not isinstance(attr, model.Attribute):
            return

        annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
        
        if is_attrib(node.value, cls) or (
               cls.auto_attribs and \
               annotation is not None and \
               not astutils.is_using_typing_classvar(annotation, cls)):
            
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
            if annotation is None and node.value is not None:
                attr.annotation = annotation_from_attrib(self.visitor, node.value, cls)

    def _handleAttrsAssignment(self, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        for dottedname in astutils.iterassign(node):
            if dottedname and len(dottedname)==1:
                # Here, we consider single name assignment only
                current = self.visitor.builder.current
                if isinstance(current, model.Class):
                    self._handleAttrsAssignmentInClass(
                        dottedname[0], node
                    )
        
    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        self._handleAttrsAssignment(node)
    visit_AnnAssign = visit_Assign

class AttrsClass(extensions.ClassMixin, model.Class):
    
    def setup(self) -> None:
        super().setup()
        self.auto_attribs: bool = False
        """
        L{True} if this class uses the C{auto_attribs} feature of the L{attrs <attr>}
        library to automatically convert annotated fields into attributes.
        """

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
    r.register_mixin(AttrsClass)
