import pytest
from typing import List
from pydoctor.epydoc.markup import ParseError, flatten, restructuredtext
from pydoctor.epydoc.markup.restructuredtext import parse_docstring
from bs4 import BeautifulSoup

def rst2html(s: str) -> str:
    errors: List[ParseError] = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return flatten(parsed.to_stan(None))

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

def to_html(docstring: str) -> str:
    """
    Utility method to convert a docstring to html with pydoctor.
    """
    err: List[ParseError] = []
    p = restructuredtext.parse_docstring(docstring, err)
    if err:
        raise ValueError("\n".join(repr(e) for e in err))
    html=flatten(p.to_stan(None))
    return html

def prettify(html: str) -> str:
    return BeautifulSoup(html).prettify()  # type: ignore[no-any-return]

# TESTS FOR NOT IMPLEMENTTED FEATURES

@pytest.mark.xfail
def test_rst_directive_abnomitions() -> None:
    html = to_html(".. warning:: Hey")
    expected_html="""
        <div class="admonition warning">
        <p class="admonition-title">Warning</p>
        <p>Hey</p>
        </div>"""
    assert prettify(html) == prettify(expected_html)

    html = to_html(".. note:: Hey")
    expected_html = """
        <div class="admonition note">
        <p class="admonition-title">Note</p>
        <p>Hey</p>
        </div>"""
    assert prettify(html) == prettify(expected_html)

@pytest.mark.xfail
def test_rst_directive_versionadded() -> None:
    html = to_html(".. versionadded:: 0.6")
    expected_html="""
        <div class="versionadded">
        <p><span class="versionmodified added">New in version 0.6.</span></p>
        </div>"""
    assert prettify(html) == prettify(expected_html)

@pytest.mark.xfail
def test_rst_directive_versionchanged() -> None:
    html = to_html(""".. versionchanged:: 0.7
    Add extras""")
    expected_html="""
        <div class="versionchanged">
        <p><span class="versionmodified changed">Changed in version 0.7: Add extras</span></p>
        </div>"""
    assert prettify(html) == prettify(expected_html)

@pytest.mark.xfail
def test_rst_directive_deprecated() -> None:
    html = to_html(""".. deprecated:: 0.2
    For security reasons""")
    expected_html="""
        <div class="deprecated">
        <p><span class="versionmodified deprecated">Deprecated since version 0.2: For security reasons</span></p>
        </div>"""
    assert prettify(html) == prettify(expected_html)
