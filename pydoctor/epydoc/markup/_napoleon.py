"""
This module contains shared behaviour between L{pydoctor.epydoc.markup.numpy} and L{pydoctor.epydoc.markup.google}. 
It's basically a wrapper for L{pydoctor.napoleon} that adapts for each L{Documentable} instance. 
"""
from typing import List, Optional, Type, Union

from pathlib import Path
import json
import warnings

from pydoctor.epydoc.markup import ParsedDocstring, ParseError
from pydoctor.epydoc.markup.restructuredtext import parse_docstring as parse_restructuredtext_docstring
from pydoctor.epydoc.markup.restructuredtext import ParsedRstDocstring
from pydoctor import napoleon
from pydoctor.napoleon.docstring import GoogleDocstring, NumpyDocstring
from pydoctor.model import Attribute, Documentable

class NapoelonDocstringParser:
    def __init__(self, obj: Optional[Documentable] = None):
        self.obj = obj

    def parse_google_docstring(self, docstring:str, errors:List[ParseError]) -> ParsedDocstring:
        """
        Parse the given docstring, which is formatted as NumPy style docstring. 
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
                                      is_attribute=isinstance(self.obj, Attribute), 
                                      config=self._load_napoleon_config())

        parsed_doc = self._parse_docstring_obj(docstring_obj, errors)

        return parsed_docstring_cls(parsed_doc,   
                                    docstring, str(docstring_obj))

    # TODO: move this somewhere else not to reload type aliases file for each documentable.
    def _load_napoleon_config(self) -> napoleon.Config:
        """
        Load the napoelon config based on L{System.options} values. 
        """
        config = napoleon.Config()
        if self.obj:
            if self.obj.system.options.napoleon_numpy_returns_allow_free_from:
                config.napoleon_numpy_returns_allow_free_from = True
            for custom_section in self.obj.system.options.napoleon_custom_sections:
                names = custom_section.split(',', 1)
                if len(names) > 1:
                    config.napoleon_custom_sections += tuple(names[0], names[1])
                elif len(names) > 0:
                    config.napoleon_custom_sections += names[0]
            if self.obj.system.options.napoleon_type_aliases:
                path = Path(self.obj.system.options.napoleon_type_aliases)
                if path.is_file():
                    try:
                        with path.open() as fobj:
                            config.napoleon_custom_sections.update(json.load(fobj))
                    except Exception as e:
                        warnings.warn(f"Failed to load custom type aliases: {e}")
                else:
                    warnings.warn(f"Cannot load custom type aliases: '{path}' is not a file. ")
        return config

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
        return parse_restructuredtext_docstring(str(docstring_obj), errors)    


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


class ParsedNumpyStyleDocstring(ParsedGoogleStyleDocstring):
    """
    Just like L{ParsedGoogleStyleDocstring}. 
    """
