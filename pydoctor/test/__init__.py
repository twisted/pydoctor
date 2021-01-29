"""PyDoctor's test suite."""

from logging import LogRecord
from typing import TYPE_CHECKING, Optional, Sequence
import sys
import pytest

from twisted.web.template import Tag, tags

from pydoctor import epydoc2stan, model
from pydoctor.epydoc.markup import DocstringLinker


posonlyargs = pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python 3.8")
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

    from _pytest.fixtures import FixtureRequest
    from _pytest.monkeypatch import MonkeyPatch
    from _pytest.tmpdir import TempPathFactory
else:
    CapLog = CaptureResult = CapSys = object
    FixtureRequest = MonkeyPatch = TempPathFactory = object


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

    def writeIndividualFiles(self, obs: Sequence[model.Documentable]) -> None:
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


class NotFoundLinker(DocstringLinker):
    """A DocstringLinker implementation that cannot find any links."""

    def link_to(self, target: str, label: str) -> Tag:
        return tags.transparent(label)  # type: ignore[no-any-return]

    def link_xref(self, target: str, label: str, lineno: int) -> Tag:
        return tags.code(label)  # type: ignore[no-any-return]

    def resolve_identifier(self, identifier: str) -> Optional[str]:
        return None
