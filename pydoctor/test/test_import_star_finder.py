from compiler.visitor import walk
from compiler.transformer import parse
from pydoctor import model, astbuilder
from pydoctor.test.test_packages import processPackage
import py

def test_simple():
    system = model.System()
    builder = astbuilder.ASTBuilder(system)
    builder.pushModule('foo', None)
    builder.popModule()
    isf = astbuilder.ImportFinder(builder, 'bar')
    walk(parse("from foo import bar"), isf)
    assert len(system.importgraph) == 1
    edge, = system.importgraph.iteritems()
    assert edge == ('bar', set(['foo']))

def test_actual():
    system = processPackage("importstartest")
    cls = system.allobjects['importstartest.mod1.C']
    assert cls.bases == ['importstartest.mod2.B']
