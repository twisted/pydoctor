from pydoctor import nevowhtml, model
import cStringIO, textwrap

import py

if not nevowhtml.EPYTEXT:
    py.test.skip("tests assume epydoc is present")

def getHTMLOf(ob):
    writer = nevowhtml.NevowWriter('')
    f = cStringIO.StringIO()
    writer.writeDocsForOne(ob, f)
    return f.getvalue()

def test_simple():
    src = '''
    def f():
        """This is a docstring."""
    '''
    mod = model.fromText(textwrap.dedent(src))
    v = getHTMLOf(mod.contents['f'])
    assert 'This is a docstring' in v
