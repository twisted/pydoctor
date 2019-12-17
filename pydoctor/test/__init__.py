"""PyDoctor's test suite."""

from __future__ import print_function
import sys
import pytest
from twisted.web.template import flattenString

py3only = pytest.mark.skipif(sys.version_info < (3, 0), reason="requires python 3")
py2only = pytest.mark.skipif(sys.version_info >= (3, 0), reason="requires python 2")

def flatten(stan):
    ret = []
    err = []
    flattenString(None, stan).addCallback(ret.append).addErrback(err.append)
    if err:
        raise err[0].value
    else:
        return ret[0].decode()
