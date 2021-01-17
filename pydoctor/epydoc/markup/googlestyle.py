#
# google.py: google-style docstring parsing
#
# Created [16/01/2021]
#

"""
Parser for google-style docstrings. 

This parser is built on top of a forked version of the Sphinx extension: Napoleon.  
"""

from typing import List

from twisted.web.template import Tag, tags

from pydoctor.epydoc.markup import ParsedDocstring, ParseError
from pydoctor.epydoc.markup.restructuredtext import parse_docstring as parse_restructuredtext_docstring
from pydoctor.epydoc.markup.napoleon.docstring import GoogleDocstring


def parse_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted as Google docstring; and
    return a L{ParsedDocstring} representation of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    rst_docstring = str(GoogleDocstring(docstring))
    return parse_restructuredtext_docstring(rst_docstring, errors)
