import zope.interface as zi
import zope.schema as zs
class MyInterfaceClass(zi.interface.InterfaceClass):
    pass
MyInterface = MyInterfaceClass("MyInterface")
class AnInterface(MyInterface):
    def foo():
        pass
    a = zi.Attribute("...")
    f = zs.Choice()
