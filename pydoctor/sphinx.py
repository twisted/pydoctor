"""
Support for Sphinx compatibility.
"""
from __future__ import annotations
from collections import defaultdict
import enum

import logging
import os
from pathlib import Path
import shutil
import textwrap
import zlib
from typing import (
    TYPE_CHECKING, Callable, ContextManager, Dict, IO, Iterable, List, Mapping,
    Optional, Set, Tuple
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
    from pydoctor.options import IntersphinxOption

    class CacheT(Protocol):
        def get(self, url: str) -> Optional[bytes]: ...
        def close(self) -> None: ...
else:
    Documentable = object
    CacheT = object

logger = logging.getLogger(__name__)

def parse_domain_reftype(name: str) -> Tuple[Optional[str], str]:
    """
    Given a string like C{class} or C{py:class} or C{rst:directive:option}, 
    returns a tuple: (domain, reftype). 
    The reftype is normalized with L{normalize_reftype}.
    """
    names = name.split(':', maxsplit=1)
    if len(names) == 1: # reftype
        domain, reftype = (None, *names)
    else: # domain:reftype
        domain, reftype = names
    return (domain, normalize_reftype(reftype))

def normalize_reftype(reftype:str) -> str:
    """
    Some reftype can be written in several manners. I.e 'cls' to 'class'. 
    This function transforms them into their canonical version. 

    This is intended to be used for the 'py' domain reftypes. Other kind
    of reftypes are returned as is.
    """
    return {

        'cls': 'class',
        'function': 'func',
        'method': 'meth', 
        'exception': 'exc',
        'attribute': 'attr',
        'attrib': 'attr',
        'constant': 'const',
        'module': 'mod', 
        'object': 'obj',
    
    }.get(reftype, reftype)

@attr.s(auto_attribs=True)
class InventoryObject:
    invname: str
    name: str
    base_url: str
    location: str
    reftype: str
    domain: Optional[str]
    display: str

class SphinxInventory:
    """
    Sphinx inventory handler.
    """

    def __init__(self, logger: Callable[..., None],):
        
        self._links: Dict[str, List[InventoryObject]] = defaultdict(list)
        self._inventories: Set[str] = set()
        self._logger = logger

    def error(self, where: str, message: str) -> None:
        self._logger(where, message, thresh=-1)
    
    def message(self, where: str, message: str) -> None:
        self._logger(where, message, thresh=1)
    
    def _add_inventory(self, invname:str|None, url_or_path: str) -> str|None:
        inventory_name = invname or str(hash(url_or_path))
        if inventory_name in self._inventories:
            # We now trigger warning when the same inventory has been loaded twice.
            if invname:
                self.error('sphinx', 
                        f'Duplicate inventory {invname!r} from {url_or_path}')
            else:
                self.error('sphinx', 
                        f'Duplicate inventory from {url_or_path}')
            return None
        self._inventories.add(inventory_name)
        return inventory_name
    
    def _update(self, data: bytes, 
                base_url:str, 
                inventory_name: str, ) -> None:
        payload = self._getPayload(base_url, data)
        invdata = self._parseInventory(base_url, payload, 
                                       invname=inventory_name)
        # Update links
        for k,v in invdata.items():
            self._links[k].extend(v)

    def update(self, cache: CacheT, intersphinx: IntersphinxOption) -> None:
        """
        Update inventory from an L{IntersphinxOption} tuple that is URL-based.
        """
        invname, url, base_url = intersphinx

        # That's an URL.
        data = cache.get(url)
        if not data:
            self.error('sphinx', f'Failed to get object inventory from url {url}')
            return
        
        inventory_name = self._add_inventory(invname, url)
        if inventory_name:
            self._update(data, base_url, inventory_name)        

    def update_from_file(self, intersphinx: IntersphinxOption) -> None:
        """
        Update inventory from an L{IntersphinxOption} tuple that is File-based.
        """
        invname, path, base_url = intersphinx
        
        # That's a file.
        try:
            data = Path(path).read_bytes()
        except Exception as e:
            self.error('sphinx', 
                    f'Failed to read inventory file {path}: {e}')
            return

        inventory_name = self._add_inventory(invname, path)
        if inventory_name:
            self._update(data, base_url, inventory_name)

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
            payload: str,
            invname: str
            ) -> Dict[str, List[InventoryObject]]:
        """
        Parse clear text payload and return a dict with module to link mapping.
        """

        result = defaultdict(list)
        for line in payload.splitlines():
            try:
                name, typ, prio, location, display = _parseInventoryLine(line)
                domain, reftype = parse_domain_reftype(typ)
            except ValueError as e:
                self.error(
                    'sphinx',
                    f'Failed to parse line {line!r} for {base_url}: {e}',
                    )
                continue
            
            result[name].append(InventoryObject(
                invname=invname, 
                name=name,
                base_url=base_url, 
                location=location,
                reftype=reftype, 
                domain=domain, 
                display=display))
        
        return result

    def getInv(self, target: str, 
               invname:Optional[str]=None, 
               domain:Optional[str]=None, 
               reftype:Optional[str]=None) -> Optional[InventoryObject]:
        """
        Get the inventory object instance matching the criteria.
        """
        
        if target not in self._links:
            return None

        options = self._links[target]
        
        def _filter(inv: InventoryObject) -> bool:
            if invname and inv.invname != invname:
                return False
            if domain and inv.domain != domain:
                return False
            if reftype and inv.reftype != reftype:
                return False
            return True

        # apply filters
        options = list(filter(_filter, options))

        if len(options) == 1:
            return options[0]
        elif not options:
            return None

        # We still have several options under consideration...
        # If the domain is not specified, then the 'py' domain is assumed. 
        # This typically happens for regular `links` that exists in several domains
        # typically like the standard library 'list' (it exists in the terms and in the standard types).
        if domain is None:
            domain = 'py'
            py_options = list(filter(_filter, options))
            if py_options:
                # TODO: We might want to leave a message in the case where several objects
                # are still in consideration. But for now, we just pick the last one because our old version
                # of the inventory (that only dealing with the 'py' domain) would override names as they were parsed.
                return py_options[-1]
        
        # If it hasn't been found in the 'py' domain, then we use the first mathing object because it makes 
        # more sens in the case of the `std` domain of the standard library.
        return options[0]

    def getLink(self, target: str,
                invname:Optional[str]=None, 
                domain:Optional[str]=None, 
                reftype:Optional[str]=None) -> Optional[str]:
        """
        Return link for ``target`` or None if no link is found.
        """
        invobj = self.getInv(target, invname, domain, reftype)
        if not invobj:
            return None
        
        base_url = invobj.base_url
        relative_link = invobj.location

        # For links ending with $, replace it with full name.
        if relative_link.endswith('$'):
            relative_link = relative_link[:-1] + target

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
        objtype: str
        if isinstance(obj, model.Module):
            objtype = 'py:module'
        elif isinstance(obj, model.Class):
            objtype = 'py:class'
        elif isinstance(obj, model.Function):
            if obj.kind is model.DocumentableKind.FUNCTION:
                objtype = 'py:function'
            else:
                objtype = 'py:method'
        elif isinstance(obj, model.Attribute):
            objtype = 'py:attribute'
        else:
            objtype = 'py:obj'
            self.error(
                'sphinx', "Unknown type %r for %s." % (type(obj), full_name,))

        return f'{full_name} {objtype} -1 {url} {display}\n'


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

    def close(self) -> None:
        self._session.close()

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

if __name__ == "__main__":
    import sys
    from pydoctor.options import Options

    opt = Options.from_args(sys.argv[1:])

    cache = prepareCache(clearCache=False, enableCache=True,
                         cachePath=USER_INTERSPHINX_CACHE,
                         maxAge=MAX_AGE_DEFAULT)
    
    inv = SphinxInventory(lambda section, msg, **kw: print(msg))
    
    for i in opt.intersphinx:
        inv.update(cache, i)

    for name, objs in inv._links.items():
        for o in objs:
            print(f'{name} '
                  f'{(o.domain+":") if o.domain else ""}'
                  f'{o.reftype} '
                  f'{o.location} '
                  f'{o.display} ')