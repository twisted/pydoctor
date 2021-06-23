"""
Test generic features of ParsedDocstring. 
"""
from typing import List
from twisted.web.template import Tag
from pydoctor.epydoc.markup import ParsedDocstring, ParseError, flatten
from pydoctor.epydoc.markup.plaintext import parse_docstring
from pydoctor.test.epydoc.test_epytext2html import parse_epytext
from pydoctor.test.epydoc.test_restructuredtext import parse_rst, prettify
from pydoctor.test import NotFoundLinker

def parse_plaintext(s: str) -> ParsedDocstring:
    errors: List[ParseError] = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return parsed

def flatten_(stan: Tag) -> str:
    return ''.join(l.strip() for l in prettify(flatten(stan)).splitlines())

def test_to_node_to_stan_caching() -> None:
    """
    Test if we get the same value again and again.
    """
    epy = parse_epytext('Just some B{strings}')
    assert epy.to_node() == epy.to_node() == epy.to_node()
    assert flatten_(epy.to_stan(NotFoundLinker())) == flatten_(epy.to_stan(NotFoundLinker())) == flatten_(epy.to_stan(NotFoundLinker()))

    rst = parse_rst('Just some **strings**')
    assert rst.to_node() == rst.to_node() == rst.to_node()
    assert flatten_(rst.to_stan(NotFoundLinker())) == flatten_(rst.to_stan(NotFoundLinker())) == flatten_(rst.to_stan(NotFoundLinker()))

    plain = parse_plaintext('Just some **strings**')
    assert plain.to_node() == plain.to_node() == plain.to_node()
    assert flatten_(plain.to_stan(NotFoundLinker())) == flatten_(plain.to_stan(NotFoundLinker())) == flatten_(plain.to_stan(NotFoundLinker()))
