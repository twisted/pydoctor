from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage
from pydoctor.zopeinterface import ZopeInterfaceSystem

from . import CapSys


# we set up the same situation using both implements and
# classImplements and run the same tests.

def test_implements() -> None:
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

def test_classImplements() -> None:
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

def test_implementer() -> None:
    src = '''
    import zope.interface

    class IFoo(zope.interface.Interface):
        pass
    class IBar(zope.interface.Interface):
        pass

    @zope.interface.implementer(IFoo)
    class Foo:
        pass
    @zope.interface.implementer(IBar)
    class FooBar(Foo):
        pass
    class OnlyBar(Foo):
        zope.interface.implementsOnly(IBar)
    '''
    implements_test(src)

def implements_test(src: str) -> None:
    mod = fromText(src, modname='zi', systemcls=ZopeInterfaceSystem)
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
    assert foo.allImplementedInterfaces == ['zi.IFoo']
    assert foobar.implements_directly == ['zi.IBar']
    assert foobar.allImplementedInterfaces == ['zi.IBar', 'zi.IFoo']
    assert onlybar.implements_directly == ['zi.IBar']
    assert onlybar.allImplementedInterfaces == ['zi.IBar']

    assert ifoo.implementedby_directly == [foo]
    assert ibar.implementedby_directly == [foobar, onlybar]


def test_subclass_with_same_name() -> None:
    src = '''
    class A:
        pass
    class A(A):
        pass
    '''
    fromText(src, modname='zi', systemcls=ZopeInterfaceSystem)

def test_multiply_inheriting_interfaces() -> None:
    src = '''
    from zope.interface import Interface, implements

    class IOne(Interface): pass
    class ITwo(Interface): pass
    class One: implements(IOne)
    class Two: implements(ITwo)
    class Both(One, Two): pass
    '''
    mod = fromText(src, modname='zi', systemcls=ZopeInterfaceSystem)
    assert len(mod.contents['Both'].allImplementedInterfaces) == 2

def test_attribute(capsys: CapSys) -> None:
    src = '''
    import zope.interface as zi
    class C(zi.Interface):
        attr = zi.Attribute("documented attribute")
        bad_attr = zi.Attribute(0)
    '''
    mod = fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    assert len(mod.contents['C'].contents) == 2
    attr = mod.contents['C'].contents['attr']
    assert attr.kind == 'Attribute'
    assert attr.name == 'attr'
    assert attr.docstring == "documented attribute"
    bad_attr = mod.contents['C'].contents['bad_attr']
    assert bad_attr.kind == 'Attribute'
    assert bad_attr.name == 'bad_attr'
    assert bad_attr.docstring is None
    captured = capsys.readouterr().out
    assert captured == 'mod:5: definition of attribute "bad_attr" should have docstring as its sole argument\n'

def test_interfaceclass() -> None:
    system = processPackage('interfaceclass', systemcls=ZopeInterfaceSystem)
    mod = system.allobjects['interfaceclass.mod']
    assert mod.contents['MyInterface'].isinterface
    assert mod.contents['MyInterface'].docstring == "This is my interface."
    assert mod.contents['AnInterface'].isinterface

def test_warnerproofing() -> None:
    src = '''
    from zope import interface
    Interface = interface.Interface
    class IMyInterface(Interface):
        pass
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    assert mod.contents['IMyInterface'].isinterface

def test_zopeschema(capsys: CapSys) -> None:
    src = '''
    from zope import schema, interface
    class IMyInterface(interface.Interface):
        text = schema.TextLine(description="fun in a bun")
        undoc = schema.Bool()
        bad = schema.ASCII(description=False)
    '''
    mod = fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    text = mod.contents['IMyInterface'].contents['text']
    assert text.docstring == 'fun in a bun'
    assert text.kind == "TextLine"
    undoc = mod.contents['IMyInterface'].contents['undoc']
    assert undoc.docstring is None
    assert undoc.kind == "Bool"
    bad = mod.contents['IMyInterface'].contents['bad']
    assert bad.docstring is None
    assert bad.kind == "ASCII"
    captured = capsys.readouterr().out
    assert captured == 'mod:6: description of field "bad" is not a string literal\n'

def test_aliasing_in_class() -> None:
    src = '''
    from zope import interface
    class IMyInterface(interface.Interface):
        Attrib = interface.Attribute
        attribute = Attrib("fun in a bun")
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    attr = mod.contents['IMyInterface'].contents['attribute']
    assert attr.docstring == 'fun in a bun'
    assert attr.kind == "Attribute"

def test_zopeschema_inheritance() -> None:
    src = '''
    from zope import schema, interface
    from zope.schema import Int as INTEGERSCHMEMAFIELD
    class MyTextLine(schema.TextLine):
        pass
    class MyOtherTextLine(MyTextLine):
        pass
    class IMyInterface(interface.Interface):
        mytext = MyTextLine(description="fun in a bun")
        myothertext = MyOtherTextLine(description="fun in another bun")
        myint = INTEGERSCHMEMAFIELD(description="not as much fun")
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    mytext = mod.contents['IMyInterface'].contents['mytext']
    assert mytext.docstring == 'fun in a bun'
    assert mytext.kind == "MyTextLine"
    myothertext = mod.contents['IMyInterface'].contents['myothertext']
    assert myothertext.docstring == 'fun in another bun'
    assert myothertext.kind == "MyOtherTextLine"
    myint = mod.contents['IMyInterface'].contents['myint']
    assert myint.kind == "Int"

def test_docsources_includes_interface() -> None:
    src = '''
    from zope import interface
    class IInterface(interface.Interface):
        def method(self):
            """documentation"""
    class Implementation:
        interface.implements(IInterface)
        def method(self):
            pass
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    imethod = mod.contents['IInterface'].contents['method']
    method = mod.contents['Implementation'].contents['method']
    assert imethod in method.docsources(), list(method.docsources())

def test_docsources_includes_baseinterface() -> None:
    src = '''
    from zope import interface
    class IBase(interface.Interface):
        def method(self):
            """documentation"""
    class IExtended(IBase):
        pass
    class Implementation:
        interface.implements(IExtended)
        def method(self):
            pass
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    imethod = mod.contents['IBase'].contents['method']
    method = mod.contents['Implementation'].contents['method']
    assert imethod in method.docsources(), list(method.docsources())

def test_docsources_interface_attribute() -> None:
    src = '''
    from zope import interface
    class IInterface(interface.Interface):
        attr = interface.Attribute("""documentation""")
    @interface.implementer(IInterface)
    class Implementation:
        attr = True
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    iattr = mod.contents['IInterface'].contents['attr']
    attr = mod.contents['Implementation'].contents['attr']
    assert iattr in list(attr.docsources())

def test_implementer_decoration() -> None:
    src = '''
    from zope.interface import Interface, implementer
    class IMyInterface(Interface):
        def method(self):
            """documentation"""
    @implementer(IMyInterface)
    class Implementation:
        def method(self):
            pass
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    iface = mod.contents['IMyInterface']
    impl = mod.contents['Implementation']
    assert impl.implements_directly == [iface.fullName()]

def test_docsources_from_moduleprovides() -> None:
    src = '''
    from zope import interface

    class IBase(interface.Interface):
        def bar():
            """documentation"""

    interface.moduleProvides(IBase)

    def bar():
        pass
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    imethod = mod.contents['IBase'].contents['bar']
    function = mod.contents['bar']
    assert imethod in function.docsources(), list(function.docsources())

def test_interfaceallgames() -> None:
    system = processPackage('interfaceallgames', systemcls=ZopeInterfaceSystem)
    mod = system.allobjects['interfaceallgames.interface']
    iface = mod.contents['IAnInterface']
    assert [o.fullName() for o in iface.implementedby_directly] == [
        'interfaceallgames.implementation.Implementation'
        ]

def test_implementer_with_star() -> None:
    """
    If the implementer call contains a split out empty list, don't fail on
    attempting to process it.
    """
    src = '''
    from zope.interface import Interface, implementer
    extra_interfaces = ()
    class IMyInterface(Interface):
        def method(self):
            """documentation"""
    @implementer(IMyInterface, *extra_interfaces)
    class Implementation:
        def method(self):
            pass
    '''
    mod = fromText(src, systemcls=ZopeInterfaceSystem)
    iface = mod.contents['IMyInterface']
    impl = mod.contents['Implementation']
    assert impl.implements_directly == [iface.fullName()]

def test_implementer_nonname(capsys: CapSys) -> None:
    """
    Non-name arguments passed to @implementer are warned about and then ignored.
    """
    src = '''
    from zope.interface import implementer
    @implementer(123)
    class Implementation:
        pass
    '''
    mod = fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    impl = mod.contents['Implementation']
    assert impl.implements_directly == []
    captured = capsys.readouterr().out
    assert captured == 'mod:3: Interface argument 1 does not look like a name\n'

def test_implementer_nonclass(capsys: CapSys) -> None:
    """
    Non-class arguments passed to @implementer are warned about but are stored
    as implemented interfaces.
    """
    src = '''
    from zope.interface import implementer
    var = 'not a class'
    @implementer(var)
    class Implementation:
        pass
    '''
    mod = fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    impl = mod.contents['Implementation']
    assert impl.implements_directly == ['mod.var']
    captured = capsys.readouterr().out
    assert captured == 'mod:4: Supposed interface "mod.var" not detected as a class\n'

def test_implementer_plainclass(capsys: CapSys) -> None:
    """
    A non-interface class passed to @implementer will be warned about but
    will be stored as an implemented interface.
    """
    src = '''
    from zope.interface import implementer
    class C:
        pass
    @implementer(C)
    class Implementation:
        pass
    '''
    mod = fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    C = mod.contents['C']
    impl = mod.contents['Implementation']
    assert not C.isinterface
    assert C.kind == "Class"
    assert impl.implements_directly == ['mod.C']
    captured = capsys.readouterr().out
    assert captured == 'mod:5: Class "mod.C" is not an interface\n'

def test_implementer_not_found(capsys: CapSys) -> None:
    """
    An unknown class passed to @implementer is warned about if its full name
    is part of our system.
    """
    src = '''
    from zope.interface import implementer
    from twisted.logger import ILogObserver
    @implementer(ILogObserver, mod.INoSuchInterface)
    class Implementation:
        pass
    '''
    fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    captured = capsys.readouterr().out
    assert captured == 'mod:4: Interface "mod.INoSuchInterface" not found\n'

def test_implementer_reparented() -> None:
    """
    A class passed to @implementer can be found even when it is moved
    to a different module.
    """

    system = ZopeInterfaceSystem()

    mod_iface = fromText('''
    from zope.interface import Interface
    class IMyInterface(Interface):
        pass
    ''', modname='_private', system=system)

    mod_export = fromText('', modname='public', system=system)

    mod_impl = fromText('''
    from zope.interface import implementer
    from _private import IMyInterface
    @implementer(IMyInterface)
    class Implementation:
        pass
    ''', modname='app', system=system)

    iface = mod_iface.contents['IMyInterface']
    iface.reparent(mod_export, 'IMyInterface')
    assert iface.fullName() == 'public.IMyInterface'
    assert 'IMyInterface' not in mod_iface.contents

    impl = mod_impl.contents['Implementation']
    assert impl.implements_directly == ['_private.IMyInterface']
    assert iface.implementedby_directly == []

    system.postProcess()
    assert impl.implements_directly == ['public.IMyInterface']
    assert iface.implementedby_directly == [impl]

def test_implementer_nocall(capsys: CapSys) -> None:
    """
    Report a warning when @implementer is used without calling it.
    """
    src = '''
    import zope.interface
    @zope.interface.implementer
    class C:
        pass
    '''
    fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    captured = capsys.readouterr().out
    assert captured == "mod:3: @implementer requires arguments\n"

def test_classimplements_badarg(capsys: CapSys) -> None:
    """
    Report a warning when the arguments to classImplements() don't make sense.
    """
    src = '''
    from zope.interface import Interface, classImplements
    class IBar(Interface):
        pass
    def f():
        pass
    classImplements()
    classImplements(None, IBar)
    classImplements(f, IBar)
    classImplements(g, IBar)
    '''
    fromText(src, modname='mod', systemcls=ZopeInterfaceSystem)
    captured = capsys.readouterr().out
    assert captured == (
        'mod:7: required argument to classImplements() missing\n'
        'mod:8: argument 1 to classImplements() is not a class name\n'
        'mod:9: argument "mod.f" to classImplements() is not a class\n'
        'mod:10: argument "g" to classImplements() not found\n'
        )
