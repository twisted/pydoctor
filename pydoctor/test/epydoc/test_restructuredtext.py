import pprint
from typing import List
from unittest import skip
from pydoctor.epydoc.markup import ParseError, flatten, restructuredtext
from pydoctor.epydoc.markup.restructuredtext import parse_docstring
from bs4 import BeautifulSoup

# FIRST PART OF THE TESTS

def rst2html(s: str) -> str:
    errors: List[ParseError] = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return flatten(parsed.to_stan(None))

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

# THIS IS HELPER METHODS
from pydoctor.epydoc.markup import flatten, restructuredtext
def to_html(docstring) -> str:
    """
    Utility method to convert a docstring to html with pydoctor. 
    """
    err = []
    p = restructuredtext.parse_docstring(docstring, err)
    if [ e.__dict__ for e in err ]!=[]: 
        raise ValueError("\n".join([ pprint.pformat(e.__dict__) for e in err ]))
    html=flatten(p.to_stan(None))
    return html

def parse_and_print(s):
     errors = []
     parsed = restructuredtext.parse_docstring(s, errors)
     for error in errors:
         print(f'ERROR: {error}')
     if parsed is None:
         print('EMPTY BODY')
     else:
         print(flatten(parsed.to_stan(None)))
     for field in parsed.fields:
         body = flatten(field.body().to_stan(None))
         arg = field.arg()
         if arg is None:
             print(f'{field.tag()}: {body}')
         else:
             print(f'{field.tag()} "{arg}": {body}')

# TESTS FOR NOT IMPLEMENTTED FEATURES 

'''
def test_rst_directive_abnomitions() -> None:
    html = to_html(".. warning:: Hey")
    expected_html="""
        <div class="admonition warning">
        <p class="admonition-title">Warning</p>
        <p>Hey</p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree
    
    html = to_html(".. note:: Hey")
    expected_html = """
        <div class="admonition note">
        <p class="admonition-title">Note</p>
        <p>Hey</p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree

def test_rst_directive_versionadded() -> None:
    html = to_html(".. versionadded:: 0.6")
    expected_html="""
        <div class="versionadded">
        <p><span class="versionmodified added">New in version 0.6.</span></p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree

def test_rst_directive_versionchanged() -> None:
    html = to_html(""".. versionchanged:: 0.7
    Add extras""")
    expected_html="""
        <div class="versionchanged">
        <p><span class="versionmodified changed">Changed in version 0.7: Add extras</span></p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree

def test_rst_directive_deprecated() -> None:
    html = to_html(""".. deprecated:: 0.2
    For security reasons""")
    expected_html="""
        <div class="deprecated">
        <p><span class="versionmodified deprecated">Deprecated since version 0.2: For security reasons</span></p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree
'''