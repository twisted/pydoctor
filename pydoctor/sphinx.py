"""
Support for Sphinx compatibility.
"""

import logging
import os
import shutil
import textwrap
import zlib
from typing import (
    TYPE_CHECKING, Callable, ContextManager, Dict, IO, Iterable, Mapping,
    Optional, Tuple
)

import appdirs
import attr
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import ExpiresAfter

if TYPE_CHECKING:
    from pydoctor.model import Documentable
    from typing_extensions import Protocol

    class CacheT(Protocol):
        def get(self, url: str) -> Optional[bytes]: ...
else:
    Documentable = object
    CacheT = object


logger = logging.getLogger(__name__)


class SphinxInventory:
    """
    Sphinx inventory handler.
    """

    def __init__(
            self,
            logger: Callable[..., None],
            project_name: Optional[str] = None
            ):
        """
        @param project_name: Dummy argument to stay compatible with
                             L{twisted.python._pydoctor}.
        """
        self._links: Dict[str, Tuple[str, str]] = {}
        self._logger = logger

    def error(self, where: str, message: str) -> None:
        self._logger(where, message, thresh=-1)

    def update(self, cache: CacheT, url: str) -> None:
        """
        Update inventory from URL.
        """
        parts = url.rsplit('/', 1)
        if len(parts) != 2:
            self.error(
                'sphinx', 'Failed to get remote base url for %s' % (url,))
            return

        base_url = parts[0]

        data = cache.get(url)

        if not data:
            self.error(
                'sphinx', 'Failed to get object inventory from %s' % (url, ))
            return

        payload = self._getPayload(base_url, data)
        self._links.update(self._parseInventory(base_url, payload))

    def _getPayload(self, base_url: str, data: bytes) -> str:
        """
        Parse inventory and return clear text payload without comments.
        """
        payload = b''
        while True:
            parts = data.split(b'\n', 1)
            if len(parts) != 2:
                payload = data
                break
            if not parts[0].startswith(b'#'):
                payload = data
                break
            data = parts[1]
        try:
            decompressed = zlib.decompress(payload)
        except zlib.error:
            self.error(
                'sphinx',
                'Failed to uncompress inventory from %s' % (base_url,))
            return ''
        try:
            return decompressed.decode('utf-8')
        except UnicodeError:
            self.error(
                'sphinx',
                'Failed to decode inventory from %s' % (base_url,))
            return ''

    def _parseInventory(
            self,
            base_url: str,
            payload: str
            ) -> Dict[str, Tuple[str, str]]:
        """
        Parse clear text payload and return a dict with module to link mapping.
        """
        result = {}
        for line in payload.splitlines():
            try:
                name, typ, prio, location, display = _parseInventoryLine(line)
            except ValueError:
                self.error(
                    'sphinx',
                    'Failed to parse line "%s" for %s' % (line, base_url),
                    )
                continue

            if not typ.startswith('py:'):
                # Non-Python references are ignored.
                continue

            result[name] = (base_url, location)
        return result

    def getLink(self, name: str) -> Optional[str]:
        """
        Return link for `name` or None if no link is found.
        """
        base_url, relative_link = self._links.get(name, (None, None))
        if not relative_link:
            return None

        # For links ending with $, replace it with full name.
        if relative_link.endswith('$'):
            relative_link = relative_link[:-1] + name

        return f'{base_url}/{relative_link}'


def _parseInventoryLine(line: str) -> Tuple[str, str, int, str, str]:
    """
    Parse a single line from a Sphinx inventory.
    @raise ValueError: If the line does not conform to the syntax.
    """
    parts = line.split(' ')

    # The format is a bit of a mess: spaces are used as separators, but
    # there are also columns that can contain spaces.
    # Use the numeric priority column as a reference point, since that is
    # what sphinx.util.inventory.InventoryFile.load_v2() does as well.
    prio_idx = 2
    try:
        while True:
            try:
                prio = int(parts[prio_idx])
                break
            except ValueError:
                prio_idx += 1
    except IndexError:
        raise ValueError("Could not find priority column")

    name = ' '.join(parts[: prio_idx - 1])
    typ = parts[prio_idx - 1]
    location = parts[prio_idx + 1]
    display = ' '.join(parts[prio_idx + 2 :])
    if not display:
        raise ValueError("Display name column cannot be empty")

    return name, typ, prio, location, display


class SphinxInventoryWriter:
    """
    Sphinx inventory handler.
    """

    def __init__(self, logger: Callable[..., None], project_name: str, project_version: str):
        self._project_name = project_name
        self._project_version = project_version
        self._logger = logger

    def info(self, where: str, message: str) -> None:
        self._logger(where, message)

    def error(self, where: str, message: str) -> None:
        self._logger(where, message, thresh=-1)

    def generate(self, subjects: Iterable[Documentable], basepath: str) -> None:
        """
        Generate Sphinx objects inventory version 2 at `basepath`/objects.inv.
        """
        path = os.path.join(basepath, 'objects.inv')
        self.info('sphinx', 'Generating objects inventory at %s' % (path,))

        with self._openFileForWriting(path) as target:
            target.write(self._generateHeader())
            content = self._generateContent(subjects)
            target.write(zlib.compress(content))

    def _openFileForWriting(self, path: str) -> ContextManager[IO[bytes]]:
        """
        Helper for testing.
        """
        return open(path, 'wb')

    def _generateHeader(self) -> bytes:
        """
        Return header for project  with name.
        """
        return f"""# Sphinx inventory version 2
# Project: {self._project_name}
# Version: {self._project_version}
# The rest of this file is compressed with zlib.
""".encode('utf-8')

    def _generateContent(self, subjects: Iterable[Documentable]) -> bytes:
        """
        Write inventory for all `subjects`.
        """
        content = []
        for obj in subjects:
            if not obj.isVisible:
                continue
            content.append(self._generateLine(obj).encode('utf-8'))
            content.append(self._generateContent(obj.contents.values()))

        return b''.join(content)

    def _generateLine(self, obj: Documentable) -> str:
        """
        Return inventory line for object.

        name domain_name:type priority URL display_name

        Domain name is always: py
        Priority is always: -1
        Display name is always: -
        """
        # Avoid circular import.
        from pydoctor import model

        full_name = obj.fullName()
        url = obj.url

        display = '-'
        if isinstance(obj, (model.Package, model.Module)):
            domainname = 'module'
        elif isinstance(obj, model.Class):
            domainname = 'class'
        elif isinstance(obj, model.Function):
            if obj.kind == 'Function':
                domainname = 'function'
            else:
                domainname = 'method'
        elif isinstance(obj, model.Attribute):
            domainname = 'attribute'
        else:
            domainname = 'obj'
            self.error(
                'sphinx', "Unknown type %r for %s." % (type(obj), full_name,))

        return f'{full_name} py:{domainname} -1 {url} {display}\n'


USER_INTERSPHINX_CACHE = appdirs.user_cache_dir("pydoctor")


@attr.s(auto_attribs=True)
class _Unit:
    """
    A unit of time for maximum age parsing.

    @see: L{parseMaxAge}
    """

    name: str
    """The name of the unit."""

    minimum: int
    """The minimum value, inclusive."""

    maximum: int
    """The maximum value, exclusive."""


# timedelta stores seconds and minutes internally as ints.  Limit them
# to a 32 bit value.  Per the documentation, days are limited to
# 999999999, and weeks are converted to days by multiplying 7.
_maxAgeUnits = {
    "s": _Unit("seconds", minimum=1, maximum=2 ** 32 - 1),
    "m": _Unit("minutes", minimum=1, maximum=2 ** 32 - 1),
    "h": _Unit("hours", minimum=1, maximum=2 ** 32 - 1),
    "d": _Unit("days", minimum=1, maximum=999999999 + 1),
    "w": _Unit("weeks", minimum=1, maximum=(999999999 + 1) // 7),
}
_maxAgeUnitNames = ", ".join(
    f"{indicator} ({unit.name})"
    for indicator, unit in _maxAgeUnits.items()
)


MAX_AGE_HELP = textwrap.dedent(
    f"""
    The maximum age of any entry in the cache.  Of the format
    <int><unit> where <unit> is one of {_maxAgeUnitNames}.
    """
)
MAX_AGE_DEFAULT = '1w'


class InvalidMaxAge(Exception):
    """
    Raised when a string cannot be parsed as a maximum age.
    """


def parseMaxAge(maxAge: str) -> Dict[str, int]:
    """
    Parse a string into a maximum age dictionary.

    @param maxAge: A string consisting of an integer number
        followed by a single character unit.
    @return: A dictionary whose keys match L{datetime.timedelta}'s
        arguments.
    @raises InvalidMaxAge: when a string cannot be parsed.
    """
    try:
        amount = int(maxAge[:-1])
    except (ValueError, TypeError):
        raise InvalidMaxAge("Maximum age must be parseable as integer.")

    try:
        unit = _maxAgeUnits[maxAge[-1]]
    except (IndexError, KeyError):
        raise InvalidMaxAge(
            f"Maximum age's units must be one of {_maxAgeUnitNames}")

    if not (unit.minimum <= amount < unit.maximum):
        raise InvalidMaxAge(
            f"Maximum age in {unit.name} must be "
            f"greater than or equal to {unit.minimum} "
            f"and less than {unit.maximum}")

    return {unit.name: amount}


@attr.s(auto_attribs=True)
class IntersphinxCache(CacheT):
    """
    An Intersphinx cache.
    """

    _session: requests.Session
    """A session that may or may not cache requests."""

    _logger: logging.Logger = logger

    @classmethod
    def fromParameters(
            cls,
            sessionFactory: Callable[[], requests.Session],
            cachePath: str,
            maxAgeDictionary: Mapping[str, int]
            ) -> 'IntersphinxCache':
        """
        Construct an instance with the given parameters.

        @param sessionFactory: A zero-argument L{callable} that
            returns a L{requests.Session}.
        @param cachePath: Path of the cache directory.
        @param maxAgeDictionary: A mapping describing the maximum
            age of any cache entry.
        @see: L{parseMaxAge}
        """
        session = CacheControl(sessionFactory(),
                               cache=FileCache(cachePath),
                               heuristic=ExpiresAfter(**maxAgeDictionary))
        return cls(session)

    def get(self, url: str) -> Optional[bytes]:
        """
        Retrieve a URL using the cache.

        @param url: The URL to retrieve.
        @return: The body of the URL, or L{None} on failure.
        """
        try:
            return self._session.get(url).content
        except Exception:
            self._logger.exception(
                "Could not retrieve intersphinx object.inv from %s",
                url
            )
            return None


def prepareCache(
        clearCache: bool,
        enableCache: bool,
        cachePath: str,
        maxAge: str,
        sessionFactory: Callable[[], requests.Session] = requests.Session,
        ) -> IntersphinxCache:
    """
    Prepare an Intersphinx cache.

    @param clearCache: Remove the cache?
    @param enableCache: Enable the cache?
    @param cachePath: Path of the cache directory.
    @param maxAge: The maximum age in seconds of cached Intersphinx
        C{objects.inv} files.
    @param sessionFactory: (optional) A zero-argument L{callable} that
        returns a L{requests.Session}.
    @return: A L{IntersphinxCache} instance.
    """
    if clearCache:
        shutil.rmtree(cachePath)
    if enableCache:
        maxAgeDictionary = parseMaxAge(maxAge)
        return IntersphinxCache.fromParameters(
            sessionFactory,
            cachePath,
            maxAgeDictionary,
        )
    return IntersphinxCache(sessionFactory())
