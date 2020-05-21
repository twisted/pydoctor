import zope.interface as zi
import zope.schema as zs


class MyInterfaceClass(zi.interface.InterfaceClass):
    pass

MyInterface = MyInterfaceClass("MyInterface")
"""This is my interface."""

class AnInterface(MyInterface):
    def foo():
        pass
    a = zi.Attribute("...")
    f = zs.Choice()
