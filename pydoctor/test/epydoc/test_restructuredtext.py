from typing import List

from pydoctor.epydoc.markup import DocstringLinker, ParseError, flatten
from pydoctor.epydoc.markup.restructuredtext import parse_docstring
from pydoctor.test import NotFoundLinker

from bs4 import BeautifulSoup
import pytest


def rst2html(docstring: str, linker: DocstringLinker = NotFoundLinker()) -> str:
    """
    Render a docstring to HTML.
    """
    errors: List[ParseError] = []
    parsed = parse_docstring(docstring, errors)
    assert not errors
    return flatten(parsed.to_stan(linker))

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

def prettify(html: str) -> str:
    return BeautifulSoup(html, features="html.parser").prettify()  # type: ignore[no-any-return]

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
