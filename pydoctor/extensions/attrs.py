
"""
Support for L{attrs}.
"""

import ast
import inspect

from typing import Dict, List, Optional, cast

from pydoctor import astbuilder, model, astutils, extensions
from pydoctor.extensions._dataclass_like import DataclasLikeClass, DataclassLikeVisitor

import attr

attrs_decorator_signature = inspect.signature(attr.s)
"""Signature of the L{attr.s} class decorator."""

attrib_signature = inspect.signature(attr.ib)
"""Signature of the L{attr.ib} function for defining class attributes."""

builtin_types = frozenset(('frozenset', 'int', 'bytes', 
                           'complex', 'list', 'tuple', 
                           'set', 'dict', 'range'))

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
    
def get_factory(expr: Optional[ast.expr], ctx: model.Documentable) -> Optional[ast.expr]:
    """
    If this AST represent a call to L{attr.Factory}, returns the expression inside the factory call
    """
    if isinstance(expr, ast.Call) and \
        astutils.node2fullname(expr.func, ctx) in ('attrs.Factory', 'attr.Factory'):
        try:
            factory, = expr.args
        except Exception:
            return None
        else:
            return factory
    else:
        return None

def _callable_return_type(dname:List[str], ctx:model.Documentable) -> Optional[ast.expr]:
    """
    Given a callable dotted name in a certain context, 
    get it's return type as ast expression.

    Note that the expression might not be fully 
    resolvable in the new context since it can come from other modules. 
    """
    r = ctx.resolveName('.'.join(dname))
    if isinstance(r, model.Class):
        return astutils.dottedname2node(dname)
    elif isinstance(r, model.Function):
        rtype = r.annotations.get('return')
        if rtype:
            return rtype
    elif r is None and len(dname)==1 and dname[0] in builtin_types:
        return astutils.dottedname2node(dname)
    # TODO: we might be able to use the shpinx inventory yo check if the 
    # provided callable is a class, in which case the class could be linked.
    return None

def _annotation_from_factory(
        factory:ast.expr,
        ctx: model.Documentable,
        ) -> Optional[ast.expr]:
    dname = astutils.node2dottedname(factory)
    if dname:
        return _callable_return_type(dname, ctx)
    else:
        return None

def _annotation_from_converter(
        converter:ast.expr,
        ctx: model.Documentable,
        ) -> Optional[ast.expr]:
    dname = astutils.node2dottedname(converter)
    if dname:
        r = ctx.resolveName('.'.join(dname))
        if isinstance(r, model.Class):
            args = dict(r.constructor_params)
        elif isinstance(r, model.Function):
            args = dict(r.annotations)
        else:
            return None    
        args.pop('return', None)
        if len(args)==1:
            return args.popitem()[1]
    return None
    
def annotation_from_attrib(
        args:inspect.BoundArguments,
        ctx: model.Documentable,
        for_constructor:bool=False
        ) -> Optional[ast.expr]:
    """Get the type of an C{attr.ib} definition.
    @param args: The L{inspect.BoundArguments} of the C{attr.ib()} call.
    @param ctx: The context in which this expression is evaluated.
    @param for_constructor: Whether we're trying to figure out the __init__ parameter annotations
        instead of the attribute annotations.
    @return: A type annotation, or None if the expression is not
                an C{attr.ib} definition or contains no type information.
    """
    if for_constructor:
        # If a converter is defined...
        converter = args.arguments.get('converter')
        if converter is not None:
            return _annotation_from_converter(converter, ctx)
        
    typ = args.arguments.get('type')
    if typ is not None:
        return astutils.unstring_annotation(typ, ctx)
    
    factory = args.arguments.get('factory')
    if factory is not None:
        return _annotation_from_factory(factory, ctx)

    default = args.arguments.get('default')
    if default is not None:
        factory = get_factory(default, ctx)
        if factory is not None:
            return _annotation_from_factory(factory, ctx)
        else:
            return astbuilder._infer_type(default)

    return None

def default_from_attrib(args:inspect.BoundArguments, ctx: model.Documentable) -> Optional[ast.expr]:
    d = args.arguments.get('default')
    f = args.arguments.get('factory')
    if isinstance(d, ast.expr):
        factory = get_factory(d, ctx)
        if factory:
            if astutils.node2dottedname(factory):
                return ast.Call(func=factory, args=[], keywords=[], lineno=d.lineno, col_offset=d.col_offset)
            else:
                return ast.Constant(value=..., lineno=d.lineno, col_offset=d.col_offset)
        return d
    elif isinstance(f, ast.expr):
        if astutils.node2dottedname(f):
            # If a simple factory is defined, the default value is a call to this function
            return ast.Call(func=f, args=[], keywords=[], lineno=f.lineno, col_offset=f.col_offset)
        else:
            # Else we can't figure it out
            return ast.Constant(value=..., lineno=f.lineno, col_offset=f.col_offset)
    else:
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
            attrs_args_value = {name: astutils.get_literal_arg(attrs_args, name, default, 
                                    typecheck, attrs_deco.lineno, mod
                                    ) for name, default, typecheck in 
                                    (('auto_attribs', False, bool),
                                     ('init', True, bool),
                                     ('kw_only', False, bool),)}
            cls.attrs_auto_attribs = attrs_args_value['auto_attribs']
            cls.attrs_init = attrs_args_value['init']
            cls.attrs_kw_only = attrs_args_value['kw_only']
    
    def transformClassVar(self, cls: model.Class, 
                          attr: model.Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        assert isinstance(cls, AttrsClass)
        is_attrs_attrib = is_attrib(value, cls)
        is_attrs_auto_attrib = cls.attrs_auto_attribs and not is_attrs_attrib and annotation is not None
        
        attrib_args = None
        attrib_args_value = {}
        if is_attrs_attrib or is_attrs_auto_attrib:
            
            attr.kind = model.DocumentableKind.INSTANCE_VARIABLE
            if value is not None:
                attrib_args = astutils.safe_bind_args(attrib_signature, value, cls.module)
                if attrib_args:
                    if annotation is None:
                        attr.annotation = annotation_from_attrib(attrib_args, cls)
                
                    attrib_args_value = {name: astutils.get_literal_arg(attrib_args, name, default, 
                                            typecheck, attr.linenumber, cls.module
                                            ) for name, default, typecheck in 
                                            (('init', True, bool),
                                            ('kw_only', False, bool),)}
        
            # Handle the auto-creation of the __init__ method.
            if cls.attrs_init:
                if is_attrs_auto_attrib or (attrib_args and attrib_args_value['init']):    
                    kind:inspect._ParameterKind = inspect.Parameter.POSITIONAL_OR_KEYWORD
                
                    if cls.attrs_kw_only or (attrib_args and attrib_args_value['kw_only']):
                        kind = inspect.Parameter.KEYWORD_ONLY

                    attrs_default:Optional[ast.expr] = ast.Constant(value=...)
                    
                    if is_attrs_auto_attrib:
                        attrs_default = value
                        factory = get_factory(attrs_default, cls)
                        if factory:
                            if astutils.node2dottedname(factory):
                                attrs_default = ast.Call(func=factory, args=[], keywords=[], 
                                                         lineno=factory.lineno, col_offset=factory.col_offset)
                            else:
                                # Factory is not a default value stricly speaking, 
                                # so we give up on trying to figure it out.
                                attrs_default = ast.Constant(value=..., lineno=factory.lineno, 
                                                             col_offset=factory.col_offset)
                    
                    elif attrib_args:
                        attrs_default = default_from_attrib(attrib_args, cls)
                    
                    # attrs strips the leading underscores from the parameter names,
                    # since there is not such thing as a private parameter.
                    init_param_name = attr.name.lstrip('_')

                    if attrib_args:
                        constructor_annotation = cls.attrs_constructor_annotations[init_param_name] = \
                            annotation_from_attrib(attrib_args, cls, for_constructor=True) or annotation
                    else:
                        constructor_annotation = cls.attrs_constructor_annotations[init_param_name] = annotation
                    
                    cls.attrs_constructor_parameters.append(
                        inspect.Parameter(
                            init_param_name, kind=kind, 
                            default=astbuilder._ValueFormatter(attrs_default, cls) 
                                if attrs_default else inspect.Parameter.empty, 
                            annotation=astbuilder._AnnotationValueFormatter(constructor_annotation, cls) 
                                if constructor_annotation else inspect.Parameter.empty))
    
    def isDataclassLike(self, cls:ast.ClassDef, mod:model.Module) -> Optional[object]:
        if any(is_attrs_deco(dec, mod) for dec in cls.decorator_list):
            return self.DATACLASS_LIKE_KIND
        return None

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
        self.attrs_constructor_parameters:List[inspect.Parameter] = []
        self.attrs_constructor_parameters.append(inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD,))
        self.attrs_constructor_annotations: Dict[str, Optional[ast.expr]] = {'self': None}

def postProcess(system:model.System) -> None:

    for cls in list(system.objectsOfType(AttrsClass)):
        # by default attr.s() overrides any defined __init__ mehtod, whereas dataclasses.
        # TODO: but if auto_detect=True, we need to check if __init__ already exists, otherwise it does not replace it.
        # NOTE: But attr.define() use auto_detect=True by default! this is getting complicated...
        if cls.isDataclassLike and cls.attrs_init:
            func = system.Function(system, '__init__', cls)
            system.addObject(func)
            # init Function attributes that otherwise would be undefined :/
            func.decorators = None
            func.is_async = False
            func.parentMod = cls.parentMod
            func.setLineNumber(cls.linenumber)

            parameters = cls.attrs_constructor_parameters
            annotations = cls.attrs_constructor_annotations
            
            # Re-ordering kw_only arguments at the end of the list
            for param in tuple(parameters):
                if param.kind is inspect.Parameter.KEYWORD_ONLY:
                    parameters.remove(param)
                    parameters.append(param)
                    ann = annotations[param.name]
                    del annotations[param.name]
                    annotations[param.name] = ann

            func.annotations = annotations
            try:
                # TODO: collect arguments from super classes attributes definitions.
                func.signature = inspect.Signature(parameters)
            except Exception as e:
                func.report(f'could not deduce attrs class __init__ signature: {e}')
                func.signature = inspect.Signature()
                func.annotations = {}
            else:
                cls.constructors.append(func)

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
    r.register_mixin(AttrsClass)
    r.register_post_processor(postProcess)
