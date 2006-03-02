from docextractor import model
from docextractor import ast_pp

class TwistedClass(model.Class):
    isinterface = False
    implementsOnly = False
    def setup(self):
        super(TwistedClass, self).setup()
        self.implements = [] # [name of interface]
        self.allimplements = [] # [(interface name, directly implemented)]
        self.implementedby = [] # [objects]

def addInterfaceInfoToClass(cls, interfaceargs, implementsOnly):
    cls.implementsOnly = implementsOnly
    for arg in interfaceargs:
        cls.implements.append(
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
        super(TwistedSystem, self).finalStateComputations()
        if tpc in self.allobjects:
            self.markInterface(self.allobjects[tpc+'.Interface'])
        for cls in self.objectsOfType(model.Class):
            if 'zope.interface.Interface' in cls.bases:
                self.markInterface(cls)
        for cls in self.objectsOfType(model.Class):
            for interface in cls.implements:
                if interface in self.allobjects and '.test.' not in interface:
                    self.allobjects[interface].implementedby.append(cls)

    def markInterface(self, cls):
        cls.isinterface = True
        cls.kind = "Interface"
        for sc in cls.subclasses:
            if '.test.' not in sc.fullName():
                self.markInterface(sc)

