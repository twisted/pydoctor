#
# plaintext.py: plaintext docstring parsing
# Edward Loper
#
# Created [04/10/01 12:00 AM]
#

"""
Parser for plaintext docstrings.  Plaintext docstrings are rendered as
verbatim output, preserving all whitespace.
"""
__docformat__ = 'epytext en'

from typing import List

from twisted.web.template import Tag, tags

from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring, ParseError


def parse_docstring(docstring: str, errors: List[ParseError]) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted as plain text; and
    return a L{ParsedDocstring} representation of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    return ParsedPlaintextDocstring(docstring)

class ParsedPlaintextDocstring(ParsedDocstring):

    def __init__(self, text: str):
        ParsedDocstring.__init__(self, ())
        self._text = text

    @property
    def has_body(self) -> bool:
        return bool(self._text)

    def to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        return tags.p(self._text, class_='pre')  # type: ignore[no-any-return]
