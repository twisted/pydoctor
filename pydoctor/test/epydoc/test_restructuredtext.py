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
    assert not errors, [e.descr() for e in errors]
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
    return BeautifulSoup(html).prettify()  # type: ignore[no-any-return]

def test_rst_directive_abnomitions() -> None:
    html = rst2html(".. warning:: Hey")
    expected_html="""
        <div class="rst-admonition warning">
        <p class="rst-first rst-admonition-title">Warning</p>
        <p class="rst-last">Hey</p>
        </div>"""
    assert prettify(html).strip() == prettify(expected_html).strip(), html

    html = rst2html(".. note:: Hey")
    expected_html = """
        <div class="rst-admonition note">
        <p class="rst-first rst-admonition-title">Note</p>
        <p class="rst-last">Hey</p>
        </div>"""
    assert prettify(html).strip() == prettify(expected_html).strip(), html

def test_rst_directive_seealso() -> None:

    html = rst2html(".. seealso:: Hey")
    expected_html = """
        <div class="rst-admonition seealso">
        <p class="rst-first rst-admonition-title">See Also</p>
        <p class="rst-last">Hey</p>
        </div>"""
    assert prettify(html).strip() == prettify(expected_html).strip(), html


def test_rst_directive_versionadded() -> None:
    html = rst2html(".. versionadded:: 0.6")
    expected_html="""
        <div class="rst-versionadded">
        <p><span class="rst-versionmodified rst-added">New in version 0.6.</span></p>
        </div>
"""
    assert prettify(html) == prettify(expected_html)


def test_rst_directive_versionchanged() -> None:
    html = rst2html(""".. versionchanged:: 0.7
    Add extras""")
    expected_html="""
        <div class="rst-versionchanged">
        <p><span class="rst-versionmodified rst-changed">Changed in version 0.7:
        </span>
        <span>
         Add extras
        </span>
        </p>
        </div>
"""
    assert prettify(html) == prettify(expected_html)


def test_rst_directive_deprecated() -> None:
    html = rst2html(""".. deprecated:: 0.2
    For security reasons""")
    expected_html="""
        <div class="rst-deprecated">
        <p><span class="rst-versionmodified rst-deprecated">Deprecated since version 0.2: 
        </span>
        <span>
         For security reasons
        </span>
        </p>
        </div>
        </div>"""
    assert prettify(html) == prettify(expected_html)
