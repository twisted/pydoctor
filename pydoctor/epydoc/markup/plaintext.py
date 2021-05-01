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

from typing import List, Callable, Optional

from docutils import nodes, utils
from twisted.web.template import Tag, tags

from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring, ParseError
from pydoctor.model import Documentable

def parse_docstring(docstring: str, errors: List[ParseError], processtypes: bool = False) -> ParsedDocstring:
    """
    Parse the given docstring, which is formatted as plain text; and
    return a L{ParsedDocstring} representation of its contents.

    @param docstring: The docstring to parse
    @param errors: A list where any errors generated during parsing
        will be stored.
    """
    return ParsedPlaintextDocstring(docstring)

def get_parser(obj: Optional[Documentable]) -> Callable[[str,List[ParseError], bool], ParsedDocstring]:
    """
    Just return the L{parse_docstring} function. 
    """
    return parse_docstring

class ParsedPlaintextDocstring(ParsedDocstring):

    def __init__(self, text: str):
        ParsedDocstring.__init__(self, ())
        self._text = text
         # Caching:
        self._document: Optional[nodes.document] = None

    @property
    def has_body(self) -> bool:
        return bool(self._text)

    def to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        return tags.p(self._text, class_='pre')  # type: ignore[no-any-return]
    
    def to_node(self) -> nodes.document:
        if self._document is not None:
            return self._document
        else:
            self._document = utils.new_document('plaintext')
            self._document.children.append(nodes.literal_block(rawsource=self._text, text=self._text))
            return self._document
