from pydoctor import nevowhtml, model
from pydoctor.nevowhtml import util, pages, writer
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test import conftest
from pydoctor.test.test_packages import processPackage
from nevow import flat
import cStringIO, os
import py

def getHTMLOf(ob):
    writer = nevowhtml.NevowWriter('')
    writer.system = ob.system
    f = cStringIO.StringIO()
    writer.writeDocsForOne(ob, f)
    return f.getvalue()

def test_simple():
    src = '''
    def f():
        """This is a docstring."""
    '''
    mod = fromText(src)
    v = getHTMLOf(mod.contents['f'])
    assert 'This is a docstring' in v

def test_empty_table():
    mod = fromText('')
    t = pages.TableFragment(None, mod, True, [])
    flattened = flat.flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table():
    mod = fromText('def f(): pass')
    t = pages.TableFragment(pages.ModulePage(mod), mod, True, mod.orderedcontents)
    flattened = flat.flatten(t)
    assert 'The renderer named' not in flattened

def test_rest_support():
    try:
        import docutils, epydoc
    except ImportError:
        py.test.skip("Requires both docutils and epydoc to be importable")
    system = model.System()
    system.options.docformat = 'restructuredtext'
    system.options.verbosity = 4
    src = '''
    def f():
        """This is a docstring for f."""
    '''
    mod = fromText(src, system=system)
    html = getHTMLOf(mod.contents['f'])
    assert "<pre>" not in html

def test_document_code_in_init_module():
    system = processPackage("codeininit")
    html = getHTMLOf(system.allobjects['codeininit'])
    assert 'functionInInit' in html

def test_basic_package():
    system = processPackage("basic")
    targetdir = py.test.ensuretemp("pydoctor")
    w = writer.NevowWriter(str(targetdir))
    w.system = system
    system.options.htmlusesplitlinks = True
    system.options.htmlusesorttable = True
    w.prepOutputDirectory()
    root, = system.rootobjects
    w.writeDocsFor(root, False)
    w.writeModuleIndex(system)
    for ob in system.allobjects.itervalues():
        assert ob.document_in_parent_page or \
               targetdir.join(ob.fullName() + '.html').check(file=1)
    assert 'Package docstring' in targetdir.join('basic.html').read()
    if conftest.option.viewhtml:
        r = os.system("open %s"%targetdir.join('index.html'))
        assert not r

def test_hasdocstring():
    system = processPackage("basic")
    from pydoctor.nevowhtml.summary import hasdocstring
    assert not hasdocstring(system.allobjects['basic._private_mod'])
    assert hasdocstring(system.allobjects['basic.mod.C.f'])
    sub_f = system.allobjects['basic.mod.D.f']
    assert hasdocstring(sub_f) and not sub_f.docstring

