from compiler.visitor import walk
from compiler.transformer import parse
from pydoctor import model, astbuilder
from pydoctor.test.test_packages import processPackage
import py

def test_simple():
    system = model.System()
    builder = astbuilder.ASTBuilder(system)
    foo = builder.pushModule('foo', None)
    builder.popModule()
    bar = builder.pushModule('bar', None)
    builder.popModule()
    isf = astbuilder.ImportFinder(builder, bar)
    walk(parse("from foo import bar"), isf)
    assert len(system.importgraph) == 1
    edge, = system.importgraph.iteritems()
    assert edge == ('bar', set(['foo']))

def test_actual():
    system = processPackage("importstartest")
    cls = system.allobjects['importstartest.mod1.C']
    assert cls.bases == ['importstartest.mod2.B']

def test_all_recognition():
    system = model.System()
    builder = astbuilder.ASTBuilder(system)
    foo = builder.pushModule('foo', None)
    builder.popModule()
    isf = astbuilder.ImportFinder(builder, foo)
    walk(parse("__all__ = ['bar']"), isf)
    assert foo.all == ['bar']

def test_all_in_class_non_recognition():
    system = model.System()
    builder = astbuilder.ASTBuilder(system)
    foo = builder.pushModule('foo', None)
    builder.popModule()
    isf = astbuilder.ImportFinder(builder, foo)
    walk(parse("class C: __all__ = ['bar']"), isf)
    assert foo.all is None
