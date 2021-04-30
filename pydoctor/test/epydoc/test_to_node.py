from typing import List
from pydoctor.epydoc.markup import ParsedDocstring, ParseError, get_parser_by_name, flatten
from pydoctor.test import NotFoundLinker

def doc2html(doc: str, markup: str = 'restructuredtext') -> str:
    err: List[ParseError] = []
    parsed_doc = get_parser_by_name(markup)(doc, err)
    assert not err
    return flatten(parsed_doc.to_stan(NotFoundLinker()))

cases = [   
            'list of int or float or None', 
            "{'F', 'C', 'N'}, default 'N'",
            "DataFrame, optional",
            "List[str] or list(bytes), optional",]

def test_to_node_no_markup() -> None:
    for s in cases:
        assert doc2html(s, 'restructuredtext') == doc2html(s, 'epytext')

cases2 = [  ('L{me}', '`me`'),
            ('B{No!}', '**No!**'),
            ('I{here}', '*here*'),
            ('L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}', '`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`')
            ]

def test_to_node_markup() -> None:
    for epystr, rststr in cases2:
        assert doc2html(rststr, 'restructuredtext') == doc2html(epystr, 'epytext')
