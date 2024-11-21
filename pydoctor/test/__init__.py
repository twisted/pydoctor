"""PyDoctor's test suite."""

from logging import LogRecord
from typing import Iterable, TYPE_CHECKING, Sequence
import sys
import pytest
from pathlib import Path

from pydoctor import epydoc2stan, model
from pydoctor.templatewriter import IWriter, TemplateLookup
from pydoctor.linker import NotFoundLinker

posonlyargs = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")
typecomment = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")
NotFoundLinker = NotFoundLinker

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

    from _pytest.fixtures import FixtureRequest
    from _pytest.monkeypatch import MonkeyPatch
    from _pytest.tmpdir import TempPathFactory
else:
    CapLog = CaptureResult = CapSys = object
    FixtureRequest = MonkeyPatch = TempPathFactory = object


class InMemoryWriter(IWriter):
    """
    Minimal template writer that doesn't touches the filesystem but will
    trigger the rendering of epydoc for the targeted code.
    """

    def __init__(self, build_directory: Path, template_lookup: 'TemplateLookup') -> None:
        pass

    def prepOutputDirectory(self) -> None:
        """
        Does nothing.
        """

    def writeIndividualFiles(self, obs: Iterable[model.Documentable]) -> None:
        """
        Trigger in memory rendering for all objects.
        """
        for ob in obs:
            self._writeDocsFor(ob)

    def writeSummaryPages(self, system: model.System) -> None:
        """
        Rig the system to not created the inter sphinx inventory.
        """
        system.options.makeintersphinx = False
    
    def writeLinks(self, system: model.System) -> None:
        """
        Does nothing.
        """

    def _writeDocsFor(self, ob: model.Documentable) -> None:
        """
        Trigger in memory rendering of the object.
        """
        if not ob.isVisible:
            return

        epydoc2stan.format_docstring(ob)

        for o in ob.contents.values():
            self._writeDocsFor(o)
        