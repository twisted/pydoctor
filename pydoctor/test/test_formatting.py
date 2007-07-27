from pydoctor import html, model
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
    doc0 = model.Documentable(None, 'twisted', None)
    docco = model.Documentable(None, 'threadz', None, doc0)
    assert html.link(docco) == 'twisted.threadz.html'

def test_summaryDoc():
    docco = model.Documentable(None, 'threadz', 'Woot\nYeah')
    assert html.summaryDoc(docco) == html.doc2html(docco, 'Woot')

def test_boringDocstring():
    assert html.boringDocstring('Woot\nYeah') == '<pre>Woot\nYeah</pre>'

def test_reallyBoringDocstring():
    undocced = '<pre class="undocumented">Undocumented</pre>'
    assert html.boringDocstring('') == undocced
    assert html.boringDocstring(None) == undocced

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
        assert html.doc2html(object(), 'Woot\nYeah') == '<pre>Woot\nYeah</pre>'

    def test_generateModuleIndex(self):
        #This test is a bit un-unity
        # And *damnit* how do I write teardowners
        html.EPYTEXT = False
        sysw = html.SystemWriter(None)
        pack = model.Package(None, 'twisted', None)
        mod = model.Module(None, 'threadz', 'Woot\nYeah', pack)
        fun = model.Function(None, 'blat', 'HICKY HECK\nYEAH', mod)
        fun.argspec = [(), None, None, ()]
        out = sysw.getHTMLFor(fun)
        assert 'blat()' in out
        assert 'HICKY HECK\nYEAH' in out
