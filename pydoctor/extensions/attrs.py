
"""
Support for L{attrs}.
"""

import ast
import inspect

from typing import Dict, List, Optional, Tuple, TypedDict, cast

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
            return astutils.dottedname2node(['object'])
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
                return ast.Call(func=factory, args=[], keywords=[], lineno=d.lineno)
            else:
                return ast.Constant(value=..., lineno=d.lineno)
        return d
    elif isinstance(f, ast.expr):
        if astutils.node2dottedname(f):
            # If a simple factory is defined, the default value is a call to this function
            return ast.Call(func=f, args=[], keywords=[], lineno=f.lineno)
        else:
            # Else we can't figure it out
            return ast.Constant(value=..., lineno=f.lineno)
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
        if not isinstance(cls, AttrsClass) or cls.dataclassLike != self.DATACLASS_LIKE_KIND:
            # not an attrs class
            return
        mod = cls.module
        try:
            attrs_deco = next(decnode for decnode in node.decorator_list 
                              if is_attrs_deco(decnode, mod))
        except StopIteration:
            return

        attrs_args = astutils.safe_bind_args(attrs_decorator_signature, attrs_deco, mod)
        if attrs_args:
            cls.attrs_options.update({name: astutils.get_literal_arg(attrs_args, name, default, 
                                    typecheck, attrs_deco.lineno, mod
                                    ) for name, default, typecheck in 
                                    (('auto_attribs', False, bool),
                                     ('init', None, (bool, type(None))),
                                     ('kw_only', False, bool),
                                     ('auto_detect', False, bool), )})
    
    def transformClassVar(self, cls: model.Class, 
                          attr: model.Attribute, 
                          annotation:Optional[ast.expr],
                          value:Optional[ast.expr]) -> None:
        assert isinstance(cls, AttrsClass)
        is_attrs_attrib = is_attrib(value, cls)
        is_attrs_auto_attrib = cls.attrs_options['auto_attribs'] and not is_attrs_attrib and annotation is not None
        
        
        if not (is_attrs_attrib or is_attrs_auto_attrib):
            return
        
        attrib_args = None
        attrib_args_value = {}

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
        if cls.attrs_options['init'] in (True, None) and is_attrs_auto_attrib or attrib_args_value.get('init'):    
            kind:inspect._ParameterKind = inspect.Parameter.POSITIONAL_OR_KEYWORD
        
            if cls.attrs_options['kw_only'] or attrib_args_value.get('kw_only'):
                kind = inspect.Parameter.KEYWORD_ONLY

            attrs_default:Optional[ast.expr] = ast.Constant(value=..., lineno=attr.linenumber)
            
            if is_attrs_auto_attrib:
                factory = get_factory(value, cls)
                if factory:
                    if astutils.node2dottedname(factory):
                        attrs_default = ast.Call(func=factory, args=[], keywords=[], lineno=factory.lineno)
                    
                    # else, the factory is not a simple function/class name, 
                    # so we give up on trying to figure it out.
                else:
                    attrs_default = value
            
            elif attrib_args:
                attrs_default = default_from_attrib(attrib_args, cls)
            
            # attrs strips the leading underscores from the parameter names,
            # since there is not such thing as a private parameter.
            init_param_name = attr.name.lstrip('_')

            if attrib_args:
                constructor_annotation = annotation_from_attrib(attrib_args, cls, for_constructor=True) or annotation
            else:
                constructor_annotation = annotation
            
            cls.attrs_constructor_annotations[init_param_name] = constructor_annotation
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

class AttrsOptions(TypedDict):
    auto_attribs: bool
    """
    L{True} if this class uses the C{auto_attribs} feature of the L{attrs}
    library to automatically convert annotated fields into attributes.
    """

    kw_only: bool
    """
    C{True} is this class uses C{kw_only} feature of L{attrs <attr>} library.
    """

    init: Optional[bool]
    """
    False if L{attrs <attr>} is not generating an __init__ method for this class.
    """

    auto_detect:bool

class AttrsClass(DataclasLikeClass, model.Class):
    def setup(self) -> None:
        super().setup()

        self.attrs_options:AttrsOptions = {'init':None, 'auto_attribs':False, 
                                           'kw_only':False, 'auto_detect':False}
        self.attrs_constructor_parameters:List[inspect.Parameter] = [
            inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD,)]
        self.attrs_constructor_annotations: Dict[str, Optional[ast.expr]] = {'self': None}

def collect_inherited_constructor_params(cls:AttrsClass) -> Tuple[List[inspect.Parameter], 
                                                    Dict[str, Optional[ast.expr]]]:
    # see https://github.com/python-attrs/attrs/pull/635/files

    base_attrs:List[inspect.Parameter] = []
    base_annotations:Dict[str, Optional[ast.expr]] = {}
    own_attr_names = cls.attrs_constructor_annotations

    # Traverse the MRO and collect attributes.
    for base_cls in reversed(cls.mro(include_external=False, include_self=False)):
        assert isinstance(base_cls, AttrsClass)
        for (name, ann),p in zip(base_cls.attrs_constructor_annotations.items(), 
                       base_cls.attrs_constructor_parameters):
            if name == 'self' or name in own_attr_names:
                continue

            base_attrs.append(p)
            base_annotations[name] = ann

    # For each name, only keep the freshest definition i.e. the furthest at the
    # back.  base_annotations is fine because it gets overwritten with every new
    # instance.
    filtered:List[inspect.Parameter] = []
    seen = set()
    for a in reversed(base_attrs):
        if a.name in seen:
            continue
        filtered.insert(0, a)
        seen.add(a.name)

    return filtered, base_annotations

def postProcess(system:model.System) -> None:

    for cls in list(system.objectsOfType(AttrsClass)):
        # by default attr.s() overrides any defined __init__ mehtod, whereas dataclasses.
        # TODO: but if auto_detect=True, we need to check if __init__ already exists, otherwise it does not replace it.
        # NOTE: But attr.define() use auto_detect=True by default! this is getting complicated...
        if cls.dataclassLike == ModuleVisitor.DATACLASS_LIKE_KIND:
            
            if cls.attrs_options['init'] is False or \
                cls.attrs_options['init'] is None and \
                cls.attrs_options['auto_detect'] is True and \
                cls.contents.get('__init__'):
                continue

            func = system.Function(system, '__init__', cls)
            # init Function attributes that otherwise would be undefined :/
            func.parentMod = cls.parentMod
            func.decorators = None
            func.is_async = False
            func.parentMod = cls.parentMod
            system.addObject(func)
            func.setLineNumber(cls.linenumber)

            # collect arguments from super classes attributes definitions.
            inherited_params, inherited_annotations = collect_inherited_constructor_params(cls)
            parameters = [cls.attrs_constructor_parameters[0], *inherited_params, *cls.attrs_constructor_parameters[1:]]
            annotations = {**inherited_annotations, **cls.attrs_constructor_annotations}
            
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
