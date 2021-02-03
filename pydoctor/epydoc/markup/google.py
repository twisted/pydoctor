"""
Parser for google-style docstrings. 

@See: L{pydoctor.epydoc.markup.numpy}
"""
from typing import Callable, List

from pydoctor.epydoc.markup import ParsedDocstring, ParseError
from pydoctor.epydoc.markup.restructuredtext import parse_docstring as parse_restructuredtext_docstring
from pydoctor.epydoc.markup.restructuredtext import ParsedRstDocstring
from pydoctor.napoleon.docstring import GoogleDocstring
from pydoctor.model import Attribute, Documentable


def parse_g_docstring(g_docstring:GoogleDocstring, 
                      errors: List[ParseError]) -> ParsedDocstring:
    """
    Helper method to parse L{GoogleDocstring} or L{NumpyDocstring} objects.
    """
    # log any warnings
    for warn, linenum in g_docstring.warnings():
        errors.append(ParseError(warn, linenum-1, is_fatal=False))
    # Get the converted reST string and parse it with docutils
    return parse_restructuredtext_docstring(str(g_docstring), errors)    

def parse_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted as Google docstring; and
    return a L{ParsedDocstring} representation of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    # init napoleon.docstring.GoogleDocstring 
    g_docstring = GoogleDocstring(docstring)
    parsed_doc = parse_g_docstring(g_docstring, errors)
    return ParsedGoogleStyleDocstring(parsed_doc, 
                                      docstring, str(g_docstring))

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
    g_docstring = GoogleDocstring(docstring, is_attribute=True)
    parsed_doc = parse_g_docstring(g_docstring, errors)
    return ParsedGoogleStyleDocstring(parsed_doc,   
                                      docstring, str(g_docstring))

def get_parser(obj:Documentable) -> Callable[[str, List[ParseError]], ParsedDocstring]:
    """
    Returns the L{parse_docstring} function or the L{parse_attribute_docstring} 
    function depending on the documentable type. 
    """
    return parse_attribute_docstring if isinstance(obj, Attribute) else parse_docstring

class ParsedGoogleStyleDocstring(ParsedRstDocstring):
    """
    Just like L{ParsedRstDocstring} but it stores references to the original 
    docstring text as well as the napoleon processed docstring. 

    This values are only used for testing purposes. 
    """

    def __init__(self, parsed_rst_docstring: ParsedRstDocstring, 
                original_docstring: str, 
                napoleon_processed_docstring: str):

        super().__init__(parsed_rst_docstring._document, parsed_rst_docstring.fields)
        self._original_docstring = original_docstring
        self._napoleon_processed_docstring = napoleon_processed_docstring