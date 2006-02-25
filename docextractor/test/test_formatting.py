from docextractor import html, model
from py import test

def test_signatures():
    argspec = [['a', 'b', 'c'], None, None, (1,2)]
    assert html.getBetterThanArgspec(argspec) == (['a'], [('b', 1), ('c', 2)])

def test_strsig():
    argspec = [['a', 'b', 'c'], None, None, (1,2)]
    assert html.signature(argspec) == "a, b=1, c=2"

def test_strsigvar():
    argspec = [['a', 'b', 'c'], 'args', 'kk', (1,2)]
    assert html.signature(argspec) == "a, *args, b=1, c=2, **kk"

def test_strsigargh():
    argspec = [['a', ['b','c']], None, None, ()]
    assert html.signature(argspec) == 'a, (b, c)'

def test_link():
    docco = model.Documentable(None, 'twisted.', 'threadz', '')
    assert html.link(docco) == 'twisted.threadz.html'

def test_summaryDoc():
    docco = model.Documentable(None, 'twisted.', 'threadz', 'Woot\nYeah')
    assert html.summaryDoc(docco) == 'Woot' # Make this better

def test_boringDocstring():
    assert html.boringDocstring('Woot\nYeah') == '<pre>Woot\nYeah</pre>'

def test_reallyBoringDocstring():
    assert html.boringDocstring('') == '<pre>Undocumented</pre>'
    assert html.boringDocstring(None) == '<pre>Undocumented</pre>'

def test_doc2htmlEpy():
    if not html.EPYTEXT:
        test.skip("Epytext not available")
    assert html.doc2html(None, 'Woot\nYeah') == '<div>Woot Yeah\n</div>'

class TestEpyHackers:
    def setup_method(self, meth):
        self.orig = html.EPYTEXT
    def teardown_method(self, meth):
        html.EPYTEXT = self.orig

    def test_doc2htmlBoring(self):
        if html.EPYTEXT:
            html.EPYTEXT = False
        assert html.doc2html(None, 'Woot\nYeah') == '<pre>Woot\nYeah</pre>'

    def test_generateModuleIndex(self):
        #This test is a bit un-unity
        # And *damnit* how do I write teardowners
        html.EPYTEXT = False
        sysw = html.SystemWriter(None)
        mod = model.Module(None, 'twisted.', 'threadz', 'Woot\nYeah')
        fun = model.Function(None, 'twisted.threadz.', 'blat', 
                             'HICKY HECK\nYEAH')
        fun.argspec = [(), None, None, ()]
        out = sysw.getHTMLFor(fun)
        assert 'blat()' in out
        assert 'HICKY HECK\nYEAH' in out


