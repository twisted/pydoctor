from typing import List

from pydoctor.epydoc.markup import DocstringLinker, ParseError, epytext
from pydoctor.test import NotFoundLinker
from pydoctor.stanutils import flatten

def epytext2html(s: str, linker: DocstringLinker = NotFoundLinker()) -> str:
    errs: List[ParseError] = []
    v = flatten(epytext.parse_docstring(s, errs).to_stan(linker))
    if errs:
        raise errs[0]
    return (v or '').rstrip()


def parse(s: str) -> str:
    errors: List[ParseError] = []
    element = epytext.parse(s, errors)
    if element is None:
        raise errors[0]
    else:
        # this strips off the <epytext>...</epytext>
        return ''.join(str(n) for n in element.children)

def test_links() -> None:
    L1 = 'L{link}'
    L2 = 'L{something.link}'
    L3 = 'L{any kind of text since intersphinx name can contain spaces}'
    L4 = 'L{looks-like-identifier}'
    L5 = 'L{this stuff <any kind of text>}'
    L6 = 'L{this stuff <looks-like-identifier>}'

    assert parse(L1) == "<para><link><name>link</name><target lineno='0'>link</target></link></para>"
    assert parse(L2) == "<para><link><name>something.link</name><target lineno='0'>something.link</target></link></para>"
    assert parse(L3) == "<para><link><name>any kind of text since intersphinx name can contain spaces</name><target lineno='0'>any kind of text since intersphinx name can contain spaces</target></link></para>"
    assert parse(L4) == "<para><link><name>looks-like-identifier</name><target lineno='0'>looks-like-identifier</target></link></para>"
    assert parse(L5) == "<para><link><name>this stuff</name><target lineno='0'>any kind of text</target></link></para>"
    assert parse(L6) == "<para><link><name>this stuff</name><target lineno='0'>looks-like-identifier</target></link></para>"

def test_basic_list() -> None:
    P1 = "This is a paragraph."
    P2 = "This is a \nparagraph."
    LI1 = "  - This is a list item."
    LI2 = "\n  - This is a list item."
    LI3 = "  - This is a list\n  item."
    LI4 = "\n  - This is a list\n  item."
    PARA = ('<para>This is a paragraph.</para>')
    ONELIST = ('<ulist><li><para>This is a '
               'list item.</para></li></ulist>')
    TWOLIST = ('<ulist><li><para>This is a '
               'list item.</para></li><li><para>This is a '
               'list item.</para></li></ulist>')

    for p in (P1, P2):
        for li1 in (LI1, LI2, LI3, LI4):
            assert parse(li1) == ONELIST
            assert parse(f'{p}\n{li1}') == PARA+ONELIST
            assert parse(f'{li1}\n{p}') == ONELIST+PARA
            assert parse(f'{p}\n{li1}\n{p}') == PARA+ONELIST+PARA

            for li2 in (LI1, LI2, LI3, LI4):
                assert parse(f'{li1}\n{li2}') == TWOLIST
                assert parse(f'{p}\n{li1}\n{li2}') == PARA+TWOLIST
                assert parse(f'{li1}\n{li2}\n{p}') == TWOLIST+PARA
                assert parse(f'{p}\n{li1}\n{li2}\n{p}') == PARA+TWOLIST+PARA

    LI5 = "  - This is a list item.\n\n    It contains two paragraphs."
    LI5LIST = ('<ulist><li><para>This is a list item.</para>'
               '<para>It contains two paragraphs.</para></li></ulist>')
    assert parse(LI5) == LI5LIST
    assert parse(f'{P1}\n{LI5}') == PARA+LI5LIST
    assert parse(f'{P2}\n{LI5}\n{P1}') == PARA+LI5LIST+PARA

    LI6 = ("  - This is a list item with a literal block::\n"
           "    hello\n      there")
    LI6LIST = ('<ulist><li><para>This is a list item with a literal '
               'block:</para><literalblock>  hello\n    there'
               '</literalblock></li></ulist>')
    assert parse(LI6) == LI6LIST
    assert parse(f'{P1}\n{LI6}') == PARA+LI6LIST
    assert parse(f'{P2}\n{LI6}\n{P1}') == PARA+LI6LIST+PARA


def test_item_wrap() -> None:
    LI = "- This is a list\n  item."
    ONELIST = ('<ulist><li><para>This is a '
               'list item.</para></li></ulist>')
    TWOLIST = ('<ulist><li><para>This is a '
               'list item.</para></li><li><para>This is a '
               'list item.</para></li></ulist>')
    for indent in ('', '  '):
        for nl1 in ('', '\n'):
            assert parse(nl1+indent+LI) == ONELIST
            for nl2 in ('\n', '\n\n'):
                assert parse(nl1+indent+LI+nl2+indent+LI) == TWOLIST


def test_literal_braces() -> None:
    """SF bug #1562530 reported some trouble with literal braces.
    This test makes sure that braces are getting rendered as desired.
    """
    assert epytext2html("{1:{2:3}}") == '{1:{2:3}}'
    assert epytext2html("C{{1:{2:3}}}") == '<tt class="rst-docutils literal"><span class="pre">{1:{2:3}}</span></tt>'
    assert epytext2html("{1:C{{2:3}}}") == '{1:<tt class="rst-docutils literal">{2:3}</tt>}'
    assert epytext2html("{{{}{}}{}}") == '{{{}{}}{}}'
    assert epytext2html("{{E{lb}E{lb}E{lb}}}") == '{{{{{}}'

def test_slugify() -> None:
    assert epytext.slugify("Héllo Wörld 1.2.3") == "hello-world-123"
