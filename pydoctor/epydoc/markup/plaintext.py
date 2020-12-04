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

from twisted.web.template import Tag, tags

from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring

def parse_docstring(docstring, errors):
    """
    Parse the given docstring, which is formatted as plain text; and
    return a C{ParsedDocstring} representation of its contents.
    @param docstring: The docstring to parse
    @type docstring: C{string}
    @param errors: A list where any errors generated during parsing
        will be stored.
    @type errors: C{list} of L{ParseError}
    @rtype: L{ParsedDocstring}
    """
    return ParsedPlaintextDocstring(docstring)

class ParsedPlaintextDocstring(ParsedDocstring):

    def __init__(self, text: str):
        ParsedDocstring.__init__(self, ())
        self._text = text

    def to_stan(self, docstring_linker: DocstringLinker) -> Tag:
        return tags.p(self._text, class_='pre')  # type: ignore[no-any-return]
