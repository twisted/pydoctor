"""PyDoctor's test suite."""

from logging import LogRecord
from typing import TYPE_CHECKING, Sequence
import sys
import pytest

from pydoctor import epydoc2stan, model

typecomment = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")


# Because pytest 6.1 does not yet export types for fixtures, we define
# approximations that are good enough for our test cases:

if TYPE_CHECKING:
    from typing_extensions import Protocol

    class CapLog(Protocol):
        records: Sequence[LogRecord]

    class CaptureResult(Protocol):
        out: str
        err: str

    class CapSys(Protocol):
        def readouterr(self) -> CaptureResult: ...
else:
    CapLog = CaptureResult = CapSys = object


class InMemoryWriter:
    """
    Minimal template writer that doesn't touches the filesystem but will
    trigger the rendering of epydoc for the targeted code.
    """

    def __init__(self, filebase: str) -> None:
        self._base = filebase

    def prepOutputDirectory(self) -> None:
        """
        Does nothing.
        """

    def writeIndividualFiles(self, obs: Sequence[model.Documentable], functionpages: bool = False) -> None:
        """
        Trigger in memory rendering for all objects.
        """
        for ob in obs:
            self._writeDocsFor(ob)

    def writeModuleIndex(self, system: model.System) -> None:
        """
        Rig the system to not created the inter sphinx inventory.
        """
        system.options.makeintersphinx = False

    def _writeDocsFor(self, ob: model.Documentable) -> None:
        """
        Trigger in memory rendering of the object.
        """
        if not ob.isVisible:
            return

        epydoc2stan.format_docstring(ob)

        for o in ob.contents.values():
            self._writeDocsFor(o)
