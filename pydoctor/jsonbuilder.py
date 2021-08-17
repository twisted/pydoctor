"""
Load and dump Documentables instances from and to JSON with the L{docspec} specification. 
"""

import ast
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union, cast
from inspect import Parameter, Signature, _empty

import astor
import attr
from pydoctor import model, docspec, epydoc2stan, astbuilder, visitor

# TODO: move this to astuils.py when PR #? has been merged
def extract_expr(_ast: ast.Module) -> ast.expr:
    elem = _ast.body[0]
    assert isinstance(elem, ast.Expr)
    return elem.value

@attr.s(auto_attribs=True)
class BuilderVisitor(visitor.Visitor[docspec.ApiObject]):
    builder: 'JSONBuilder'

    def visit_Data(self, data: docspec.Data) -> None:
        """
        Data entry may represent an indirecton (import) or an actual attribute!
        """
        if data.kind is docspec.ApiObject.Kind.INDIRECTION:
            assert isinstance(self.builder.current, model.CanContainImportsDocumentable)
            assert data.value is not None
            self.builder.current._localNameToFullName_map[data.name] = data.value
            return

        obj = self.builder.addAttribute(data.name, 
            getattr(model.DocumentableKind, data.kind.name), 
            self.builder.current)
        
        lineno = None
        if data.location is not None:
            lineno = data.location.lineno
        self.builder.push(obj, lineno)

        if data.docstring is not None:
            obj.setDocstring(data.docstring)
            obj.parsed_docstring = epydoc2stan.parse_docstring(obj, data.docstring, obj)
        
        if data.datatype is not None:
            obj.annotation = extract_expr(ast.parse(data.datatype))
        # TODO: Add decorators: Optional[List[str]] to docspec.Data.
    
    def visit_Function(self, function: docspec.Function) -> None:
        """
        """
        lineno = None
        if function.location is not None:
            lineno = function.location.lineno
        obj = self.builder.pushFunction(function.name, lineno)

        obj.kind = getattr(model.DocumentableKind, function.kind.name)

        if function.docstring is not None:
            obj.setDocstring(function.docstring)
            obj.parsed_docstring = epydoc2stan.parse_docstring(obj, function.docstring, obj)

        obj.is_async = function.modifiers is not None and 'async' in function.modifiers

        # signature
        signature_builder = astbuilder.SignatureBuilder()
        for argument in (a for a in function.args if a.type is docspec.Argument.Type.POSITIONAL_ONLY):
            signature_builder.add_arg(argument.name, Parameter.POSITIONAL_ONLY, 
                default=extract_expr(ast.parse(argument.default_value)) if argument.default_value else None)
        for argument in (a for a in function.args if a.type is docspec.Argument.Type.POSITIONAL_OR_KEYWORD):
            signature_builder.add_arg(argument.name, Parameter.POSITIONAL_OR_KEYWORD, 
                default=extract_expr(ast.parse(argument.default_value)) if argument.default_value else None)
        for argument in (a for a in function.args if a.type is docspec.Argument.Type.VAR_POSITIONAL):
            signature_builder.add_arg(argument.name, Parameter.VAR_POSITIONAL, default=None)
        for argument in (a for a in function.args if a.type is docspec.Argument.Type.KEYWORD_ONLY):
            signature_builder.add_arg(argument.name, Parameter.KEYWORD_ONLY, 
                default=extract_expr(ast.parse(argument.default_value)) if argument.default_value else None)
        for argument in (a for a in function.args if a.type is docspec.Argument.Type.VAR_KEYWORD):
            signature_builder.add_arg(argument.name, Parameter.VAR_KEYWORD, default=None)
        try:
            signature = signature_builder.get_signature()
        except ValueError as ex:
            obj.report(f'{obj.fullName()} has invalid parameters: {ex}')
            signature = Signature()

        obj.signature = signature
        
        # annotations
        annotations: Dict[str,ast.expr] = {}
        for argument in function.args:
            if argument.datatype is not None:
                annotations[argument.name] = extract_expr(ast.parse(argument.datatype))
        if function.return_type is not None:
            annotations['return'] = extract_expr(ast.parse(function.return_type))

        obj.annotations = annotations

        # decorators
        decorators: Optional[List[ast.expr]] = None
        if function.decorators is not None:
            decorators = []
            for deco in function.decorators:
                decorators.append(extract_expr(ast.parse(deco)))
        obj.decorators = decorators
    
    def visit_Class(self, class_: docspec.Class) -> None:
        """
        """
        lineno = None
        if class_.location is not None:
            lineno = class_.location.lineno
        obj = self.builder.pushClass(class_.name, lineno)

        obj.kind = getattr(model.DocumentableKind, class_.kind.name)

        if class_.docstring is not None:
            obj.setDocstring(class_.docstring)
            obj.parsed_docstring = epydoc2stan.parse_docstring(obj, class_.docstring, obj)

        # bases
        rawbases = []
        bases = []
        baseobjects = []
        if class_.bases is not None:
            rawbases = class_.bases
            for str_base in rawbases:
                full_name = self.builder.current.expandName(str_base)
                bases.append(full_name)
                baseobj = self.builder.system.objForFullName(full_name)
                if not isinstance(baseobj, model.Class):
                    baseobj = None
                baseobjects.append(baseobj)
        obj.rawbases = rawbases
        obj.bases = bases
        obj.baseobjects = baseobjects

        # raw decorators
        raw_decorators: Optional[List[ast.expr]] = None
        if class_.decorators is not None:
            raw_decorators = []
            for deco in class_.decorators:
                raw_decorators.append(extract_expr(ast.parse(deco)))
            obj.raw_decorators = raw_decorators
        else:
            obj.raw_decorators = []
        
        # decorators
        obj.decorators = []
        for decnode in obj.raw_decorators:
            args: Optional[Sequence[ast.expr]]
            if isinstance(decnode, ast.Call):
                base = astbuilder.node2fullname(decnode.func, self.builder.current)
                args = decnode.args
                if base in ('attr.s', 'attr.attrs', 'attr.attributes'):
                    obj.auto_attribs |= astbuilder._uses_auto_attribs(decnode, self.builder.current.module)
            else:
                base = astbuilder.node2fullname(decnode, self.builder.current)
                args = None
            if base is None:  # pragma: no cover
                # There are expressions for which node2fullname() returns None,
                # but I cannot find any that don't lead to a SyntaxError
                # when used in a decorator.
                obj.report("cannot make sense of class decorator")
            else:
                obj.decorators += [(base, args)]
        
        # subclasses
        for b in obj.baseobjects:
            if b is not None:
                b.subclasses.append(obj)

    def visit_Module(self, module: docspec.Module) -> None:
        """
        """
        is_package = module.kind is docspec.ApiObject.Kind.PACKAGE

        if module.location and module.location.filename:
            modpath: Optional[Path] = Path(module.location.filename)
        else:
            modpath = None
        
        factory = self.builder.system.Package if is_package else self.builder.system.Module
        obj = factory(self.builder.system, module.name, self.builder.current, modpath)
        self.builder.system.addObject(obj)
        self.builder.push(obj)

        if module.docstring is not None:
            obj.setDocstring(module.docstring)
            obj.parsed_docstring = epydoc2stan.parse_docstring(obj, module.docstring, obj)
        
        if modpath:
            self.builder.system.setSourceHref(obj, modpath)

    def unknown_departure(self, obj: docspec.ApiObject) -> None:
        if obj.kind is not docspec.ApiObject.Kind.INDIRECTION:
            assert obj.full_name == self.builder.current.fullName(), f"{self.builder.current.fullName()} is not {obj.full_name}"
            self.builder.pop(self.builder.current)

@attr.s(auto_attribs=True)
class JSONBuilder(astbuilder.BaseBuilder):
    system: model.System
    BuilderVisitor = BuilderVisitor
    
    def processModule(self, mod_spec: docspec.Module) -> None:
        v = self.BuilderVisitor(self)
        visitor.walkabout(mod_spec, v, 
            get_children=lambda ob: ob.members if isinstance(ob, docspec.HasMembers) else ())

@attr.s(auto_attribs=True)
class SerializerVisitor(visitor.Visitor[model.Documentable]):
    serializer: 'JSONSerializer'
    spec: docspec.Module = attr.ib(default=None, init=False)

    current : docspec.ApiObject = attr.ib(default=None, init=False)
    _stack: List[docspec.ApiObject] = attr.ib(factory=list, init=False)

    def push(self, ob: docspec.ApiObject) -> None:
        self._stack.append(self.current)
        self.current = ob

    def pop(self, ob: docspec.ApiObject) -> None:
        self.current = self._stack.pop()
    
    def enter_object(self, ob: docspec.ApiObject) -> None:
        if self.current:
            assert isinstance(self.current, docspec.HasMembers)
            self.current.members.append(ob)
            self.spec.sync_hierarchy()
        else:
            assert isinstance(ob, docspec.Module)
            self.spec = ob
        self.push(ob)

    def unknown_departure(self, obj: model.Documentable) -> None:
        assert self.current.full_name == obj.fullName() , f"{obj.fullName()} is not {self.current.full_name}"
        self.pop(self.current)

    def visit_Attribute(self, ob: model.Attribute) -> None:
        spec = self.serializer.Data(name=ob.name, 
            location=docspec.Location(str(ob.module.source_path) if ob.module.source_path else '', ob.linenumber), 
            docstring=ob.docstring, 
            kind=getattr(docspec.ApiObject.Kind, ob.kind.name),
            datatype=astor.to_source(ob.annotation) if ob.annotation else None, 
            value=astor.to_source(getattr(ob, 'value')) if getattr(ob, 'value', None) else None, # TODO change once #397 is merged.
            )
        self.enter_object(spec)

    def visit_Function(self, ob: model.Function) -> None:
        modifiers = []
        args=[]

        # modifier, only used for async currently
        if ob.is_async:
            modifiers.append('async')

        # args
        for name, param in ob.signature.parameters.items():
            
            datatype = None
            raw_datatype: Optional[ast.expr] = (ob.annotations or {}).get(name)
            if raw_datatype:
                datatype = astor.to_source(raw_datatype)
            
            default_value = None
            if param.default and param.default is not _empty:
                default_value = astor.to_source(param.default.value)

            args.append(docspec.Argument(name=name, 
                                         type=getattr(docspec.Argument.Type, param.kind.name),
                                         datatype=datatype, 
                                         default_value=default_value))

        # decorators
        if ob.decorators:
            decorators: Optional[List[str]] = []
            for deco in ob.decorators:
                cast(List[str], decorators).append(astor.to_source(deco))
        else:
            decorators = None
        
        # return type
        return_type = None
        if ob.annotations:
            rtype = ob.annotations.get('return')
            return_type = astor.to_source(rtype) if rtype else None

        spec = self.serializer.Function(name=ob.name, 
            location=docspec.Location(str(ob.module.source_path) if ob.module.source_path else '', ob.linenumber), 
            docstring=ob.docstring, 
            kind=getattr(docspec.ApiObject.Kind, ob.kind.name),
            modifiers=modifiers,
            args=args, 
            decorators=decorators,
            return_type=return_type
            )
        self.enter_object(spec)
    
    def visit_Class(self, ob: model.Class) -> None:
        
        # decorators
        if ob.raw_decorators:
            decorators: Optional[List[str]] = []
            for deco in ob.raw_decorators:
                cast(List[str], decorators).append(astor.to_source(deco))
        else:
            decorators = None

        spec = self.serializer.Class(ob.name, 
            location=docspec.Location(str(ob.module.source_path) if ob.module.source_path else '', ob.linenumber), 
            docstring=ob.docstring, 
            kind=getattr(docspec.ApiObject.Kind, ob.kind.name),
            bases=ob.rawbases,
            decorators=decorators,
            members=[])

        self.enter_object(spec)
        self.add_indirections(spec, ob)
        self.spec.sync_hierarchy()
    
    def visit_Module(self, ob: model.Module) -> None:
        spec = self.serializer.Module(name=ob.name, 
            location=docspec.Location(str(ob.module.source_path) if ob.module.source_path else '', ob.linenumber),
            docstring=ob.docstring, 
            kind=getattr(docspec.ApiObject.Kind, ob.kind.name),
            members=[],
            all=list(ob.all),
            docformat=ob.docformat
        )
        self.enter_object(spec)
        self.add_indirections(spec, ob)
        self.spec.sync_hierarchy()

    visit_Package = visit_Module

    def add_indirections(self, spec:Union[docspec.Module, docspec.Class], ob: model.CanContainImportsDocumentable) -> None:
        for name, value in ob._localNameToFullName_map.items():
            indirection = self.serializer.Data(name=name, 
                location=spec.location, 
                docstring=None, 
                kind=docspec.ApiObject.Kind.INDIRECTION,
                value=value
            )
            spec.members.append(indirection)

@attr.s(auto_attribs=True)
class JSONSerializer:

    modules_spec: List[docspec.Module] = attr.ib(factory=list, init=False)
    
    SerializerVisitor = SerializerVisitor
    Class = docspec.Class
    Data = docspec.Data
    Function = docspec.Function
    Module = docspec.Module
    System = docspec.System
    
    def processModule(self, mod: model.Module) -> None:
        v = self.SerializerVisitor(self)
        visitor.walkabout(mod, v, get_children=lambda ob: ob.contents.values())
        self.modules_spec.append(v.spec)

model.System.defaultJSONBuilder = JSONBuilder
model.System.defaultJSONSerializer = JSONSerializer

