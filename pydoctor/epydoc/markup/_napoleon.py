"""
This module contains a class to wrap shared behaviour between 
L{pydoctor.epydoc.markup.numpy} and L{pydoctor.epydoc.markup.google}. 
"""
from __future__ import annotations

from pydoctor.epydoc.markup import ObjClass, ParsedDocstring, ParseError, processtypes
from pydoctor.epydoc.markup import restructuredtext
from pydoctor.napoleon.docstring import GoogleDocstring, NumpyDocstring


class NapoelonDocstringParser:
    """
    Parse google-style or numpy-style docstrings.

    First wrap the L{pydoctor.napoleon} converter classes, then call
    L{pydoctor.epydoc.markup.restructuredtext.parse_docstring} with the
    converted reStructuredText docstring.

    If the L{Documentable} instance is an L{Attribute}, the docstring
    will be parsed differently.
    """

    def __init__(self, objclass: ObjClass | None = None):
        """
        @param objclass: Class of the documentable object we're parsing the docstring for.
        """
        self.objclass = objclass

    def parse_google_docstring(
        self, docstring: str, errors: list[ParseError]
    ) -> ParsedDocstring:
        """
        Parse the given docstring, which is formatted as Google style docstring.
        Return a L{ParsedDocstring} representation of its contents.

        @param docstring: The docstring to parse
        @param errors: A list where any errors generated during parsing
            will be stored.
        """
        return self._parse_docstring(
            docstring, errors, GoogleDocstring, )

    def parse_numpy_docstring(
        self, docstring: str, errors: list[ParseError]
    ) -> ParsedDocstring:
        """
        Parse the given docstring, which is formatted as NumPy style docstring.
        Return a L{ParsedDocstring} representation of its contents.

        @param docstring: The docstring to parse
        @param errors: A list where any errors generated during parsing
            will be stored.
        """
        return self._parse_docstring(
            docstring, errors, NumpyDocstring, )

    def _parse_docstring(
        self,
        docstring: str,
        errors: list[ParseError],
        docstring_cls: type[GoogleDocstring],
    ) -> ParsedDocstring:

        docstring_obj = docstring_cls(
            docstring, 
            what=self.objclass,
        )

        return self._parse_docstring_obj(docstring_obj, errors)

    @staticmethod
    def _parse_docstring_obj(
        docstring_obj: GoogleDocstring, errors: list[ParseError]
    ) -> ParsedDocstring:
        """
        Helper method to parse L{GoogleDocstring} or L{NumpyDocstring} objects.
        """
        # log any warnings
        for warn, lineno in docstring_obj.warnings:
            errors.append(ParseError(warn, lineno, is_fatal=False))
        # Get the converted reST string and parse it with docutils
        return processtypes(restructuredtext.parse_docstring)(str(docstring_obj), errors)
