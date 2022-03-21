"""
Tests for the L{node2stan} module.

:See: {test.epydoc.test_epytext2html}, {test.epydoc.test_restructuredtext}
"""

from pydoctor.test.epydoc.test_epytext2html import epytext2node
from pydoctor.test.epydoc.test_restructuredtext import rst2node

from pydoctor.node2stan import gettext


def test_gettext() -> None:
    doc = '''
        This paragraph is not in any section.

        Section 1
        =========
          This is a paragraph in section 1.

          Section 1.1
          -----------
          This is a paragraph in section 1.1.

        Section 2
        =========
          This is a paragraph in section 2.
        '''
    assert gettext(epytext2node(doc)) == [
        'This paragraph is not in any section.', 
        'Section 1', 'This is a paragraph in section 1.', 
        'Section 1.1', 'This is a paragraph in section 1.1.', 
        'Section 2', 'This is a paragraph in section 2.']

    doc = '''
        I{B{Inline markup} may be nested; and
        it may span} multiple lines.

          - I{Italicized text}
          - B{Bold-faced text}
          - C{Source code}
          - Math: M{m*x+b}

        Without the capital letter, matching
        braces are not interpreted as markup:
        C{my_dict={1:2, 3:4}}.
        '''
    assert gettext(epytext2node(doc)) == [
        'Inline markup', ' may be nested; and it may span', 
        ' multiple lines.', 'Italicized text', 'Bold-faced text', 
        'Source code', 'Math: ', 'm*x+b', 
        'Without the capital letter, matching braces are not interpreted as markup: ', 
        'my_dict=', '{', '1:2, 3:4', '}', '.']

    doc = '''
        - U{www.python.org}
        - U{http://www.python.org}
        - U{The epydoc homepage<http://
          epydoc.sourceforge.net>}
        - U{The B{I{Python}} homepage
          <www.python.org>}
        - U{Edward Loper<mailto:edloper@
          gradient.cis.upenn.edu>}
        '''

    # TODO: Make it retreive the links refuid attribute.
    assert gettext(epytext2node(doc)) == ['www.python.org', 
    'http://www.python.org', 'The epydoc homepage', 'The ', 'Python', 
    ' homepage', 'Edward Loper']

    doc = '''
    This paragraph is not in any section.

    `<postmaster@example.net>`__

    .. note:: This is just a note with nested contents

        .. image:: https://avatars0.githubusercontent.com/u/50667087?s=200&v=4
            :target: https://mfesiem.github.io/docs/msiempy/msiempy.html
            :alt: Nitro
            :width: 50
            :height: 50

    '''

    assert gettext(rst2node(doc)) == ['This paragraph is not in any section.', 
    'mailto:postmaster@example.net', 'This is just a note with nested contents']