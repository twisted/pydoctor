import textwrap
from docextractor.twistedmodel import TwistedSystem
from docextractor import model

def test_simple():
    src = '''
    import zope.interface
    class IFoo(zope.interface.Interface):
        pass
    class Foo:
        zope.interface.implements(IFoo)
    '''
    mod = model.fromText(textwrap.dedent(src), 'zi', TwistedSystem())
    mod.system.finalStateComputations()
    interface = mod.contents['IFoo']
    implementation = mod.contents['Foo']
    assert interface.isinterface
    assert implementation.implements == [interface.fullName()]
    assert interface.implementedby == [implementation]
    

