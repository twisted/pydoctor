"""Miscellaneous utilities for the HTML writer."""

import warnings
from typing import (Any, Callable, Dict, Generic, Iterable, Iterator, List, Mapping, 
                    Optional, MutableMapping, Tuple, TypeVar, Union, Sequence, TYPE_CHECKING)
from pydoctor import epydoc2stan
import collections.abc
from pydoctor import model

if TYPE_CHECKING:
    from typing import Literal

from twisted.web.template import Tag

class DocGetter:
    """L{epydoc2stan} bridge."""
    def get(self, ob: model.Documentable, summary: bool = False) -> Tag:
        if summary:
            return epydoc2stan.format_summary(ob)
        else:
            return epydoc2stan.format_docstring(ob)
    def get_type(self, ob: model.Documentable) -> Optional[Tag]:
        return epydoc2stan.type2stan(ob)
    def get_toc(self, ob: model.Documentable) -> Optional[Tag]:
        return epydoc2stan.format_toc(ob)

def srclink(o: model.Documentable) -> Optional[str]:
    """
    Get object source code URL, i.e. hosted on github. 
    """
    return o.sourceHref

def css_class(o: model.Documentable) -> str:
    """
    A short, lower case description for use as a CSS class in HTML. 
    Includes the kind and privacy. 
    """
    kind = o.kind
    assert kind is not None # if kind is None, object is invisible
    class_ = epydoc2stan.format_kind(kind).lower().replace(' ', '')
    if o.privacyClass is model.PrivacyClass.PRIVATE:
        class_ += ' private'
    return class_    

def overriding_subclasses(
        classobj: model.Class,
        name: str,
        firstcall: bool = True
        ) -> Iterator[model.Class]:
    """
    Helper function to retreive the subclasses that override the given name from the parent class object. 
    """
    if not firstcall and name in classobj.contents:
        yield classobj
    else:
        for subclass in classobj.subclasses:
            if subclass.isVisible:
                yield from overriding_subclasses(subclass, name, firstcall=False)

def nested_bases(classobj: model.Class) -> Iterator[Tuple[model.Class, ...]]:
    """
    Helper function to retreive the complete list of base classes chains (represented by tuples) for a given Class. 
    A chain of classes is used to compute the member inheritence from the first element to the last element of the chain.  
    
    The first yielded chain only contains the Class itself. 

    Then for each of the super-classes:
        - the next yielded chain contains the super class and the class itself, 
        - the the next yielded chain contains the super-super class, the super class and the class itself, etc...
    """
    _mro = classobj.mro()
    for i, _ in enumerate(_mro):
        yield tuple(reversed(_mro[:(i+1)]))


def unmasked_attrs(baselist: Sequence[model.Class]) -> Sequence[model.Documentable]:
    """
    Helper function to reteive the list of inherited children given a base classes chain (As yielded by L{nested_bases}). 
    The returned members are inherited from the Class listed first in the chain to the Class listed last: they are not overriden in between. 
    """
    maybe_masking = {
        o.name
        for b in baselist[1:]
        for o in b.contents.values()
        }
    return [o for o in baselist[0].contents.values()
            if o.isVisible and o.name not in maybe_masking]

def alphabetical_order_func(o: model.Documentable) -> Tuple[Any, ...]:
    """
    Sort by privacy, kind and fullname.
    Callable to use as the value of standard library's L{sorted} function C{key} argument.
    """
    return (-o.privacyClass.value, -_map_kind(o.kind).value if o.kind else 0, o.fullName().lower())

def source_order_func(o: model.Documentable) -> Tuple[Any, ...]:
    """
    Sort by privacy, kind and linenumber.
    Callable to use as the value of standard library's L{sorted} function C{key} argument.
    """
    return (-o.privacyClass.value, -_map_kind(o.kind).value if o.kind else 0, o.linenumber)

def _map_kind(kind: model.DocumentableKind) -> model.DocumentableKind:
    if kind == model.DocumentableKind.PACKAGE:
        # packages and modules should be listed together
        return model.DocumentableKind.MODULE
    return kind

def objects_order(order: 'Literal["alphabetical", "source"]') -> Callable[[model.Documentable], Tuple[Any, ...]]: 
    """
    Function to craft a callable to use as the value of standard library's L{sorted} function C{key} argument
    such that the objects are sorted by: Privacy, Kind first, then by Name or Linenumber depending on
    C{order} argument.

    Example::

        children = sorted((o for o in ob.contents.values() if o.isVisible),
                      key=objects_order("alphabetical"))
    """

    if order == "alphabetical":
        return alphabetical_order_func
    elif order == "source":
        return source_order_func
    else:
        assert False

def get_objects_order(ob: model.Documentable) -> Callable[[model.Documentable], Tuple[Any, ...]]:
    """
    Help function to get the right orderring function from the type of object passed.
    Users can customize class and module members order independently.
    """
    order_func = objects_order(ob.system.options.cls_member_order) \
            if isinstance(ob, model.Class) else \
            objects_order(ob.system.options.mod_member_order)
    return order_func

def class_members(cls: model.Class) -> List[Tuple[Tuple[model.Class, ...], Sequence[model.Documentable]]]:
    """
    Returns the members as well as the inherited members of a class.

    @returns: Tuples of tuple: C{inherited_via:Tuple[model.Class, ...], attributes:Sequence[model.Documentable]}.
    """
    baselists = []
    for baselist in nested_bases(cls):
        attrs = unmasked_attrs(baselist)
        if attrs:
            baselists.append((baselist, attrs))
    return baselists

def inherited_members(cls: model.Class) -> List[model.Documentable]:
    """
    Returns only the inherited members of a class, as a plain list.
    """
    
    children : List[model.Documentable] = []
    for inherited_via,attrs in class_members(cls):
        if len(inherited_via)>1:
            children.extend(attrs)
    return children

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
