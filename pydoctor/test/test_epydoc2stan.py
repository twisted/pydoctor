from pydoctor import epydoc2stan
from pydoctor import model
from pydoctor.sphinx import SphinxInventory
from pydoctor.test.test_astbuilder import fromText


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
    epydoc2stan.doc2stan(mod.contents['f'])
    epydoc2stan.doc2stan(mod.contents['C'])
    epydoc2stan.doc2stan(mod.contents['D'])

def test_summary():
    mod = fromText('''
    def single_line_summary():
        """
        Lorem Ipsum

        Ipsum Lorem
        """
    def no_summary():
        """
        Foo
        Bar
        Baz
        Qux
        """
    def three_lines_summary():
        """
        Foo
        Bar
        Baz

        Lorem Ipsum
        """
    ''')
    def get_summary(func):
        def part_flat(x):
            if isinstance(x, list):
                return ''.join(map(part_flat, x))
            else:
                return x
        return part_flat(
            epydoc2stan.doc2stan(
                mod.contents[func],
                summary=True)[0].children)
    assert u'Lorem Ipsum' == get_summary('single_line_summary')
    assert u'Foo Bar Baz' == get_summary('three_lines_summary')
    assert u'No summary' == get_summary('no_summary')


def test_EpydocLinker_look_for_intersphinx_no_link():
    """
    Return None if inventory had no link for our markup.
    """
    system = model.System()
    target = model.Module(system, 'ignore-name', 'ignore-docstring')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.look_for_intersphinx('base.module')

    assert None is result


def test_EpydocLinker_look_for_intersphinx_hit():
    """
    Return the link from inventory based on first package name.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg, 'some-project')
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name', 'ignore-docstring')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.look_for_intersphinx('base.module.other')

    assert 'http://tm.tld/some.html' == result


def test_EpydocLinker_translate_identifier_xref_intersphinx():
    """
    Return the link from inventory.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg, 'some-project')
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name', 'ignore-docstring')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.translate_identifier_xref(
        'base.module.other', 'base.module.pretty')

    expected = (
        '<a href="http://tm.tld/some.html"><code>base.module.pretty</code></a>'
        )
    assert expected == result
