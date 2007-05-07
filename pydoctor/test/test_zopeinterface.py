import textwrap
from pydoctor.twisted import TwistedASTBuilder
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage
from pydoctor import model

# we set up the same situation using both implements and
# classImplements and run the same tests.

def test_implements():
    src = '''
    import zope.interface

    class IFoo(zope.interface.Interface):
        pass
    class IBar(zope.interface.Interface):
        pass

    class Foo:
        zope.interface.implements(IFoo)
    class FooBar(Foo):
        zope.interface.implements(IBar)
    class OnlyBar(Foo):
        zope.interface.implementsOnly(IBar)
    '''
    implements_test(src)

def test_classImplements():
    src = '''
    import zope.interface
    class IFoo(zope.interface.Interface):
        pass
    class IBar(zope.interface.Interface):
        pass
    class Foo:
        pass
    class FooBar(Foo):
        pass
    class OnlyBar(Foo):
        pass
    zope.interface.classImplements(Foo, IFoo)
    zope.interface.classImplements(FooBar, IBar)
    zope.interface.classImplementsOnly(OnlyBar, IBar)
    '''
    implements_test(src)


def implements_test(src):
    mod = fromText(src, 'zi', buildercls=TwistedASTBuilder)
    ifoo = mod.contents['IFoo']
    ibar = mod.contents['IBar']
    foo = mod.contents['Foo']
    foobar = mod.contents['FooBar']
    onlybar = mod.contents['OnlyBar']

    assert ifoo.isinterface and ibar.isinterface
    assert not foo.isinterface and not foobar.isinterface and not foobar.isinterface

    assert not foo.implementsOnly and not foobar.implementsOnly
    assert onlybar.implementsOnly

    assert foo.implements_directly == ['zi.IFoo']
    assert foo.implements_indirectly == []
    assert foobar.implements_directly == ['zi.IBar']
    assert foobar.implements_indirectly == ['zi.IFoo']
    assert onlybar.implements_directly == ['zi.IBar']
    assert onlybar.implements_indirectly == []

    assert ifoo.implementedby_directly == ['zi.Foo']
    assert ifoo.implementedby_indirectly == ['zi.FooBar']
    assert ibar.implementedby_directly == ['zi.FooBar', 'zi.OnlyBar']
    assert ibar.implementedby_indirectly == []

def test_subclass_with_same_name():
    src = '''
    class A:
        pass
    class A(A):
        pass
    '''
    mod = fromText(src, 'zi', buildercls=TwistedASTBuilder)

def test_multiply_inheriting_interfaces():
    src = '''
    from zope.interface import Interface, implements

    class IOne(Interface): pass
    class ITwo(Interface): pass
    class One: implements(IOne)
    class Two: implements(ITwo)
    class Both(One, Two): pass
    '''
    mod = fromText(src, 'zi', buildercls=TwistedASTBuilder)
    assert len(mod.contents['Both'].implements_indirectly) == 2

def test_attribute():
    src = '''
    import zope.interface as zi
    class C:
        attr = zi.Attribute("docstring")
    '''
    mod = fromText(src, buildercls=TwistedASTBuilder)
    assert len(mod.contents['C'].contents) == 1

def test_interfaceclass():
    src = '''
    import zope.interface as zi
    class MyInterfaceClass(zi.interface.InterfaceClass):
        pass
    MyInterface = MyInterfaceClass("MyInterface")
    class AnInterface(MyInterface):
        pass
    '''
    system = processPackage('interfaceclass', buildercls=TwistedASTBuilder)
    mod = system.allobjects['interfaceclass.mod']
    assert mod.contents['AnInterface'].isinterface

def test_warnerproofing():
    src = '''
    from zope import interface
    Interface = interface.Interface
    class IMyInterface(Interface):
        pass
    '''
    mod = fromText(src, buildercls=TwistedASTBuilder)
    assert mod.contents['IMyInterface'].isinterface
