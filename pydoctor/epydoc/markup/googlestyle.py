#
# google.py: google-style docstring parsing
#
# Created [16/01/2021]
#

"""
Parser for google-style docstrings. 

This parser is built on top of a forked version of the Sphinx extension: Napoleon.  
"""
from typing import Callable, List

from pydoctor.epydoc.markup import ParsedDocstring, ParseError
from pydoctor.epydoc.markup.restructuredtext import parse_docstring as parse_restructuredtext_docstring
from pydoctor.epydoc.markup.napoleon.docstring import GoogleDocstring
from pydoctor.model import Attribute, Documentable

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

def parse_inline_attribute_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Napoleon google-style docstrings processing was designed to be working with a reference to
    the actual live object. So it could check wheither or not the object was an attribute. We can't do that
    here, so there is another function to parse attribute docstrings. 

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    rst_docstring = str(GoogleDocstring(docstring, is_attribute = True))
    return parse_restructuredtext_docstring(rst_docstring, errors)

def get_parser(obj:Documentable) -> Callable[[str,List[ParseError]], ParsedDocstring]:
    """
    Returns the `parse_docstring` function or the `parse_inline_attribute_docstring` 
    function depending if the documentable is an attribute or not. 
    """
    return parse_inline_attribute_docstring if isinstance(obj, Attribute) else parse_docstring

