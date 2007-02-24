from pydoctor import epydoc2stan
from pydoctor.test.test_astbuilder import fromText
import py

def setup_module(mod):
    if not mod.epydoc2stan.EPYTEXT:
        py.test.skip("tests rather pointless without epydoc installed")

def test_multiple_types():
    mod = fromText('''
    def f(a):
        """
        @param a: it\'s a parameter!
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class C(object):
        """
        @ivar a: it\'s an instance var
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class D(object):
        """
        @cvar a: it\'s an instance var
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    ''')
    # basically "assert not fail":
    epydoc2stan.doc2html(mod.contents['f'])
    epydoc2stan.doc2html(mod.contents['C'])
    epydoc2stan.doc2html(mod.contents['D'])
