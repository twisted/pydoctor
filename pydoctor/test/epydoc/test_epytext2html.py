"""
Test how epytext is transformed to HTML using L{ParsedDocstring.to_node()} and L{node2stan.node2stan()} functions.

Many of these test cases are adapted examples from
U{the epytext documentation<http://epydoc.sourceforge.net/epytext.html>}.
"""

from typing import List

import pytest

from pydoctor.epydoc.markup import ParseError, ParsedDocstring
from pydoctor.stanutils import flatten
from pydoctor.epydoc.markup.epytext import parse_docstring
from pydoctor.node2stan import node2stan
from pydoctor.test import NotFoundLinker
from pydoctor.test.epydoc.test_restructuredtext import prettify

from docutils import nodes, __version_info__ as docutils_version_info

def parse_epytext(s: str) -> ParsedDocstring:
    errors: List[ParseError] = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return parsed

def epytext2node(s: str)-> nodes.document:
    return parse_epytext(s).to_node()

def epytext2html(s: str) -> str:
    return squash(flatten(node2stan(epytext2node(s), NotFoundLinker())))

def squash(s: str) -> str:
    return ''.join(l.strip() for l in prettify(s).splitlines())

def test_epytext_paragraph() -> None:
    doc = '''
        This is a paragraph.  Paragraphs can
        span multiple lines, and can contain
        I{inline markup}.


        This is another paragraph.  Paragraphs
        are separated by blank lines.
        '''
    expected = '''

         <p>
          This is a paragraph.  Paragraphs can span multiple lines, and can contain
          <em>
           inline markup
          </em>
          .
         </p>
         <p>
          This is another paragraph.  Paragraphs are separated by blank lines.
         </p>

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
        <ol class="rst-simple"> <li>  This is an ordered list item. </li> 
        <li>  This is another ordered list item. </li> 
        <li>  This is a third list item.  Note that the paragraph may be indented more than the bullet. </li>
        </ol>
        <p> This ends the list.</p>
        <ol class="rst-simple"> <li>  This new list starts at four. </li></ol>
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
    <p>This is a paragraph.</p><ol class="rst-simple"><li>This is a list item.</li>
    <li>This is a second list item.<ul><li>This is a sublist.</li></ul></li></ol>
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
        <p>This is a paragraph.</p><ol><li><p class="rst-first">This is a list item.</p>
        <ul class="rst-simple"><li>This is a sublist.</li><li>The sublist contains two items.
        <ul><li>The second item of the sublist has its own sublist.</li></ul></li></ul></li>
        <li><p class="rst-first">This list item contains two paragraphs and a doctest block.</p>
        <pre class="py-doctest"><span class="py-prompt">&gt;&gt;&gt; </span>
        <span class="py-builtin">len</span>(<span class="py-string">'This is a doctest block'</span>)
        <span class="py-output">23</span></pre><p>This is the second paragraph.</p></li></ol>
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

          <p>
           This paragraph is not in any section.
          </p>
          <div class="rst-section" id="rst-section-1">
           <h2 class="heading">
            Section 1
           </h2>
           <p>
            This is a paragraph in section 1.
           </p>
           <div class="rst-section" id="rst-section-11">
            <h3 class="heading">
             Section 1.1
            </h3>
            <p>
             This is a paragraph in section 1.1.
            </p>
           </div>
          </div>
          <div class="rst-section" id="rst-section-2">
           <h2 class="heading">
            Section 2
           </h2>
           <p>
            This is a paragraph in section 2.
           </p>
          </div>

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

          <p>
           The following is a literal block:
          </p>
          <pre class="rst-literal-block">
    Literal /
           / Block
</pre>
          <p>
           This is a paragraph following the literal block.
          </p>

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
        <p> <em>  <strong>   Inline markup  </strong>  may be nested; and it may span </em> multiple lines.</p>
        <ul class="rst-simple"> <li>  <em>   Italicized text  </em> </li> <li>  <strong>   Bold-faced text  </strong> </li> 
        <li>  <tt class="rst-docutils rst-literal">   Source code  </tt> </li> 
        <li>  Math:  <span class="rst-formula rst-math">   <i>    m   </i>   *   <i>    x   </i>   +   <i>    b   </i>  </span> </li></ul>
        <p> Without the capital letter, matching braces are not interpreted as markup: <tt class="rst-docutils rst-literal">  
        <span class="pre">   my_dict={1:2,  </span>  3:4} </tt> .</p>
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
        <ul class="rst-simple">
        <li><a class="rst-external rst-reference" href="http://www.python.org" target="_top">www.python.org</a></li>
        <li><a class="rst-external rst-reference" href="http://www.python.org" target="_top">http://www.python.org</a></li>
        <li><a class="rst-external rst-reference" href="http://epydoc.sourceforge.net" target="_top">The epydoc homepage</a></li>
        <li><a class="rst-external rst-reference" href="http://www.python.org" target="_top">The<strong><em>Python</em></strong>homepage</a></li>
        <li><a class="rst-external rst-reference" href="mailto:edloper@gradient.cis.upenn.edu" target="_top">Edward Loper</a></li></ul>'''

    assert epytext2html(doc) == squash(expected)

def test_epytext_symbol() -> None:
    doc = '''
        Symbols can be used in equations:
          - S{sum}S{alpha}/x S{<=} S{beta}

        S{<-} and S{larr} both give left
        arrows.  Some other arrows are
        S{rarr}, S{uarr}, and S{darr}.
        '''
    expected = '''
    <p> Symbols can be used in equations:</p>
    <ul class="rst-simple"> <li>  <span>   ∑  </span>  <span>   α  </span>  /x  <span>   ≤  </span>  <span>   β  </span> </li></ul>
    <p> <span>  ← </span> and <span>  ← </span> both give left arrows.  Some other arrows are <span>  → </span> , <span>  ↑ </span> , and <span>  ↓ </span> .</p>
    '''
    assert epytext2html(doc) == squash(expected)

def test_nested_markup() -> None:
    """
    The Epytext nested inline markup are correctly transformed to HTML. 
    """
    doc = '''
        I{B{Inline markup} may be nested; and
        it may span} multiple lines.
        '''
    expected = '''<em> <strong>  Inline markup </strong> may be nested; and it may span</em>multiple lines.'''
    
    assert epytext2html(doc) == squash(expected)

    doc = '''
        It becomes a little bit complicated with U{B{custom} links <https://google.ca>}
        '''
    expected = '''
      It becomes a little bit complicated with<a class="rst-external rst-reference" href="https://google.ca" target="_top"><strong>custom</strong>links</a>
      '''
    
    assert epytext2html(doc) == squash(expected)

# From docutils 0.18 the toc entries uses different ids.
@pytest.mark.skipif(docutils_version_info < (0,18), reason="HTML ids in toc tree changed in docutils 0.18.0.")
def test_get_toc() -> None:

    docstring = """
Titles
======

Level 2
-------

Level 3
~~~~~~~

Level 4
^^^^^^^

Level 5
!!!!!!!

Level 2.2
---------

Level 22
--------

Lists
=====

Other
=====
"""

    errors: List[ParseError] = []
    parsed = parse_docstring(docstring, errors)
    assert not errors, [str(e.descr()) for e in errors]
    
    toc = parsed.get_toc(4)
    assert toc is not None
    html = flatten(toc.to_stan(NotFoundLinker()))
    
    expected_html="""
    <li>
 <p class="rst-first">
  <a class="rst-internal rst-reference" href="#rst-titles" id="rst-toc-entry-1">
   Titles
  </a>
 </p>
 <ul class="rst-simple">
  <li>
   <a class="rst-internal rst-reference" href="#rst-level-2" id="rst-toc-entry-2">
    Level 2
   </a>
   <ul>
    <li>
     <a class="rst-internal rst-reference" href="#rst-level-3" id="rst-toc-entry-3">
      Level 3
     </a>
    </li>
   </ul>
  </li>
  <li>
   <a class="rst-internal rst-reference" href="#rst-level-22" id="rst-toc-entry-4">
    Level 2.2
   </a>
  </li>
  <li>
   <a class="rst-internal rst-reference" href="#rst-level-22-1" id="rst-toc-entry-5">
    Level 22
   </a>
  </li>
 </ul>
</li>
<li>
 <a class="rst-internal rst-reference" href="#rst-lists" id="rst-toc-entry-6">
  Lists
 </a>
</li>
<li>
 <a class="rst-internal rst-reference" href="#rst-other" id="rst-toc-entry-7">
  Other
 </a>
</li>
"""
    assert prettify(html) == prettify(expected_html)
