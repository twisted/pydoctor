# epydoc -- Regression testing
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

from typing import List
from pydoctor.epydoc.markup import ParseError, ParsedDocstring, get_parser_by_name
import pydoctor.epydoc.markup

def parse_docstring(doc: str, markup: str, processtypes: bool = False) -> ParsedDocstring:
    
    parse = get_parser_by_name(markup)
    if processtypes:
        if markup in ('google','numpy'):
            raise AssertionError("don't process types twice.")
        parse = pydoctor.epydoc.markup.processtypes(parse)
    
    errors: List[ParseError] = []
    parsed = parse(doc, errors)
    assert not errors, [f"{e.linenum()}:{e.descr()}" for e in errors]
    return parsed
