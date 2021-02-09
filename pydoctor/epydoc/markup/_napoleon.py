"""
This module contains a class to wrap shared behaviour between 
L{pydoctor.epydoc.markup.numpy} and L{pydoctor.epydoc.markup.google}. 
"""
from typing import List, Optional, Type

from pydoctor.epydoc.markup import ParsedDocstring, ParseError
from pydoctor.epydoc.markup import restructuredtext
from pydoctor.napoleon.docstring import GoogleDocstring, NumpyDocstring
from pydoctor.model import Attribute, Documentable

class NapoelonDocstringParser:
    """
    Parse google-style or numpy-style docstrings. 

    First wrap the L{pydoctor.napoleon} converter classes, then call 
    L{pydoctor.epydoc.markup.restructuredtext.parse_docstring} with the 
    converted reStructuredText docstring. 

    If the L{Documentable} instance is an L{Attribute}, the docstring
    will be parsed differently. 
    """
    def __init__(self, obj: Optional[Documentable] = None):
        """
        @param obj: Documentable object we're parsing the docstring for. 
        """
        self.obj = obj

    def parse_google_docstring(self, docstring:str, errors:List[ParseError]) -> ParsedDocstring:
        """
        Parse the given docstring, which is formatted as Google style docstring. 
        Return a L{ParsedDocstring} representation of its contents.

        @param docstring: The docstring to parse
        @param errors: A list where any errors generated during parsing
            will be stored.
        """
        return self._parse_docstring(docstring, errors, GoogleDocstring, ParsedGoogleStyleDocstring)
    
    def parse_numpy_docstring(self, docstring:str, errors:List[ParseError]) -> ParsedDocstring:
        """
        Parse the given docstring, which is formatted as NumPy style docstring.
        Return a L{ParsedDocstring} representation of its contents.

        @param docstring: The docstring to parse
        @param errors: A list where any errors generated during parsing
            will be stored.
        """
        return self._parse_docstring(docstring, errors, NumpyDocstring, ParsedNumpyStyleDocstring)

    def _parse_docstring(self, docstring:str, errors:List[ParseError], 
                         docstring_cls:Type[GoogleDocstring],
                         parsed_docstring_cls:Type['ParsedGoogleStyleDocstring']) -> ParsedDocstring:
        
        docstring_obj = docstring_cls(docstring, 
                                      is_attribute=isinstance(self.obj, Attribute))

        parsed_doc = self._parse_docstring_obj(docstring_obj, errors)

        return parsed_docstring_cls(parsed_doc,   
                                    docstring, str(docstring_obj))


    @staticmethod
    def _parse_docstring_obj(docstring_obj:GoogleDocstring, 
                            errors: List[ParseError]) -> ParsedDocstring:
        """
        Helper method to parse L{GoogleDocstring} or L{NumpyDocstring} objects.
        """
        # log any warnings
        for warn, linenum in docstring_obj.warnings():
            errors.append(ParseError(warn, linenum-1, is_fatal=False))
        # Get the converted reST string and parse it with docutils
        return restructuredtext.parse_docstring(str(docstring_obj), errors)    


class ParsedGoogleStyleDocstring(restructuredtext.ParsedRstDocstring):
    """
    Just like L{ParsedRstDocstring} but it stores references to the original 
    docstring text as well as the napoleon processed docstring. 

    This values are only used for testing purposes. 
    """

    def __init__(self, parsed_rst_docstring: restructuredtext.ParsedRstDocstring, 
                original_docstring: str, 
                napoleon_processed_docstring: str):

        super().__init__(parsed_rst_docstring._document, parsed_rst_docstring.fields)
        self._original_docstring = original_docstring
        self._napoleon_processed_docstring = napoleon_processed_docstring


class ParsedNumpyStyleDocstring(ParsedGoogleStyleDocstring):
    """
    Just like L{ParsedGoogleStyleDocstring}. 
    """
