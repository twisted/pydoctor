from compiler.visitor import walk
from compiler.transformer import parse
from pydoctor import model, astbuilder
from pydoctor.test.test_packages import processPackage

def test_simple():
    system = model.System()
    builder = astbuilder.ASTBuilder(system)
    foo = builder.pushModule('foo', None)
    builder.popModule()
    bar = builder.pushModule('bar', None)
    builder.popModule()
    isf = astbuilder.ImportFinder(builder, bar)
    bar = builder.pushModule('baz', None)
    walk(parse("from foo import bar"), isf)
    builder.popModule()
    assert len(system.importgraph) == 1
    edge, = system.importgraph.iteritems()
    assert edge == ('bar', set(['foo']))

def test_actual():
    system = processPackage("importstartest")
    cls = system.allobjects['importstartest.mod1.C']
    assert cls.bases == ['importstartest.mod2.B']

