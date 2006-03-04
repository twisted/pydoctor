from docextractor import model
from docextractor import ast_pp

class TwistedClass(model.Class):
    isinterface = False
    implementsOnly = False
    implementedby_directly = None # [objects], when isinterface == True
    implementedby_indirectly = None # [objects], when isinterface == True
    def setup(self):
        super(TwistedClass, self).setup()
        self.implements_directly = [] # [name of interface]
        self.implements_indirectly = [] # [(interface name, directly implemented)]

def addInterfaceInfoToClass(cls, interfaceargs, implementsOnly):
    cls.implementsOnly = implementsOnly
    if implementsOnly:
        cls.implements_directly = []
    for arg in interfaceargs:
        cls.implements_directly.append(
            cls.dottedNameToFullName(ast_pp.pp(arg)))


class TwistedModuleVisitor(model.ModuleVistor):
    def visitCallFunc(self, node):
        current = self.system.current
        str_base = ast_pp.pp(node.node)
        base = self.system.current.dottedNameToFullName(str_base)
        if base in ['zope.interface.implements', 'zope.interface.implementsOnly']:
            if not isinstance(current, model.Class):
                self.default(node)
                return
            addInterfaceInfoToClass(current, node.args,
                                    base == 'zope.interface.implementsOnly')
        elif base in ['zope.interface.classImplements',
                      'zope.interface.classImplementsOnly']:
            clsname = current.dottedNameToFullName(ast_pp.pp(node.args[0]))
            if clsname not in self.system.allobjects:
                self.system.warning("classImplements on unknown class", clsname)
                return
            cls = self.system.allobjects[clsname]
            addInterfaceInfoToClass(cls, node.args[1:],
                                    base == 'zope.interface.classImplementsOnly')


class TwistedSystem(model.System):
    Class = TwistedClass
    ModuleVistor = TwistedModuleVisitor

    def finalStateComputations(self):
        tpc = 'twisted.python.components'
        if tpc in self.allobjects:
            self.push(self.allobjects[tpc])
            self.pushClass('Interface', None)
            self.popClass()
            self.pop(self.allobjects[tpc])
        super(TwistedSystem, self).finalStateComputations()

        if tpc in self.allobjects:
            self.markInterface(self.allobjects[tpc+'.Interface'])
        for cls in self.objectsOfType(model.Class):
            if 'zope.interface.Interface' in cls.bases:
                self.markInterface(cls)

        for cls in self.objectsOfType(model.Class):
            if cls.isinterface or len(cls.baseobjects) != cls.baseobjects.count(None):
                continue
            self.push_implements_info(cls, cls.implements_directly)

        for cls in self.objectsOfType(model.Class):
            for interface in cls.implements_directly:
                if interface in self.allobjects and '.test.' not in interface:
                    interface_ob = self.allobjects[interface]
                    if interface_ob.implementedby_directly is None:
                        self.warning("probable interface not marked as such",
                                     interface_ob.fullName())
                        interface_ob.implementedby_directly = []
                        interface_ob.implementedby_indirectly = []
                    interface_ob.implementedby_directly.append(cls.fullName())
            for interface in cls.implements_indirectly:
                if interface in self.allobjects and '.test.' not in interface:
                    interface_ob = self.allobjects[interface]
                    if interface_ob.implementedby_indirectly is None:
                        self.warning("probable interface not marked as such",
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
            ob.implements_indirectly.extend(interfaces)
            if ob.implementsOnly:
                ob.implements_indirectly = []
                newinterfaces = ob.implements_directly
            else:
                newinterfaces = interfaces + ob.implements_directly
            self.push_implements_info(ob, newinterfaces)
