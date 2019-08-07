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

from pydoctor.epydoc.markup import ParsedDocstring
from pydoctor.epydoc.util import plaintext_to_html

def parse_docstring(docstring, errors):
    """
    @return: A pair C{(M{d}, M{e})}, where C{M{d}} is a
        C{ParsedDocstring} that encodes the contents of the given
        plaintext docstring; and C{M{e}} is a list of errors that were
        generated while parsing the docstring.
    @rtype: C{L{ParsedPlaintextDocstring}, C{list} of L{ParseError}}
    """
    return ParsedPlaintextDocstring(docstring)

class ParsedPlaintextDocstring(ParsedDocstring):
    def __init__(self, text):
        if text is None: raise ValueError('Bad text value (expected a str)')
        self._text = text

    def split_fields(self, errors=None):
        return self, []

    def to_html(self, docstring_linker, **options):
        plaintext = plaintext_to_html(self.to_plaintext(docstring_linker))
        return '<pre class="literalblock">\n%s\n</pre>\n' % plaintext

    def to_plaintext(self, docstring_linker, **options):
        if 'indent' in options:
            indent = options['indent']
            lines = self._text.split('\n')
            return '\n'.join([' '*indent+l for l in lines])+'\n'
        return self._text+'\n'
