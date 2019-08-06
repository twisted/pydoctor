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

def parse_docstring(docstring, errors, **options):
    """
    @return: A pair C{(M{d}, M{e})}, where C{M{d}} is a
        C{ParsedDocstring} that encodes the contents of the given
        plaintext docstring; and C{M{e}} is a list of errors that were
        generated while parsing the docstring.
    @rtype: C{L{ParsedPlaintextDocstring}, C{list} of L{ParseError}}
    """
    return ParsedPlaintextDocstring(docstring, **options)

class ParsedPlaintextDocstring(ParsedDocstring):
    def __init__(self, text, **options):
        self._verbatim = options.get('verbatim', 1)
        if text is None: raise ValueError, 'Bad text value (expected a str)'
        self._text = text

    def to_html(self, docstring_linker, **options):
        if options.get('verbatim', self._verbatim) == 0:
            return plaintext_to_html(self.to_plaintext(docstring_linker))
        else:
            return ParsedDocstring.to_html(self, docstring_linker, **options)

    def to_plaintext(self, docstring_linker, **options):
        if 'indent' in options:
            indent = options['indent']
            lines = self._text.split('\n')
            return '\n'.join([' '*indent+l for l in lines])+'\n'
        return self._text+'\n'
