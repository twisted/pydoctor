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

from twisted.web.template import tags

from pydoctor.epydoc.markup import ParsedDocstring

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
    def __init__(self, text):
        if text is None: raise ValueError('Bad text value (expected a str)')
        self._text = text

    def split_fields(self, errors=None):
        return self, []

    def to_stan(self, docstring_linker):
        return tags.pre(class_='literalblock')('\n', self._text, '\n')
