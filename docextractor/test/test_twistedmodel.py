import textwrap
from docextractor.twistedmodel import TwistedSystem
from docextractor import model

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
    mod = model.fromText(textwrap.dedent(src), 'zi', TwistedSystem())
    mod.system.finalStateComputations()
    ifoo = mod.contents['IFoo']
    ibar = mod.contents['IBar']
    foo = mod.contents['Foo']
    foobar = mod.contents['FooBar']
    onlybar = mod.contents['OnlyBar']

    assert ifoo.isinterface and ibar.isinterface
    assert not foo.isinterface and not foobar.isinterface and not foobar.isinterface

    assert not foo.implementsOnly and not foobar.implementsOnly
    assert onlybar.implementsOnly

    # these tests illustrate the silliness of the current situation.
    # work needed.
    
    assert foo.implements == ['zi.IFoo']
    assert foobar.implements == ['zi.IBar']
    assert onlybar.implements == ['zi.IBar']
    
    assert ifoo.implementedby == [foo]
    assert ibar.implementedby == [foobar, onlybar]

