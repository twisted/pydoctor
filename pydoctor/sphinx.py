"""
Support for Sphinx compatibility.
"""
from __future__ import absolute_import, print_function

import logging
import os
import shutil
import textwrap
import zlib

import appdirs
import attr
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from cachecontrol.heuristics import ExpiresAfter

logger = logging.getLogger(__name__)


class SphinxInventory(object):
    """
    Sphinx inventory handler.
    """

    def __init__(self, logger, project_name=None):
        """
        @param project_name: Dummy argument to stay compatible with
                             L{twisted.python._pydoctor}.
        """
        self._links = {}
        self.error = lambda where, message: logger(where, message, thresh=-1)

    def update(self, cache, url):
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

    def _getPayload(self, base_url, data):
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

    def _parseInventory(self, base_url, payload):
        """
        Parse clear text payload and return a dict with module to link mapping.
        """
        result = {}
        for line in payload.splitlines():
            parts = line.split(' ', 4)
            if len(parts) != 5:
                self.error(
                    'sphinx',
                    'Failed to parse line "%s" for %s' % (line, base_url),
                    )
                continue
            result[parts[0]] = (base_url, parts[3])
        return result

    def getLink(self, name):
        """
        Return link for `name` or None if no link is found.
        """
        base_url, relative_link = self._links.get(name, (None, None))
        if not relative_link:
            return None

        # For links ending with $, replace it with full name.
        if relative_link.endswith('$'):
            relative_link = relative_link[:-1] + name

        return '%s/%s' % (base_url, relative_link)


class SphinxInventoryWriter(object):
    """
    Sphinx inventory handler.
    """

    version = (2, 0)

    def __init__(self, logger, project_name):
        self.project_name = project_name
        self.info = logger
        self.error = lambda where, message: logger(where, message, thresh=-1)

    def generate(self, subjects, basepath):
        """
        Generate Sphinx objects inventory version 2 at `basepath`/objects.inv.
        """
        path = os.path.join(basepath, 'objects.inv')
        self.info('sphinx', 'Generating objects inventory at %s' % (path,))

        with self._openFileForWriting(path) as target:
            target.write(self._generateHeader())
            content = self._generateContent(subjects)
            target.write(zlib.compress(content))

    def _openFileForWriting(self, path):
        """
        Helper for testing.
        """
        return open(path, 'wb')

    def _generateHeader(self):
        """
        Return header for project  with name.
        """
        version = [str(part) for part in self.version]
        return ("""# Sphinx inventory version 2
# Project: %s
# Version: %s
# The rest of this file is compressed with zlib.
""" % (self.project_name, '.'.join(version))).encode('utf-8')

    def _generateContent(self, subjects):
        """
        Write inventory for all `subjects`.
        """
        content = []
        for obj in subjects:
            if not obj.isVisible:
                continue
            content.append(self._generateLine(obj).encode('utf-8'))
            content.append(self._generateContent(obj.orderedcontents))

        return b''.join(content)

    def _generateLine(self, obj):
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

        if obj.documentation_location is model.DocLocation.OWN_PAGE:
            url = obj.fullName() + '.html'
        else:
            url = obj.parent.fullName() + '.html#' + obj.name

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

        return '%s py:%s -1 %s %s\n' % (full_name, domainname, url, display)


USER_INTERSPHINX_CACHE = appdirs.user_cache_dir("pydoctor")


@attr.s
class _Unit(object):
    """
    A unit of time for maximum age parsing.

    @ivar name: The name of the unit.
    @type name: L{str}

    @ivar minimum: The minimum value, inclusive.
    @ivar minimum: L{int}

    @ivar maximum: The maximum value, exclusive.
    @ivar maxium: L{int}

    @see: L{parseMaxAge}
    """
    name = attr.ib()
    minimum = attr.ib()
    maximum = attr.ib()


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
    "{} ({})".format(indicator, unit.name)
    for indicator, unit in _maxAgeUnits.items()
)


MAX_AGE_HELP = textwrap.dedent(
    """
    The maximum age of any entry in the cache.  Of the format
    <int><unit> where <unit> is one of {}.
    """.format(_maxAgeUnitNames)
)
MAX_AGE_DEFAULT = '1w'


class InvalidMaxAge(Exception):
    """
    Raised when a string cannot be parsed as a maximum age.
    """


def parseMaxAge(maxAge):
    try:
        amount = int(maxAge[:-1])
    except (ValueError, TypeError):
        raise InvalidMaxAge("Maximum age must be parseable as integer.")

    try:
        unit = _maxAgeUnits[maxAge[-1]]
    except (IndexError, KeyError):
        raise InvalidMaxAge(
            "Maximum age's units must be one of {}".format(_maxAgeUnitNames))

    if not (unit.minimum <= amount < unit.maximum):
        raise InvalidMaxAge(
            "Maximum age in {} must be "
            "greater than or equal to {} "
            "and less than {}".format(unit.name, unit.minimum, unit.maximum))

    return {unit.name: amount}


parseMaxAge.__doc__ = (
    """
    Parse a string into a maximum age dictionary.

    @param maxAge: {}
    @type maxAge: L{str}

    @raises: L{InvalidMaxAge} when a string cannot be parsed.

    @return: A dictionary whose keys match L{datetime.timedelta}'s
        arguments.
    @rtype: L{dict}
    """
)


@attr.s
class IntersphinxCache(object):
    """
    An Intersphinx cache.

    @param session: A session that may or may not cache requests.
    @type session: L{requests.Session}
    """
    _session = attr.ib()
    _logger = attr.ib(default=logger)

    @classmethod
    def fromParameters(cls, sessionFactory, cachePath, maxAgeDictionary):
        """
        Construct an instance with the given parameters.

        @param sessionFactory: A zero-argument L{callable} that
            returns a L{requests.Session}.

        @param cachePath: Path of the cache directory.
        @type cachePath: L{str}

        @param maxAgeDictionary: A dictionary describing the maximum
            age of any cache entry.
        @type maxAgeDictionary: L{dict}

        @see: L{parseMaxAge}
        """
        session = CacheControl(sessionFactory(),
                               cache=FileCache(cachePath),
                               heuristic=ExpiresAfter(**maxAgeDictionary))
        return cls(session)

    def get(self, url):
        """
        Retrieve a URL using the cache.

        @param url: The URL to retrieve.
        @type url: L{str}

        @return: The body of the URL.
        @rtype: L{bytes} on success and L{None} on failure.
        """
        try:
            return self._session.get(url).content
        except Exception:
            self._logger.exception(
                "Could not retrieve intersphinx object.inv from %s",
                url
            )
            return None


@attr.s
class StubCache(object):
    """
    A stub cache.

    @param cache: A L{dict} mapping URLs to content.
    @type cache: L{dict} of L{str} to L{bytes}
    """
    _cache = attr.ib()

    def get(self, url):
        """
        Return stored for the given URL.

        @param url: The URL to retrieve.
        @type url: L{str}

        @return: The "body" of the URL - the value from L{_cache} or
            L{None}.
        @rtype: L{bytes}.
        """
        return self._cache.get(url)


def prepareCache(
        clearCache,
        enableCache,
        cachePath,
        maxAge,
        sessionFactory=requests.Session,
):
    """
    Prepare an Intersphinx cache.

    @param clearCache: Remove the cache?
    @type clearCache: L{bool}

    @param enableCache: Enable the cache?
    @type enableCache: L{bool}

    @param cachePath: Path of the cache directory.
    @type cachePath: L{str}

    @param maxAge: The maximum age in seconds of cached Intersphinx
        C{objects.inv} files.
    @type maxAge: L{float}

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
