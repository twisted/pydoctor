from typing import List
from pydoctor.epydoc.markup import ParseError, ParsedDocstring, get_parser_by_name, flatten
from pydoctor.test.epydoc.test_restructuredtext import prettify
from pydoctor.test import NotFoundLinker

def doc2html(doc: str, markup: str) -> str:
    return ''.join(prettify(flatten(parse_docstring(doc, markup).to_stan(NotFoundLinker()))).splitlines())

def parse_docstring(doc: str, markup: str, processtypes: bool = False) -> ParsedDocstring:
    errors: List[ParseError] = []
    parsed = get_parser_by_name(markup)(doc, errors, processtypes)
    assert not errors
    return parsed

def test_to_node_no_markup() -> None:
    cases = [   
            'list of int or float or None', 
            "{'F', 'C', 'N'}, default 'N'",
            "DataFrame, optional",
            "List[str] or list(bytes), optional",]

    for s in cases:
        assert doc2html(s, 'restructuredtext') == doc2html(s, 'epytext')

def test_to_node_markup() -> None:

    cases = [  ('L{me}', '`me`'),
            ('B{No!}', '**No!**'),
            ('I{here}', '*here*'),
            ('L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}', '`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`')
            ]

    for epystr, rststr in cases:
        assert doc2html(rststr, 'restructuredtext') == doc2html(epystr, 'epytext')
