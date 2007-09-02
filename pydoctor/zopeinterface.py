from pydoctor import model, ast_pp, astbuilder
from compiler import ast, visitor
import re

class ZopeInterfaceClass(model.Class):
    isinterface = False
    isschemafield = False
    isinterfaceclass = False
    implementsOnly = False
    implementedby_directly = None # [objects], when isinterface == True
    implementedby_indirectly = None # [objects], when isinterface == True
    def setup(self):
        super(ZopeInterfaceClass, self).setup()
        self.implements_directly = [] # [name of interface]
        self.implements_indirectly = [] # [(interface name, directly implemented)]

class Attribute(model.Documentable):
    kind = "Attribute"
    document_in_parent_page = True

class ZopeInterfaceFunction(model.Function):
    def docsources(self):
        for source in super(ZopeInterfaceFunction, self).docsources():
            yield source
        if not isinstance(self.parent, model.Class):
            return
        for interface in (self.parent.implements_directly +
                          self.parent.implements_indirectly):
            io = self.system.objForFullName(interface)
            if io is not None:
                if self.name in io.contents:
                    yield io.contents[self.name]


def addInterfaceInfoToClass(cls, interfaceargs, implementsOnly):
    cls.implementsOnly = implementsOnly
    if implementsOnly:
        cls.implements_directly = []
    for arg in interfaceargs:
        cls.implements_directly.append(
            cls.dottedNameToFullName(ast_pp.pp(arg)))

schema_prog = re.compile('zope\.schema\.([a-zA-Z_][a-zA-Z0-9_]*)')


class ZopeInterfaceModuleVisitor(astbuilder.ModuleVistor):
    def funcNameFromCall(self, node):
        str_base = ast_pp.pp(node.node)
        return self.builder.current.dottedNameToFullName(str_base)

    def visitAssign(self, node):
        # i would like pattern matching in python please
        # if match(Assign([AssName(?name, _)], CallFunc(?funcName, [Const(?docstring)])), node):
        #     ...
        sup = lambda : super(ZopeInterfaceModuleVisitor, self).visitAssign(node)
        if isinstance(self.builder.current, model.Module) and \
               ast_pp.pp(node) == 'Interface = interface.Interface\n':
            # warner!!!

            n2fn = self.builder.current._name2fullname
            n2fn['Interface'] = 'zope.interface.Interface'
            return sup()
        if len(node.nodes) != 1 or \
               not isinstance(node.nodes[0], ast.AssName) or \
               not isinstance(self.builder.current, model.Class) or \
               not isinstance(node.expr, ast.CallFunc):
            return sup()

        funcName = self.funcNameFromCall(node.expr)

        def pushAttribute(docstring, kind):
            attr = self.builder._push(Attribute, node.nodes[0].name, docstring)
            attr.linenumber = node.lineno
            attr.kind = kind
            if attr.parentMod.sourceHref:
                attr.sourceHref = attr.parentMod.sourceHref + '#L' + \
                                  str(attr.linenumber)
            self.builder._pop(Attribute)

        def handleSchemaField(kind):
            print node.expr
            descriptions = [arg for arg in node.expr.args if isinstance(arg, ast.Keyword)
                            and arg.name == 'description']
            docstring = None
            if len(descriptions) > 1:
                self.builder.system.msg('parsing', 'xxx')
            elif len(descriptions) == 1:
                description = descriptions[0].expr
                if isinstance(description, ast.Const) and isinstance(description.value, str):
                    docstring = description.value
            pushAttribute(docstring, kind)

        if funcName == 'zope.interface.Attribute':
            args = node.expr.args
            if len(args) != 1 or \
                   not isinstance(args[0], ast.Const) or \
                   not isinstance(args[0].value, str):
                return sup()
            docstring = args[0].value
            pushAttribute(args[0].value, "Attribute")
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

    def visitCallFunc_zope_interface_implements(self, funcName, node):
        if not isinstance(self.builder.current, model.Class):
            self.default(node)
            return
        addInterfaceInfoToClass(self.builder.current, node.args,
                                funcName == 'zope.interface.implementsOnly')
    visitCallFunc_zope_interface_implementsOnly = visitCallFunc_zope_interface_implements

    def visitCallFunc_zope_interface_classImplements(self, funcName, node):
        clsname = self.builder.current.dottedNameToFullName(ast_pp.pp(node.args[0]))
        if clsname not in self.system.allobjects:
            self.builder.warning("classImplements on unknown class", clsname)
            return
        cls = self.system.allobjects[clsname]
        addInterfaceInfoToClass(cls, node.args[1:],
                                funcName == 'zope.interface.classImplementsOnly')
    visitCallFunc_zope_interface_classImplementsOnly = visitCallFunc_zope_interface_classImplements


def markInterfaceClass(cls):
    cls.isinterfaceclass = True
    for sc in cls.subclasses:
        markInterfaceClass(sc)

class InterfaceClassFinder(object):
    funcNameFromCall = ZopeInterfaceModuleVisitor.funcNameFromCall.im_func
    def __init__(self, builder, modfullname):
        self.builder = builder
        self.system = builder.system
        self.modfullname = modfullname
        self.newinterfaces = []

    def visitAssign(self, node):
        if len(node.nodes) != 1 or \
               not isinstance(node.nodes[0], ast.AssName) or \
               not isinstance(self.builder.current, model.Module) or \
               not isinstance(node.expr, ast.CallFunc):
            return
        funcName = self.funcNameFromCall(node.expr)
        name = node.nodes[0].name
        args = node.expr.args
        ob = self.system.objForFullName(funcName)
        if ob is not None and isinstance(ob, model.Class) and ob.isinterfaceclass:
            interface = self.builder.pushClass(name, "...")
            print 'new interface', interface
            interface.isinterface = True
            interface.linenumber = node.lineno
            interface.parent.orderedcontents.sort(key=lambda x:x.linenumber)
            self.newinterfaces.append(interface)
            self.builder.popClass()

    def visitFunction(self, node):
        return

    def visitClass(self, node):
        if not isinstance(self.builder.current, model.Module):
            return
        mod = self.builder.current
        if node.name in mod.contents:
            cls = mod.contents[node.name]
        elif node.name in mod._name2fullname:
            cls = self.builder.system.allobjects[mod._name2fullname[node.name]]
        else:
            return
        for i, (bn, bo) in enumerate(zip(cls.bases, cls.baseobjects)):
            if bo is not None:
                continue
            if bn in mod.contents:
                cls.baseobjects[i] = mod.contents[bn]
                cls.bases[i] = mod.fullName() + '.' + bn




class ZopeInterfaceASTBuilder(astbuilder.ASTBuilder):
    ModuleVistor = ZopeInterfaceModuleVisitor

    def popClass(self):
        c = self.current
        for n, o in zip(c.bases, c.baseobjects):
            if schema_prog.match(n) or (o and o.isschemafield):
                c.isschemafield = True
                break
        super(ZopeInterfaceASTBuilder, self).popClass()

class ZopeInterfaceSystem(model.System):
    Class = ZopeInterfaceClass
    Function = ZopeInterfaceFunction
    defaultBuilder = ZopeInterfaceASTBuilder

    def _finalStateComputations(self):
        super(ZopeInterfaceSystem, self)._finalStateComputations()
        builder = self.defaultBuilder(self)
        for cls in self.objectsOfType(model.Class):
            if 'zope.interface.interface.InterfaceClass' in cls.bases:
                markInterfaceClass(cls)

        newinterfaces = []
        for mod in self.objectsOfType(model.Module):
            if not hasattr(mod, 'filepath'):
                continue
            builder.push(mod)
            try:
                icf = InterfaceClassFinder(builder, mod.fullName())
                ast = builder.parseFile(mod.filepath)
                if not ast:
                    continue
                visitor.walk(ast, icf)
            finally:
                builder.pop(mod)
            newinterfaces.extend(icf.newinterfaces)

        newinterfacemap = dict([(i.fullName(), i) for i in newinterfaces])
        for cls in self.objectsOfType(model.Class):
            for i, b in enumerate(cls.bases):
                if b in newinterfacemap:
                    assert (cls.baseobjects[i] is None or
                            cls.baseobjects[i] is newinterfacemap[b])
                    cls.baseobjects[i] = newinterfacemap[b]
                    newinterfacemap[b].subclasses.append(cls)

        for newi in newinterfaces:
            self.markInterface(newi)
        for cls in self.objectsOfType(model.Class):
            if 'zope.interface.Interface' in cls.bases:
                self.markInterface(cls)
            for baseOb in cls.baseobjects:
                if baseOb and baseOb.system is not self and baseOb.isinterface:
                    self.markInterface(cls)

        for cls in self.objectsOfType(model.Class):
            if cls.isinterface or len(cls.baseobjects) != cls.baseobjects.count(None):
                continue
            self.push_implements_info(cls, cls.implements_directly)

        for cls in self.objectsOfType(model.Class):
            for interface in cls.implements_directly:
                interface_ob = self.objForFullName(interface)
                if interface_ob is not None:
                    if interface_ob.implementedby_directly is None:
                        builder.warning("probable interface not marked as such",
                                     interface_ob.fullName())
                        interface_ob.implementedby_directly = []
                        interface_ob.implementedby_indirectly = []
                    interface_ob.implementedby_directly.append(cls.fullName())
            for interface in cls.implements_indirectly:
                interface_ob = self.objForFullName(interface)
                if interface_ob is not None:
                    if interface_ob.implementedby_indirectly is None:
                        builder.warning("probable interface not marked as such",
                                     interface_ob.fullName())
                        interface_ob.implementedby_directly = []
                        interface_ob.implementedby_indirectly = []
                    interface_ob.implementedby_indirectly.append(cls.fullName())

    def markInterface(self, cls):
        cls.isinterface = True
        cls.kind = "Interface"
        cls.implementedby_directly = []
        cls.implementedby_indirectly = []
        for sc in cls.subclasses:
            if '.test.' not in sc.fullName():
                self.markInterface(sc)

    def push_implements_info(self, cls, interfaces):
        for ob in cls.subclasses:
            for interface in interfaces:
                if interface not in ob.implements_indirectly:
                    ob.implements_indirectly.append(interface)
            if ob.implementsOnly:
                ob.implements_indirectly = []
                newinterfaces = ob.implements_directly
            else:
                newinterfaces = interfaces + ob.implements_directly
            self.push_implements_info(ob, newinterfaces)
