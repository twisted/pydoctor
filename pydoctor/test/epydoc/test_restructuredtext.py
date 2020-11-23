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

@skip
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

@skip
def test_rst_directive_versionadded() -> None:
    html = to_html(".. versionadded:: 0.6")
    expected_html="""
        <div class="versionadded">
        <p><span class="versionmodified added">New in version 0.6.</span></p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree

@skip
def test_rst_directive_versionchanged() -> None:
    html = to_html(""".. versionchanged:: 0.7
    Add extras""")
    expected_html="""
        <div class="versionchanged">
        <p><span class="versionmodified changed">Changed in version 0.7: Add extras</span></p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree

@skip
def test_rst_directive_deprecated() -> None:
    html = to_html(""".. deprecated:: 0.2
    For security reasons""")
    expected_html="""
        <div class="deprecated">
        <p><span class="versionmodified deprecated">Deprecated since version 0.2: For security reasons</span></p>
        </div>"""
    assert BeautifulSoup(html, 'html.parser').tree==BeautifulSoup(expected_html, 'html.parser').tree

"""
:Parameters:
    size
        The size of the fox (in meters)
    weight : float
        The weight of the fox (in stones)
    age : int
        The age of the fox (in years)
"""

"""
:param size: The size of the fox (in meters)
:param weight: The weight of the fox (in stones)
:param age: The age of the fox (in years)
:type weight: float
:type age: age
"""

"""
:param str sender: The person sending the message
:param str recipient: The recipient of the message
:param str message_body: The body of the message
:param priority: The priority of the message, can be a number 1-5
:type priority: integer or None
:return: the message id
:rtype: int
:raises ValueError: if the message_body exceeds 160 characters
:raises TypeError: if the message_body is not a basestring



Docstring markup parsing is handled by the `markup` package.
See the submodule list for more information about the submodules
and subpackages.

:group Docstring Processing: markup
:group Miscellaneous: util, test

:author: `Edward Loper <edloper@gradient.cis.upenn.edu>`__
:requires: Python 2.3+
:version: 3.0.1
:see: `The epydoc webpage <http://epydoc.sourceforge.net>`__
:see: `The epytext markup language manual <http://epydoc.sourceforge.net/epytext.html>`__

:todo: Create a better default top_page than trees.html.
:todo: Fix trees.html to work when documenting non-top-levelmodules/packages
:todo: Implement @include
:todo: Optimize epytext
:todo: More doctests
:todo: When introspecting, limit how much introspection you do (eg, don't construct docs for imported modules' vars if it's not necessary)

:bug: UserDict.* is interpreted as imported .. why??

:license: IBM Open Source License
:copyright: |copy| 2006 Edward Loper

:newfield contributor: Contributor, Contributors (Alphabetical Order)
:contributor: `Glyph Lefkowitz  <mailto:glyph@twistedmatrix.com>`__
:contributor: `Edward Loper  <mailto:edloper@gradient.cis.upenn.edu>`__
:contributor: `Bruce Mitchener  <mailto:bruce@cubik.org>`__
:contributor: `Jeff O'Halloran  <mailto:jeff@ohalloran.ca>`__
:contributor: `Simon Pamies  <mailto:spamies@bipbap.de>`__
:contributor: `Christian Reis  <mailto:kiko@async.com.br>`__
:contributor: `Daniele Varrazzo  <mailto:daniele.varrazzo@gmail.com>`__
:contributor: `Jonathan Guyer <mailto:guyer@nist.gov>`__

.. |copy| unicode:: 0xA9 .. copyright sign


Continue read in https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#
and https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#directives
"""