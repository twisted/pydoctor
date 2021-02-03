"""
Parser for numpy-style docstrings. 

@See: L{pydoctor.epydoc.markup.google}
"""
from typing import Callable, List

from pydoctor.epydoc.markup import ParsedDocstring, ParseError
from pydoctor.epydoc.markup.google import parse_g_docstring, ParsedGoogleStyleDocstring
from pydoctor.napoleon.docstring import NumpyDocstring
from pydoctor.model import Attribute, Documentable

def parse_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted as NumPy style docstring; and
    return a L{ParsedDocstring} representation of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    # init napoleon.docstring.NumpyDocstring 
    np_docstring = NumpyDocstring(docstring)
    parsed_doc = parse_g_docstring(np_docstring, errors)
    return ParsedNumpyStyleDocstring(parsed_doc,   
                                     docstring, str(np_docstring))

def parse_attribute_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Napoleon google-style docstrings processing was designed to be working with a reference to
    the actual live object. So it could check if the object was an attribute. We can't do that
    here, so there is another function to parse attribute docstrings. Attribute docstring have 
    a different syntax. 

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    np_docstring = NumpyDocstring(docstring, is_attribute = True)
    parsed_doc = parse_g_docstring(np_docstring, errors)
    return ParsedNumpyStyleDocstring(parsed_doc,   
                                     docstring, str(np_docstring))

def get_parser(obj:Documentable) -> Callable[[str, List[ParseError]], ParsedDocstring]:
    """
    Returns the L{parse_docstring} function or the L{parse_attribute_docstring} 
    function depending on the documentable type. 
    """
    return parse_attribute_docstring if isinstance(obj, Attribute) else parse_docstring

class ParsedNumpyStyleDocstring(ParsedGoogleStyleDocstring):
    """
    Just like L{ParsedGoogleStyleDocstring}. 
    """