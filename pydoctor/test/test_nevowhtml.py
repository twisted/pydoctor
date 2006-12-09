from pydoctor import nevowhtml, model
from pydoctor.nevowhtml import util, pages
from pydoctor.test.test_astbuilder import fromText
from nevow import flat
import cStringIO
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
    t = pages.TableFragment(mod, True, [])
    flattened = flat.flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table():
    mod = fromText('def f(): pass')
    t = pages.TableFragment(mod, True, mod.orderedcontents)
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
    from pydoctor.test.test_packages import processPackage
    system = processPackage("codeininit")
    html = getHTMLOf(system.allobjects['codeininit'])
    assert 'functionInInit' in html

