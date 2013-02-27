"""Support for Zope interfaces."""

from pydoctor import model, ast_pp, astbuilder
from compiler import ast
import re
import pytest

class ZopeInterfaceClass(model.Class):
    isinterface = False
    isschemafield = False
    isinterfaceclass = False
    implementsOnly = False
    implementedby_directly = None # [objects], when isinterface == True
    def setup(self):
        super(ZopeInterfaceClass, self).setup()
        self.implements_directly = [] # [name of interface]

    @property
    def allImplementedInterfaces(self):
        """Return all the interfaces implemented by this class.

        This returns them in something like the classic class MRO.
        """
        r = list(self.implements_directly)
        if self.implementsOnly:
            return r
        for b in self.baseobjects:
            if b is None:
                continue
            for interface in b.allImplementedInterfaces:
                if interface not in r:
                    r.append(interface)
        return r

    @property
    def allImplementations(self):
        r = list(self.implementedby_directly)
        stack = [self.system.objForFullName(n) for n in r]
        while stack:
            c = stack.pop(0)
            for sc in c.subclasses:
                if sc.implementsOnly:
                    continue
                stack.append(sc)
                if sc.fullName() not in r:
                    r.append(sc.fullName())
        return r


class ZopeInterfaceFunction(model.Function):
    def docsources(self):
        for source in super(ZopeInterfaceFunction, self).docsources():
            yield source
        if not isinstance(self.parent, (model.Class, model.Module)):
            return
        for interface in self.parent.allImplementedInterfaces:
            io = self.system.objForFullName(interface)
            if io is not None:
                for io2 in io.allbases(include_self=True):
                    if self.name in io2.contents:
                        yield io2.contents[self.name]

def addInterfaceInfoToModule(module, interfaceargs):
#    pytest.set_trace()
    for arg in interfaceargs:
        if not isinstance(arg, tuple):
            fullName = module.expandName(ast_pp.pp(arg))
        else:
            fullName = arg[1]
        module.implements_directly.append(fullName)
        obj = module.system.objForFullName(fullName)
        if obj is not None:
            if not obj.isinterface:
                obj.system.msg(
                    'zopeinterface',
                    'probable interface %r not marked as such'%obj,
                    thresh=1)
                obj.isinterface = True
                obj.kind = "Interface"
                obj.implementedby_directly = []
            obj.implementedby_directly.append(module.fullName())

def addInterfaceInfoToClass(cls, interfaceargs, implementsOnly):
    cls.implementsOnly = implementsOnly
    if implementsOnly:
        cls.implements_directly = []
    for arg in interfaceargs:
        if not isinstance(arg, tuple):
            fullName = cls.expandName(ast_pp.pp(arg))
        else:
            fullName = arg[1]
        cls.implements_directly.append(fullName)
        obj = cls.system.objForFullName(fullName)
        if obj is not None:
            if not obj.isinterface:
                obj.system.msg(
                    'zopeinterface',
                    'probable interface %r not marked as such'%obj,
                    thresh=1)
                obj.isinterface = True
                obj.kind = "Interface"
                obj.implementedby_directly = []
            obj.implementedby_directly.append(cls.fullName())


schema_prog = re.compile('zope\.schema\.([a-zA-Z_][a-zA-Z0-9_]*)')
interface_prog = re.compile(
    'zope\.schema\.interfaces\.([a-zA-Z_][a-zA-Z0-9_]*)'
    '|zope\.interface\.Interface')

def namesInterface(system, name):
    if interface_prog.match(name):
        return True
    obj = system.objForFullName(name)
    if not obj or not isinstance(obj, model.Class):
        return False
    return obj.isinterface

def extractAttributeDescription(node):
    pass

def extractSchemaDescription(node):
    pass

class ZopeInterfaceModuleVisitor(astbuilder.ModuleVistor):

    schema_like_patterns = [
        ('zope\.interface\.Attribute', extractAttributeDescription),
        ]

    def funcNameFromCall(self, node):
        str_base = ast_pp.pp(node.node)
        return self.builder.current.expandName(str_base)

    def visitAssign(self, node):
        # i would like pattern matching in python please
        # if match(Assign([AssName(?name, _)], CallFunc(?funcName, [Const(?docstring)])), node):
        #     ...
        sup = lambda : super(ZopeInterfaceModuleVisitor, self).visitAssign(node)
        if len(node.nodes) != 1 or \
               not isinstance(node.nodes[0], ast.AssName) or \
               not isinstance(node.expr, ast.CallFunc):
            return sup()

        funcName = self.funcNameFromCall(node.expr)

        if isinstance(self.builder.current, model.Module):
            name = node.nodes[0].name
            args = node.expr.args
            ob = self.system.objForFullName(funcName)
            if ob is not None and isinstance(ob, model.Class) and ob.isinterfaceclass:
                interface = self.builder.pushClass(name, "...")
                self.builder.system.msg('parsing', 'new interface')
                interface.isinterface = True
                interface.implementedby_directly = []
                interface.linenumber = node.lineno
                self.builder.popClass()
            return sup()
        elif not isinstance(self.builder.current, model.Class):
            return sup()

        def pushAttribute(docstring, kind):
            attr = self.builder._push(model.Attribute, node.nodes[0].name, docstring)
            attr.linenumber = node.lineno
            attr.kind = kind
            if attr.parentMod.sourceHref:
                attr.sourceHref = attr.parentMod.sourceHref + '#L' + \
                                  str(attr.linenumber)
            self.builder._pop(model.Attribute)

        def extractStringLiteral(node):
            if isinstance(node, ast.Const) and isinstance(node.value, str):
                return node.value
            elif isinstance(node, ast.CallFunc) \
                  and isinstance(node.node, ast.Name) \
                  and node.node.name == '_' \
                  and len(node.args) == 1 \
                  and isinstance(node.args[0], ast.Const) \
                  and isinstance(node.args[0].value, str):
                return node.args[0].value

        def handleSchemaField(kind):
            #print node.expr
            descriptions = [arg for arg in node.expr.args if isinstance(arg, ast.Keyword)
                            and arg.name == 'description']
            docstring = None
            if len(descriptions) > 1:
                self.builder.system.msg('parsing', 'xxx')
            elif len(descriptions) == 1:
                docstring = extractStringLiteral(descriptions[0].expr)
            pushAttribute(docstring, kind)

        if funcName == 'zope.interface.Attribute':
            args = node.expr.args
            if len(args) != 1:
                return sup()
            pushAttribute(extractStringLiteral(args[0]), "Attribute")
            return sup()

        if schema_prog.match(funcName):
            kind = schema_prog.match(funcName).group(1)
            handleSchemaField(kind)
            return sup()

        cls = self.builder.system.objForFullName(funcName)
        if cls and isinstance(cls, ZopeInterfaceClass) and cls.isschemafield:
            handleSchemaField(cls.name)
        return sup()

    def visitCallFunc(self, node):
        base = self.funcNameFromCall(node)
        meth = getattr(self, "visitCallFunc_" + base.replace('.', '_'), None)
        if meth is not None:
            meth(base, node)

    def visitCallFunc_zope_interface_moduleProvides(self, funcName, node):
        if not isinstance(self.builder.current, model.Module):
            self.default(node)
            return

        addInterfaceInfoToModule(self.builder.current, node.args)

    def visitCallFunc_zope_interface_implements(self, funcName, node):
        if not isinstance(self.builder.current, model.Class):
            self.default(node)
            return
        addInterfaceInfoToClass(self.builder.current, node.args,
                                funcName == 'zope.interface.implementsOnly')
    visitCallFunc_zope_interface_implementsOnly = visitCallFunc_zope_interface_implements

    def visitCallFunc_zope_interface_classImplements(self, funcName, node):
        clsname = self.builder.current.expandName(
            ast_pp.pp(node.args[0]))
        if clsname not in self.system.allobjects:
            self.builder.system.msg(
                "parsing",
                "classImplements on unknown class %r"%clsname)
            return
        cls = self.system.allobjects[clsname]
        addInterfaceInfoToClass(cls, node.args[1:],
                                funcName == 'zope.interface.classImplementsOnly')
    visitCallFunc_zope_interface_classImplementsOnly = visitCallFunc_zope_interface_classImplements

    def visitClass(self, node):
        super(ZopeInterfaceModuleVisitor, self).visitClass(node)
        cls = self.builder.current.contents[node.name]
        if 'zope.interface.interface.InterfaceClass' in cls.bases:
            cls.isinterfaceclass = True
        if len([b for b in cls.bases
                if namesInterface(self.system, b)]) > 0:
            cls.isinterface = True
            cls.kind = "Interface"
            cls.implementedby_directly = []
        for n, o in zip(cls.bases, cls.baseobjects):
            if schema_prog.match(n) or (o and o.isschemafield):
                cls.isschemafield = True
        for ((dn, fn, o), args) in cls.decorators:
            if fn == 'zope.interface.implementer':
                addInterfaceInfoToClass(cls, args, False)


class ZopeInterfaceModule(model.Module):
    def setup(self):
        super(ZopeInterfaceModule, self).setup()
        self.implements_directly = [] # [name of interface]

    @property
    def allImplementedInterfaces(self):
        """Return all the interfaces implemented by this class.

        This returns them in something like the classic class MRO.
        """
        return list(self.implements_directly)


class ZopeInterfaceASTBuilder(astbuilder.ASTBuilder):
    ModuleVistor = ZopeInterfaceModuleVisitor


class ZopeInterfaceSystem(model.System):
    Module = ZopeInterfaceModule
    Class = ZopeInterfaceClass
    Function = ZopeInterfaceFunction
    defaultBuilder = ZopeInterfaceASTBuilder
