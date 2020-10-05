"""PyDoctor's test suite."""

from logging import LogRecord
from typing import NamedTuple, Sequence
import sys
import pytest

typecomment = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")


# Because pytest 6.1 does not yet export types for fixtures, we define
# approximations that are good enough for our test cases:

class CapLog:
    records: Sequence[LogRecord]

class CaptureResult(NamedTuple):
    out: str
    err: str

class CapSys:
    def readouterr(self) -> CaptureResult: ...
