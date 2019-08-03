# epydoc -- Utility functions
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""
Miscellaneous utility functions that are used by multiple modules.

@group Python source types: py_src_filename
@group Text processing: wordwrap, decode_with_backslashreplace,
    plaintext_to_html
"""
__docformat__ = 'epytext en'

import os.path, re

######################################################################
## Python Source Types
######################################################################

PY_SRC_EXTENSIONS = ['.py', '.pyw']

def py_src_filename(filename):
    basefile, extension = os.path.splitext(filename)
    if extension in PY_SRC_EXTENSIONS:
        return filename
    else:
        for ext in PY_SRC_EXTENSIONS:
            if os.path.isfile('%s%s' % (basefile, ext)):
                return '%s%s' % (basefile, ext)
        else:
            raise ValueError('Could not find a corresponding '
                             'Python source file for %r.' % filename)

######################################################################
## Text Processing
######################################################################

def decode_with_backslashreplace(s):
    r"""
    Convert the given 8-bit string into unicode, treating any
    character c such that ord(c)<128 as an ascii character, and
    converting any c such that ord(c)>128 into a backslashed escape
    sequence.

        >>> decode_with_backslashreplace('abc\xff\xe8')
        u'abc\\xff\\xe8'
    """
    # s.encode('string-escape') is not appropriate here, since it
    # also adds backslashes to some ascii chars (eg \ and ').
    assert isinstance(s, str)
    return (s
            .decode('latin1')
            .encode('ascii', 'backslashreplace')
            .decode('ascii'))

def wordwrap(str, indent=0, right=75, startindex=0, splitchars=''):
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
    @param startindex: If specified, then assume that the first line
        is already preceeded by C{startindex} characters.
    @type startindex: C{int}
    @param splitchars: A list of non-whitespace characters which can
        be used to split a line.  (E.g., use '/\\' to allow path names
        to be split over multiple lines.)
    @rtype: C{str}
    """
    if splitchars:
        chunks = re.split(r'( +|\n|[^ \n%s]*[%s])' %
                          (re.escape(splitchars), re.escape(splitchars)),
                          str.expandtabs())
    else:
        chunks = re.split(r'( +|\n)', str.expandtabs())
    result = [' '*(indent-startindex)]
    charindex = max(indent, startindex)
    for chunknum, chunk in enumerate(chunks):
        if (charindex+len(chunk) > right and charindex > 0) or chunk == '\n':
            result.append('\n' + ' '*indent)
            charindex = indent
            if chunk[:1] not in ('\n', ' '):
                result.append(chunk)
                charindex += len(chunk)
        else:
            result.append(chunk)
            charindex += len(chunk)
    return ''.join(result).rstrip()+'\n'

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
