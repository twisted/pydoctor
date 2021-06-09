from typing import List
from textwrap import dedent

from pydoctor.epydoc.markup import DocstringLinker, ParseError, flatten, ParsedDocstring
from pydoctor.epydoc.markup.restructuredtext import parse_docstring
from pydoctor.test import NotFoundLinker
from pydoctor.node2stan import node2stan

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

@pytest.mark.xfail
def test_rst_directive_versionadded() -> None:
    html = rst2html(".. versionadded:: 0.6")
    expected_html="""
        <div class="versionadded">
        <p><span class="versionmodified added">New in version 0.6.</span></p>
        </div>"""
    assert prettify(html) == prettify(expected_html)

@pytest.mark.xfail
def test_rst_directive_versionchanged() -> None:
    html = rst2html(""".. versionchanged:: 0.7
    Add extras""")
    expected_html="""
        <div class="versionchanged">
        <p><span class="versionmodified changed">Changed in version 0.7: Add extras</span></p>
        </div>"""
    assert prettify(html) == prettify(expected_html)

@pytest.mark.xfail
def test_rst_directive_deprecated() -> None:
    html = rst2html(""".. deprecated:: 0.2
    For security reasons""")
    expected_html="""
        <div class="deprecated">
        <p><span class="versionmodified deprecated">Deprecated since version 0.2: For security reasons</span></p>
        </div>"""
    assert prettify(html) == prettify(expected_html)
