# epydoc -- Utility functions
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""
Miscellaneous utility functions that are used by multiple modules.

@group Text processing: plaintext_to_html
"""
__docformat__ = 'epytext en'

from twisted.web.template import flattenString

######################################################################
## Text Processing
######################################################################

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
