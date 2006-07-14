from pydoctor import nevowhtml, model
from pydoctor.test.test_astbuilder import fromText
import cStringIO

import py

if not nevowhtml.EPYTEXT:
    py.test.skip("tests assume epydoc is present")

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
