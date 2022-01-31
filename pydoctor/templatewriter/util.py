"""Miscellaneous utilities for the HTML writer."""

import warnings
import collections.abc
from typing import Any, Dict, Generic, Iterable, Iterator, Mapping, Optional, MutableMapping, Tuple, TypeVar, Union
from pydoctor import model
from pydoctor.epydoc2stan import format_kind

def css_class(o: model.Documentable) -> str:
    """
    A short, lower case description for use as a CSS class in HTML. 
    Includes the kind and privacy. 
    """
    kind = o.kind
    assert kind is not None # if kind is None, object is invisible
    class_ = format_kind(kind).lower().replace(' ', '')
    if o.privacyClass is model.PrivacyClass.PRIVATE:
        class_ += ' private'
    return class_

def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename: str) -> None:
    """Deprecated: can be removed once Twisted stops patching this."""
    warnings.warn("pydoctor.templatewriter.util.templatefile() "
        "is deprecated and returns None. It will be remove in future versions. "
        "Please use the templating system.")
    return None

_VT = TypeVar('_VT')

# Credits: psf/requests see https://github.com/psf/requests/blob/main/AUTHORS.rst
class CaseInsensitiveDict(MutableMapping[str, _VT], Generic[_VT]):
    """A case-insensitive ``dict``-like object.
    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.
    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::
        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True
    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.
    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """

    def __init__(self, data: Optional[Union[Mapping[str, _VT], Iterable[Tuple[str, _VT]]]] = None, **kwargs: Any) -> None:
        self._store: Dict[str, Tuple[str, _VT]] = collections.OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key: str, value: _VT) -> None:
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> _VT:
        return self._store[key.lower()][1]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def lower_items(self) -> Iterator[Tuple[str, _VT]]:
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, collections.abc.Mapping):
            other = CaseInsensitiveDict(other)
            # Compare insensitively
            return dict(self.lower_items()) == dict(other.lower_items())
        else:
            return NotImplemented

    # Copy is required
    def copy(self) -> 'CaseInsensitiveDict[_VT]':
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self) -> str:
        return str(dict(self.items()))
