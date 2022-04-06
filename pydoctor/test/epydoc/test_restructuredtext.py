from typing import List
from textwrap import dedent

from pydoctor.epydoc.markup import DocstringLinker, ParseError, ParsedDocstring, get_parser_by_name
from pydoctor.epydoc.markup.restructuredtext import parse_docstring
from pydoctor.test import NotFoundLinker
from pydoctor.node2stan import node2stan
from pydoctor.stanutils import flatten, flatten_text

from docutils import nodes
from bs4 import BeautifulSoup
import pytest

def prettify(html: str) -> str:
    return BeautifulSoup(html, features="html.parser").prettify()  # type: ignore[no-any-return]

def parse_rst(s: str) -> ParsedDocstring:
    errors: List[ParseError] = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return parsed

def rst2html(docstring: str, linker: DocstringLinker = NotFoundLinker()) -> str:
    """
    Render a docstring to HTML.
    """
    return flatten(parse_rst(docstring).to_stan(linker))
    
def node2html(node: nodes.Node, oneline: bool = True) -> str:
    if oneline:
        return ''.join(prettify(flatten(node2stan(node, NotFoundLinker()))).splitlines())
    else:
        return flatten(node2stan(node, NotFoundLinker()))

def rst2node(s: str) -> nodes.document:
    return parse_rst(s).to_node()

def test_rst_partial() -> None:
    """
    The L{node2html()} function can convert fragment of a L{docutils} document, 
    it's not restricted to actual L{docutils.nodes.document} object. 
    
    Really, any nodes can be passed to that function, the only requirement is 
    that the node's C{document} attribute is set to a valid L{docutils.nodes.document} object.
    """
    doc = dedent('''
        This is a paragraph.  Paragraphs can
        span multiple lines, and can contain
        `inline markup`.

        This is another paragraph.  Paragraphs
        are separated by blank lines.
        ''')
    expected = dedent('''
        <p>This is another paragraph.  Paragraphs
        are separated by blank lines.</p>
        ''').lstrip()
    
    node = rst2node(doc)

    for child in node[:]:
          assert isinstance(child, nodes.paragraph)
    
    assert node2html(node[-1], oneline=False) == expected
    assert node[-1].parent == node

def test_rst_body_empty() -> None:
    src = """
    :return: a number
    :rtype: int
    """
    errors: List[ParseError] = []
    pdoc = parse_docstring(src, errors)
    assert not errors
    assert not pdoc.has_body
    assert len(pdoc.fields) == 2

def test_rst_body_nonempty() -> None:
    src = """
    Only body text, no fields.
    """
    errors: List[ParseError] = []
    pdoc = parse_docstring(src, errors)
    assert not errors
    assert pdoc.has_body
    assert len(pdoc.fields) == 0

def test_rst_anon_link_target_missing() -> None:
    src = """
    This link's target is `not defined anywhere`__.
    """
    errors: List[ParseError] = []
    parse_docstring(src, errors)
    assert len(errors) == 1
    assert errors[0].descr().startswith("Anonymous hyperlink mismatch:")
    assert errors[0].is_fatal()

def test_rst_anon_link_email() -> None:
    src = "`<postmaster@example.net>`__"
    html = rst2html(src)
    assert html.startswith('<a ')
    assert ' href="mailto:postmaster@example.net"' in html
    assert html.endswith('>mailto:postmaster@example.net</a>')

def test_rst_xref_with_target() -> None:
    src = "`mapping <typing.MutableMapping>`"
    html = rst2html(src)
    assert html.startswith('<code>mapping</code>')

def test_rst_xref_implicit_target() -> None:
    src = "`func()`"
    html = rst2html(src)
    assert html.startswith('<code>func()</code>')

def test_rst_directive_adnomitions() -> None:
    expected_html_multiline="""
        <div class="rst-admonition {}">
        <p class="rst-first rst-admonition-title">{}</p>
        <p>this is the first line</p>
        <p class="rst-last">and this is the second line</p>
        </div>
"""

    expected_html_single_line = """
        <div class="rst-admonition {}">
        <p class="rst-first rst-admonition-title">{}</p>
        <p class="rst-last">this is a single line</p>
        </div>
"""

    admonition_map = {
            'Attention': 'attention',
            'Caution': 'caution',
            'Danger': 'danger',
            'Error': 'error',
            'Hint': 'hint',
            'Important': 'important',
            'Note': 'note',
            'Tip': 'tip',
            'Warning': 'warning',
        }

    for title, admonition_name in admonition_map.items():
        # Multiline
        docstring = (".. {}::\n"
                    "\n"
                    "   this is the first line\n"
                    "   \n"
                    "   and this is the second line\n"
                    ).format(admonition_name)

        expect = expected_html_multiline.format(
            admonition_name, title
        )

        actual = rst2html(docstring)

        assert prettify(expect)==prettify(actual)

        # Single line
        docstring = (".. {}:: this is a single line\n"
                    ).format(admonition_name)

        expect = expected_html_single_line.format(
            admonition_name, title
        )

        actual = rst2html(docstring)

        assert prettify(expect)==prettify(actual)


def test_rst_directive_versionadded() -> None:
    """
    It renders the C{versionadded} RST directive using a custom markup with
    dedicated CSS classes.
    """
    html = rst2html(".. versionadded:: 0.6")
    expected_html="""<div class="rst-versionadded">
<span class="rst-versionmodified rst-added">New in version 0.6.</span></div>
"""
    assert html==expected_html, html

def test_rst_directive_versionchanged() -> None:
    """
    It renders the C{versionchanged} RST directive with custom markup and supports
    an extra text besides the version information.
    """
    html = rst2html(""".. versionchanged:: 0.7
    Add extras""")
    expected_html="""<div class="rst-versionchanged">
<span class="rst-versionmodified rst-changed">Changed in version 0.7: </span><span>Add extras</span></div>
"""
    assert html==expected_html, html

def test_rst_directive_deprecated() -> None:
    """
    It renders the C{deprecated} RST directive with custom markup and supports
    an extra text besides the version information.
    """
    html = rst2html(""".. deprecated:: 0.2
    For security reasons""")
    expected_html="""<div class="rst-deprecated">
<span class="rst-versionmodified rst-deprecated">Deprecated since version 0.2: </span><span>For security reasons</span></div>
"""
    assert html==expected_html, html
    
def test_rst_directive_seealso() -> None:

    html = rst2html(".. seealso:: Hey")
    expected_html = """
        <div class="rst-admonition seealso">
        <p class="rst-first rst-admonition-title">See Also</p>
        <p class="rst-last">Hey</p>
        </div>"""
    assert prettify(html).strip() == prettify(expected_html).strip(), html


@pytest.mark.parametrize(
    'markup', ('epytext', 'plaintext', 'restructuredtext', 'numpy', 'google')
    )
def test_summary(markup:str) -> None:
    cases = [
        ("Single line", "Single line"), 
        ("Single line.", "Single line."), 
        ("Single line with period.", "Single line with period."),
        ("""
        Single line with period.
        
        @type: Also with a tag.
        """, "Single line with period."), 
        ("Other lines with period.\nThis is attached", "Other lines with period. This is attached"),
        ("Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. ", 
         "Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line. Single line..."),
        ("Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line. Single line Single line Single line ", 
         "Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line Single line..."),
        ("""
        Return a fully qualified name for the possibly-dotted name.

        To explain what this means, consider the following modules... blabla""",
        "Return a fully qualified name for the possibly-dotted name.")
    ]
    for src, summary_text in cases:
        errors: List[ParseError] = []
        pdoc = get_parser_by_name(markup)(dedent(src), errors, False)
        assert not errors
        assert pdoc.get_summary() == pdoc.get_summary() # summary is cached inside ParsedDocstring as well.
        assert flatten_text(pdoc.get_summary().to_stan(NotFoundLinker())) == summary_text