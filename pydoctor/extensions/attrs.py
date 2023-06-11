
"""
Support for L{attrs}.
"""

import ast
import functools
import inspect

from typing import Dict, Optional, Union, cast

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
    
def is_factory_call(expr: ast.expr, ctx: model.Documentable) -> bool:
    """
    Does this AST represent a call to L{attr.Factory}?
    """
    return isinstance(expr, ast.Call) and \
        astutils.node2fullname(expr.func, ctx) in ('attrs.Factory', 'attr.Factory')

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
    # if not is_attrib(expr, ctx):
    #     return None
    # args = astutils.safe_bind_args(attrib_signature, expr, ctx.module)
    # if args is not None:
    #     typ = args.arguments.get('type')
    #     if typ is not None:
    #         return astutils.unstring_annotation(typ, ctx)
    #     default = args.arguments.get('default')
    #     if default is not None:
    #         return astbuilder._infer_type(default)
    # return None
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

def default_from_attrib(args:inspect.BoundArguments, ctx: model.Documentable) -> Optional[ast.expr]:
    d = args.arguments.get('default')
    f = args.arguments.get('factory')
    if d is not None:
        if is_factory_call(d, ctx):
            return ast.Constant(value=...)
        return cast(ast.expr, d)
    elif f: # If a factory is defined, the default value is not obvious.
        return ast.Constant(value=...)
    else:
        return None

class ModuleVisitor(DataclassLikeVisitor):
    
    def visit_ClassDef(self, node:ast.ClassDef) -> None:
        """
        Called when a class definition is visited.
        """
        super().visit_ClassDef(node)

        cls = self.visitor.builder._stack[-1].contents.get(node.name)
        if not isinstance(cls, AttrsClass) or not cls.isDataclassLike:
            return
        mod = cls.module
        try:
            attrs_deco = next(decnode for decnode in node.decorator_list 
                              if is_attrs_deco(decnode, mod))
        except StopIteration:
            return

        attrs_args = astutils.safe_bind_args(attrs_decorator_signature, attrs_deco, mod)
        if attrs_args:
            cls.attrs_auto_attribs = astutils.get_literal_arg(name='auto_attribs', default=False, typecheck=bool,
                                                              args=attrs_args, lineno=attrs_deco.lineno, module=mod)
            cls.attrs_init = astutils.get_literal_arg(name='init', default=True, typecheck=bool,
                                                      args=attrs_args, lineno=attrs_deco.lineno, module=mod)
            cls.attrs_kw_only = astutils.get_literal_arg(name='kw_only', default=False, typecheck=bool,
                                                         args=attrs_args, lineno=attrs_deco.lineno, module=mod)
    
    def transformClassVar(self, cls: model.Class, 
                          attr: model.Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        assert isinstance(cls, AttrsClass)
        is_attrs_attrib = is_attrib(value, cls)
        is_attrs_auto_attrib = cls.attrs_auto_attribs and annotation is not None
        
        if is_attrs_attrib or is_attrs_auto_attrib:
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
            if annotation is None and value is not None:
                attrib_args = astutils.safe_bind_args(attrib_signature, value, cls.module)
                if attrib_args:
                    attr.annotation = annotation_from_attrib(attrib_args, cls)
            else:
                attrib_args = None
        
            # Handle the auto-creation of the __init__ method.
            if cls.attrs_init:
                
                if is_attrs_auto_attrib or (attrib_args and 
                                            astutils.get_literal_arg(name='init', default=True, typecheck=bool,
                                                                     args=attrib_args, module=cls.module, lineno=attr.linenumber)):
                    kind:inspect._ParameterKind = inspect.Parameter.POSITIONAL_OR_KEYWORD
                    
                    if cls.attrs_kw_only or (attrib_args and 
                                             astutils.get_literal_arg(name='kw_only', default=False, typecheck=bool,
                                                                      args=attrib_args, module=cls.module, lineno=attr.linenumber)):
                        kind = inspect.Parameter.KEYWORD_ONLY

                    attrs_default:Optional[ast.expr] = ast.Constant(value=...)
                    
                    if is_attrs_auto_attrib:
                        attrs_default = value
                        
                        if attrs_default and is_factory_call(attrs_default, cls):
                            # Factory is not a default value stricly speaking, 
                            # so we give up on trying to figure it out.
                            attrs_default = ast.Constant(value=...)
                    
                    elif attrib_args is not None:
                        attrs_default = default_from_attrib(attrib_args, cls)
                    
                    # attrs strips the leading underscores from the parameter names,
                    # since there is not such thing as a private parameter.
                    init_param_name = attr.name.lstrip('_')

                    # TODO: Check if attrs defines a converter, if it does not, it's OK
                    # to deduce that the type of the argument is the same as type of the parameter.
                    # But actually, this might be a wrong assumption.
                    cls.attrs_constructor_parameters.append(
                        inspect.Parameter(
                            init_param_name, kind=kind, 
                            default=astbuilder._ValueFormatter(attrs_default, cls) if attrs_default else inspect.Parameter.empty, 
                            annotation=inspect.Parameter.empty))
                    
                    if attrib_args is not None:
                        cls.attrs_constructor_annotations[init_param_name] = \
                            annotation_from_attrib(attrib_args, cls, for_init_method=True) or annotation
                    else:
                        cls.attrs_constructor_annotations[init_param_name] = annotation
    
    def isDataclassLike(self, cls:ast.ClassDef, mod:model.Module) -> bool:
        return any(is_attrs_deco(dec, mod) for dec in cls.decorator_list)

class AttrsClass(DataclasLikeClass, model.Class):
    def setup(self) -> None:
        super().setup()
        
        self.attrs_auto_attribs: bool = False
        """
        L{True} if this class uses the C{auto_attribs} feature of the L{attrs}
        library to automatically convert annotated fields into attributes.
        """
        
        self.attrs_kw_only: bool = False
        """
        C{True} is this class uses C{kw_only} feature of L{attrs <attr>} library.
        """

        self.attrs_init: bool = True
        """
        False if L{attrs <attr>} is not generating an __init__ method for this class.
        """

        # since the signatures doesnt include type annotations, we track them in a separate attribute.
        self.attrs_constructor_parameters = []
        self.attrs_constructor_parameters.append(inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD,))
        self.attrs_constructor_annotations: Dict[str, Optional[ast.expr]] = {'self': None}

def postProcess(system:model.System) -> None:

    for cls in list(system.objectsOfType(AttrsClass)):
        # by default attr.s() overrides any defined __init__ mehtod, whereas dataclasses.
        # TODO: but if auto_detect=True, we need to check if __init__ already exists, otherwise it does not replace it.
        # NOTE: But attr.define() use auto_detect=True by default! this is getting complicated...
        if cls.attrs_init:
            func = system.Function(system, '__init__', cls)
            system.addObject(func)
            # init Function attributes that otherwise would be undefined :/
            func.decorators = None
            func.is_async = False

            func.annotations = cls.attrs_constructor_annotations
            try:
                # TODO: collect arguments from super classes attributes definitions.
                func.signature = inspect.Signature(cls.attrs_constructor_parameters)
            except Exception as e:
                func.report(f'could not deduce attrs class __init__ signature: {e}')
                func.signature = inspect.Signature()
                func.annotations = {}

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
    r.register_mixin(AttrsClass)
    r.register_post_processor(postProcess)
