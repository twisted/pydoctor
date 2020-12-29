"""
Test how epytext is rendered to HTML.

Many of these test cases are adapted examples from
U{the epytext documentation<http://epydoc.sourceforge.net/epytext.html>}.

On Python < 3.6 dictionaries don't preserve insertion order,
which makes the order of attributes in the HTML output random.
To work around this, expected output should contain at most
one attribute per tag.
"""

from typing import List

from pydoctor.epydoc.markup import DocstringLinker, ParseError, flatten
from pydoctor.epydoc.markup.epytext import parse_docstring
from pydoctor.test import NotFoundLinker


def epytext2html(s: str, linker: DocstringLinker = NotFoundLinker()) -> str:
    errors: List[ParseError] = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return flatten(parsed.to_stan(linker))

def squash(s: str) -> str:
    return ''.join(
        line.lstrip() for line in s.strip().split('\n')
        ).replace('|', '\n')


def test_epytext_paragraph() -> None:
    doc = '''
        This is a paragraph.  Paragraphs can
        span multiple lines, and can contain
        I{inline markup}.


        This is another paragraph.  Paragraphs
        are separated by blank lines.
        '''
    expected = '''
        <p>This is a paragraph.  Paragraphs can span multiple lines, and can contain <i>inline markup</i>.</p>
        <p>This is another paragraph.  Paragraphs are separated by blank lines.</p>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_ordered_list() -> None:
    doc = '''
          1. This is an ordered list item.

          2. This is another ordered list
          item.

          3. This is a third list item.  Note that
             the paragraph may be indented more
             than the bullet.

        This ends the list.

          4. This new list starts at four.
        '''
    expected = '''
        <ol>
        <li>This is an ordered list item.</li>
        <li>This is another ordered list item.</li>
        <li>This is a third list item.  Note that the paragraph may be indented more than the bullet.</li>
        </ol>
        <p>This ends the list.</p>
        <ol start="4">
        <li>This new list starts at four.</li>
        </ol>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_nested_list() -> None:
    doc = '''
        This is a paragraph.
            1. This is a list item.
            2. This is a second list
               item.
                 - This is a sublist.
        '''
    expected = '''
        <p>This is a paragraph.</p>
        <ol>
            <li>This is a list item.</li>
            <li>This is a second list item.
            <ul><li>This is a sublist.</li></ul></li>
        </ol>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_complex_list() -> None:
    doc = '''
        This is a paragraph.
          1. This is a list item.
            - This is a sublist.
            - The sublist contains two
              items.
                - The second item of the
                  sublist has its own sublist.

          2. This list item contains two
             paragraphs and a doctest block.

             >>> len('This is a doctest block')
             23

             This is the second paragraph.
        '''
    expected = '''
        <p>This is a paragraph.</p>
        <ol>
          <li>This is a list item.
            <ul>
              <li>This is a sublist.</li>
              <li>The sublist contains two items.
                <ul>
                  <li>The second item of the sublist has its own sublist.</li>
                </ul>
              </li>
            </ul>
          </li>
          <li>This list item contains two paragraphs and a doctest block.
            <pre class="py-doctest">
              |<span class="py-prompt">&gt;&gt;&gt; </span>
               <span class="py-builtin">len</span>
               (<span class="py-string">'This is a doctest block'</span>)
              |<span class="py-output">23</span>
            |</pre>
            <p>This is the second paragraph.</p>
          </li>
        </ol>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_sections() -> None:
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
    expected = '''
        <p>This paragraph is not in any section.</p>
        <h1>Section 1</h1>
        <p>This is a paragraph in section 1.</p>
        <h2>Section 1.1</h2>
        <p>This is a paragraph in section 1.1.</p>
        <h1>Section 2</h1>
        <p>This is a paragraph in section 2.</p>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_literal_block() -> None:
    doc = '''
        The following is a literal block::

            Literal /
                   / Block

        This is a paragraph following the
        literal block.
        '''
    expected = '''
        <p>The following is a literal block:</p>
        <pre class="literalblock">
        |    Literal /
        |           / Block
        |</pre>
        <p>This is a paragraph following the literal block.</p>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_inline() -> None:
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
    expected = '''
        <p><i><b>Inline markup</b> may be nested; and it may span</i> multiple lines.</p>
        <ul>
          <li><i>Italicized text</i></li>
          <li><b>Bold-faced text</b></li>
          <li><code>Source code</code></li>
          <li>Math: <i class="math">m*x+b</i></li>
        </ul>
        <p>Without the capital letter, matching braces are not interpreted as markup: <code>my_dict={1:2, 3:4}</code>.</p>
        '''
    assert epytext2html(doc) == squash(expected)

def test_epytext_url() -> None:
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
    expected = '''
        <ul>
          <li><a href="http://www.python.org">www.python.org</a></li>
          <li><a href="http://www.python.org">http://www.python.org</a></li>
          <li><a href="http://epydoc.sourceforge.net">The epydoc homepage</a></li>
          <li><a href="http://www.python.org">The <b><i>Python</i></b> homepage</a></li>
          <li><a href="mailto:edloper@gradient.cis.upenn.edu">Edward Loper</a></li>
        </ul>
        '''
    # Drop 'target' attribute so we have one attribute per tag.
    assert epytext2html(doc).replace(' target="_top"', '') == squash(expected)

def test_epytext_symbol() -> None:
    doc = '''
        Symbols can be used in equations:
          - S{sum}S{alpha}/x S{<=} S{beta}

        S{<-} and S{larr} both give left
        arrows.  Some other arrows are
        S{rarr}, S{uarr}, and S{darr}.
        '''
    expected = '''
        <p>Symbols can be used in equations:</p>
        <ul>
            <li>&#8721;&#945;/x &#8804; &#946;</li>
        </ul>
        <p>&#8592; and &#8592; both give left arrows.  Some other arrows are &#8594;, &#8593;, and &#8595;.</p>
        '''
    assert epytext2html(doc) == squash(expected)
