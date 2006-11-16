from pydoctor import nevowhtml, model
from pydoctor.test.test_astbuilder import fromText
from nevow import flat
import cStringIO
import py

class System:
    class options:
        htmlusesorttable = False

def getHTMLOf(ob):
    writer = nevowhtml.NevowWriter('')
    writer.system = System
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
    class system:
        urlprefix = ''
        class options:
            htmlusesorttable = True
    t = nevowhtml.TableFragment(system, True, [])
    flattened = flat.flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table():
    class Child:
        kind = "kooky"
        docstring = None
        document_in_parent_page = False
        linenumber = 10
        class system:
            urlprefix = ''
            sourcebase = None
            class options:
                htmlusesorttable = True
        def fullName(self):
            return 'fullName'
        name = 'name'
        contents = {}
    t = nevowhtml.TableFragment(Child().system, True, [Child()])
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

