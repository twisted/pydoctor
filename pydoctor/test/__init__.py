"""PyDoctor's test suite."""

from __future__ import print_function
import sys
import pytest

py3only = pytest.mark.skipif(sys.version_info < (3, 0), reason="requires python 3")
py2only = pytest.mark.skipif(sys.version_info >= (3, 0), reason="requires python 2")
