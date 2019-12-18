# epydoc -- Utility functions
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

"""
Miscellaneous utility functions that are used by multiple modules.
"""
__docformat__ = 'epytext en'

from twisted.web.template import flattenString

######################################################################
## Text Processing
######################################################################

def flatten(stan):
    ret = []
    err = []
    flattenString(None, stan).addCallback(ret.append).addErrback(err.append)
    if err:
        raise err[0].value
    else:
        return ret[0].decode()
