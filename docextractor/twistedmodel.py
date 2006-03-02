from docextractor import model
from docextractor import ast_pp

class TwistedClass(model.Class):
    def setup(self):
        super(TwistedClass, self).setup()
        self.isinterface = False
        self.implements = []
        self.implementedby = []

class TwistedModuleVisitor(model.ModuleVistor):
    def visitCallFunc(self, node):
        current = self.system.current
        if not isinstance(current, model.Class):
            self.default(node)
            return
        str_base = ast_pp.pp(node.node)
        base = self.system.current.dottedNameToFullName(str_base)
        if base == 'zope.interface.implements':
            for arg in node.args:
                current.implements.append(
                    self.system.current.dottedNameToFullName(ast_pp.pp(arg)))
    
class TwistedSystem(model.System):
    Class = TwistedClass
    ModuleVistor = TwistedModuleVisitor

    def finalStateComputations(self):
        self.push(self.allobjects['twisted.python.components'])
        self.pushClass('Interface', None)
        self.popClass()
        super(TwistedSystem, self).finalStateComputations()
        self.markInterface(self.allobjects['twisted.python.components.Interface'])
        for cls in self.objectsOfType(model.Class):
            if 'zope.interface.Interface' in cls.bases:
                self.markInterface(cls)
        for cls in self.objectsOfType(model.Class):
            for interface in cls.implements:
                if interface in self.allobjects and '.test.' in interface:
                    self.allobjects[interface].implementedby.append(cls)

    def markInterface(self, cls):
        cls.isinterface = True
        cls.kind = "Interface"
        for sc in cls.subclasses:
            if '.test.' not in sc.fullName():
                self.markInterface(sc)

