
"""
Support for L{attrs <attr>}.
"""

import ast
import functools
import inspect

from typing import Dict, Optional, Union

from pydoctor import astbuilder, model, astutils, extensions, visitor

import attr

attrs_decorator_signature = inspect.signature(attr.s)
"""Signature of the L{attr.s} class decorator."""

attrib_signature = inspect.signature(attr.ib)
"""Signature of the L{attr.ib} function for defining class attributes."""

def get_attrs_args(call: ast.AST, ctx: model.Module) -> Optional[inspect.BoundArguments]:
    """Get the arguments passed to an C{attr.s} class definition."""
    if not isinstance(call, ast.Call):
        return None
    try:
        return astutils.bind_args(attrs_decorator_signature, call)
    except TypeError as ex:
        message = str(ex).replace("'", '"')
        ctx.report(
            f"Invalid arguments for attr.s(): {message}",
            lineno_offset=call.lineno
            )
        return None

def is_attrib(expr: Optional[ast.expr], ctx: model.Documentable) -> bool:
    """Does this expression return an C{attr.ib}?"""
    return isinstance(expr, ast.Call) and astutils.node2fullname(expr.func, ctx) in (
        'attr.ib', 'attr.attrib', 'attr.attr'
        )
    
def is_factory_call(expr: ast.expr, ctx: model.Documentable) -> bool:
    """
    Does this AST represent a call to L{attr.Factory}?
    """
    return isinstance(expr, ast.Call) and \
        astutils.node2fullname(expr.func, ctx) in ('attrs.Factory', 'attr.Factory')

def get_attrib_args(expr: ast.expr, ctx: model.Documentable) -> Optional[inspect.BoundArguments]:
    """Get the arguments passed to an C{attr.ib} definition.
    @return: The arguments, or L{None} if C{expr} does not look like
        an C{attr.ib} definition or the arguments passed to it are invalid.
    """
    if is_attrib(expr, ctx):
        try:
            return astutils.bind_args(attrib_signature, expr)
        except TypeError as ex:
            message = str(ex).replace("'", '"')
            ctx.module.report(
                f"Invalid arguments for attr.ib(): {message}",
                lineno_offset=expr.lineno
                )
    return None

uses_init = functools.partial(astutils.get_literal_arg, name='init', default=True, typecheck=bool)
uses_kw_only = functools.partial(astutils.get_literal_arg, name='kw_only', default=False, typecheck=bool)
uses_auto_attribs = functools.partial(astutils.get_literal_arg, name='auto_attribs', default=False, typecheck=bool)

def annotation_from_attrib(
        args:inspect.BoundArguments,
        ctx: model.Documentable,
        for_init_method:bool=False
        ) -> Optional[ast.expr]:
    """Get the type of an C{attr.ib} definition.
    @param args: The L{inspect.BoundArguments} of the C{attr.ib()} call.
    @param ctx: The context in which this expression is evaluated.
    @param for_init_method: Whether we're trying to figure out the __init__ parameter annotations
        instead of the attribute annotations.
    @return: A type annotation, or None if the expression is not
                an C{attr.ib} definition or contains no type information.
    """
    typ = args.arguments.get('type')
    if typ is not None:
        return astutils.unstring_annotation(typ, ctx)
    default = args.arguments.get('default')
    if default is not None:
        return astbuilder._infer_type(default)
    # TODO: support factory parameter.
    if for_init_method:
        # If a converter is defined, then we can't be sure of what exact type of parameter is accepted
        converter = args.arguments.get('converter')
        if converter is not None:
            return ast.Constant(value=...)
    return None

def default_from_attrib(args:inspect.BoundArguments, ctx: model.Documentable) -> Optional[ast.AST]:
    d = args.arguments.get('default')
    f = args.arguments.get('factory')
    if d is not None:
        if is_factory_call(d, ctx):
            return ast.Constant(value=...)
        return d
    elif f: # If a factory is defined, the default value is not obvious.
        return ast.Constant(value=...)
    else:
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
        
        for name, decnode in astutils.iter_decorators(node, cls):
            if not name in ('attr.s', 'attr.attrs', 'attr.attributes'):
                continue
            
            # True by default
            cls.attrs_init = True

            attrs_args = get_attrs_args(decnode, cls.module)
            if attrs_args:
                cls.attrs_auto_attribs = uses_auto_attribs(args=attrs_args, lineno=decnode.lineno, module=cls.module)
                cls.attrs_init = uses_init(args=attrs_args, lineno=decnode.lineno, module=cls.module)
                cls.attrs_kw_only = uses_kw_only(args=attrs_args, lineno=decnode.lineno, module=cls.module)
            break
    
    def _handleAttrsAssignmentInClass(self, target:str, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        cls = self.visitor.builder.current
        assert isinstance(cls, AttrsClass)

        attr: Optional[model.Documentable] = cls.contents.get(target)
        if attr is None:
            return
        if not isinstance(attr, model.Attribute):
            return

        annotation = node.annotation if isinstance(node, ast.AnnAssign) else None
        
        is_attrs_attrib = is_attrib(node.value, cls)
        is_attrs_auto_attrib = cls.attrs_auto_attribs and \
               annotation is not None and \
               not astutils.is_using_typing_classvar(annotation, cls)
        
        if is_attrs_attrib or is_attrs_auto_attrib:
            
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
            attrib_args = get_attrib_args(node.value, cls)
            
            if annotation is None and attrib_args is not None:
                attr.annotation = annotation_from_attrib(attrib_args, cls)
            
            # Handle the auto-creation of the __init__ method.
            if cls.attrs_init:

                if is_attrs_auto_attrib or (attrib_args and uses_init(args=attrib_args, module=cls.module, lineno=node.lineno)):
                    kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
                    
                    if cls.attrs_kw_only or (attrib_args and uses_kw_only(args=attrib_args, module=cls.module, lineno=node.lineno)):
                        kind = inspect.Parameter.KEYWORD_ONLY

                    attrs_default = ast.Constant(value=...)
                    
                    if is_attrs_auto_attrib:
                        attrs_default = node.value
                        
                        if is_factory_call(attrs_default, cls):
                            # Factory is not a default value stricly speaking, 
                            # so we give up on trying to figure it out.
                            attrs_default = ast.Constant(value=...)
                    
                    elif attrib_args is not None:
                        attrs_default = default_from_attrib(attrib_args, cls)
                    
                    # attrs strips the leading underscores from the parameter names,
                    # since there is not such thing as a private parameter.
                    _init_param_name = attr.name.lstrip('_')

                    # TODO: Check if attrs defines a converter, if it does not, it's OK
                    # to deduce that the type of the argument is the same as type of the parameter.
                    # But actually, this might be a wrong assumption.
                    cls.attrs_constructor_signature_builder.add_param(
                        _init_param_name, kind=kind, default=attrs_default, annotation=None
                    )
                    if attrib_args is not None:
                        cls.attrs_constructor_annotations[_init_param_name] = \
                            annotation_from_attrib(attrib_args, cls, for_init_method=True) or annotation
                    else:
                        cls.attrs_constructor_annotations[_init_param_name] = annotation

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
        
        self.attrs_auto_attribs: bool = False
        """
        L{True} if this class uses the C{auto_attribs} feature of the L{attrs <attr>}
        library to automatically convert annotated fields into attributes.
        """
        
        self.attrs_kw_only: bool = False
        """
        C{True} is this class uses C{kw_only} feature of L{attrs <attr>} library.
        """

        self.attrs_init: bool = False
        """
        False if L{attrs <attr>} is not generating an __init__ method for this class.
        """

        # since the signatures doesnt include type annotations, we track them in a separate attribute.
        self.attrs_constructor_signature_builder = astbuilder.SignatureBuilder(self)
        self.attrs_constructor_signature_builder.add_param('self', inspect.Parameter.POSITIONAL_OR_KEYWORD,)
        self.attrs_constructor_annotations: Dict[str, Optional[ast.expr]] = {'self':None}

def postProcess(system:model.System) -> None:

    for cls in list(system.objectsOfType(model.Class)):
        # by default attr.s() overrides any defined __init__ mehtod, whereas dataclasses.
        # TODO: but if auto_detect=True, we need to check if __init__ already exists, otherwise it does not replace it.
        # NOTE: But attr.define() use auto_detect=True by default! this is getting complicated...
        if cls.attrs_init:
            func = system.Function(system, '__init__', cls)
            system.addObject(func)
            # init Function attributes that otherwise would be undefined :/
            func.decorators = None
            func.is_async = False

            try:
                # TODO: collect arguments from super classes attributes definitions.
                func.signature = cls.attrs_constructor_signature_builder.get_signature()
                func.annotations = cls.attrs_constructor_annotations
            except ValueError as e:
                func.report(f'could not deduce attrs class __init__ signature: {e}')
                func.signature = inspect.Signature()
                func.annotations = {}

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
    r.register_mixin(AttrsClass)
    r.register_post_processor(postProcess)
