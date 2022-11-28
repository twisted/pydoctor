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
    errors: List[ParseError] = []
    parsed = get_parser_by_name(markup)(doc, errors)
    if processtypes:
        pydoctor.epydoc.markup.processtypes(parsed, errors)
    assert not errors, [f"{e.linenum()}:{e.descr()}" for e in errors]
    return parsed
