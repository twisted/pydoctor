from pydoctor import nevowhtml, model
from pydoctor.test.test_astbuilder import fromText
from nevow import flat
import cStringIO

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
        class system:
            urlprefix = ''
            class options:
                htmlusesorttable = True
        def fullName(self):
            return 'fullName'
        name = 'name'
        contents = {}
    t = nevowhtml.TableFragment(Child().system, True, [Child()])
    flattened = flat.flatten(t)
    assert 'The renderer named' not in flattened
