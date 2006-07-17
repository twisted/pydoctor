import zope.interface as zi
class MyInterfaceClass(zi.interface.InterfaceClass):
    pass
MyInterface = MyInterfaceClass("MyInterface")
class AnInterface(MyInterface):
    pass
