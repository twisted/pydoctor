# epydoc -- Utility functions
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""
Miscellaneous utility functions that are used by multiple modules.

@group Text processing: wordwrap, plaintext_to_html
"""
__docformat__ = 'epytext en'

import re

from twisted.web.template import flattenString

######################################################################
## Text Processing
######################################################################

def wordwrap(s, indent=0, right=75):
    """
    Word-wrap the given string.  I.e., add newlines to the string such
    that any lines that are longer than C{right} are broken into
    shorter lines (at the first whitespace sequence that occurs before
    index C{right}).  If the given string contains newlines, they will
    I{not} be removed.  Any lines that begin with whitespace will not
    be wordwrapped.

    @param indent: If specified, then indent each line by this number
        of spaces.
    @type indent: C{int}
    @param right: The right margin for word wrapping.  Lines that are
        longer than C{right} will be broken at the first whitespace
        sequence before the right margin.
    @type right: C{int}
    """
    result = [' ' * indent]
    charindex = indent
    for chunk in re.split(r'( +|\n)', s.expandtabs()):
        if (charindex + len(chunk) > right and charindex > 0) or chunk == '\n':
            result.append('\n' + ' ' * indent)
            charindex = indent
            if chunk[:1] not in ('\n', ' '):
                result.append(chunk)
                charindex += len(chunk)
        else:
            result.append(chunk)
            charindex += len(chunk)
    return ''.join(result).rstrip() + '\n'

def plaintext_to_html(s):
    """
    @return: An HTML string that encodes the given plaintext string.
    In particular, special characters (such as C{'<'} and C{'&'})
    are escaped.
    @rtype: C{string}
    """
    s = s.replace('&', '&amp;').replace('"', '&quot;')
    s = s.replace('<', '&lt;').replace('>', '&gt;')
    return s

def flatten(stan):
    ret = []
    err = []
    flattenString(None, stan).addCallback(ret.append).addErrback(err.append)
    if err:
        raise err[0].value
    else:
        return ret[0].decode()
