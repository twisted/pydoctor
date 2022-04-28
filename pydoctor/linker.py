"""
This module provides implementations of epydoc's L{DocstringLinker} class.
"""

from collections import defaultdict
import attr
from twisted.web.template import Tag, tags
from typing import (
    TYPE_CHECKING, Dict,Iterable, List, Optional, Set, Union, cast
)

from pydoctor.epydoc.markup import DocstringLinker

if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    from typing_extensions import Literal
    
    # This import must be kept in the TYPE_CHECKING block for circular references issues.
    from pydoctor import model

def taglink(o: 'model.Documentable', page_url: str, 
            label: Optional["Flattenable"] = None, 
            same_page_optimization:bool=True) -> Tag:
    """
    Create a link to an object that exists in the system.

    @param o: The object to link to
    @param page_url: The URL of the current page
    @param label: The label to use for the link
    @param same_page_optimization: Whether to create a link with the anchor only when 
        page_url matches the object's URL.
    """
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())

    if label is None:
        label = o.fullName()

    url = o.url
    if url.startswith(page_url + '#') and same_page_optimization is True:
        # When linking to an item on the same page, omit the path.
        # Besides shortening the HTML, this also avoids the page being reloaded
        # if the query string is non-empty.
        url = url[len(page_url):]

    ret: Tag = tags.a(label, href=url, class_='internal-link')
    if label != o.fullName():
        ret(title=o.fullName())
    return ret


class _EpydocLinker(DocstringLinker):
    """
    This linker implements the xref lookup logic.
    """
    
    class LookupFailed(LookupError):
        """
        Encapsulate a link tag that is not actually a link because we count not resolve the name. 

        Used only if L{_EpydocLinker.strict} is True.
        """
        def __init__(self, *args: object, link: Tag) -> None:
            super().__init__(*args)
            self.link: Tag = link

    def __init__(self, obj: 'model.Documentable', same_page_optimization:bool, strict:bool=False):
        self.obj = obj
        self.same_page_optimization=same_page_optimization
        self.strict=strict

    @staticmethod
    def _create_intersphinx_link(label:"Flattenable", url:str) -> Tag:
        """
        Create a link with the special 'intersphinx-link' CSS class.
        """
        return tags.a(label, href=url, class_='intersphinx-link')

    def look_for_name(self,
            name: str,
            candidates: Iterable['model.Documentable'],
            lineno: int
            ) -> Optional['model.Documentable']:
        part0 = name.split('.')[0]
        potential_targets = []
        for src in candidates:
            if part0 not in src.contents:
                continue
            target = src.resolveName(name)
            if target is not None and target not in potential_targets:
                potential_targets.append(target)
        if len(potential_targets) == 1:
            return potential_targets[0]
        elif len(potential_targets) > 1:
            self.obj.report(
                "ambiguous ref to %s, could be %s" % (
                    name,
                    ', '.join(ob.fullName() for ob in potential_targets)),
                'resolve_identifier_xref', lineno)
        return None

    def look_for_intersphinx(self, name: str) -> Optional[str]:
        """
        Return link for `name` based on intersphinx inventory.

        Return None if link is not found.
        """
        return self.obj.system.intersphinx.getLink(name)

    def link_to(self, identifier: str, label: "Flattenable") -> Tag:
        # :Raises _EpydocLinker.LookupFailed: If the identifier cannot be resolved and self.strict is True.
        # Can return a Tag('a') or Tag('transparent') if not found
        fullID = self.obj.expandName(identifier)

        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return taglink(target, self.obj.page_object.url, label, 
                           same_page_optimization=self.same_page_optimization)

        url = self.look_for_intersphinx(fullID)
        if url is not None:
            return self._create_intersphinx_link(label, url=url)

        link = tags.transparent(label)
        if self.strict:
            raise self.LookupFailed(identifier, link=link)
        return link

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
        # :Raises _EpydocLinker.LookupFailed: If the identifier cannot be resolved and self.strict is True.
        # Otherwise returns a Tag('code'). 
        # If not foud the code tag will simply contain the label as Flattenable, like:
        # Tag('code', children=['label as Flattenable'])
        # If the link is found it gives something like:
        # Tag('code', children=[Tag('a', href='...', children=['label as Flattenable'])])
        xref: "Flattenable"
        try:
            resolved = self._resolve_identifier_xref(target, lineno)
        except LookupError as e:
            xref = label
            if self.strict:
                raise self.LookupFailed(str(e), link=tags.code(xref)) from e
        else:
            if isinstance(resolved, str):
                xref = self._create_intersphinx_link(label, url=resolved)
            else:
                xref = taglink(resolved, self.obj.page_object.url, label, 
                           same_page_optimization=self.same_page_optimization)
                
        return tags.code(xref)

    def resolve_identifier(self, identifier: str) -> Optional[str]:
        fullID = self.obj.expandName(identifier)

        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return target.url

        return self.look_for_intersphinx(fullID)

    def _resolve_identifier_xref(self,
            identifier: str,
            lineno: int
            ) -> Union[str, 'model.Documentable']:
        """
        Resolve a crossreference link to a Python identifier.
        This will resolve the identifier to any reasonable target,
        even if it has to look in places where Python itself would not.

        @param identifier: The name of the Python identifier that
            should be linked to.
        @param lineno: The line number within the docstring at which the
            crossreference is located.
        @return: The referenced object within our system, or the URL of
            an external target (found via Intersphinx).
        @raise LookupError: If C{identifier} could not be resolved.
        """

        # There is a lot of DWIM here. Look for a global match first,
        # to reduce the chance of a false positive.

        # Check if 'identifier' is the fullName of an object.
        target = self.obj.system.objForFullName(identifier)
        if target is not None:
            return target

        # Check if the fullID exists in an intersphinx inventory.
        fullID = self.obj.expandName(identifier)
        target_url = self.look_for_intersphinx(fullID)
        if not target_url:
            # FIXME: https://github.com/twisted/pydoctor/issues/125
            # expandName is unreliable so in the case fullID fails, we
            # try our luck with 'identifier'.
            target_url = self.look_for_intersphinx(identifier)
        if target_url:
            return target_url

        # Since there was no global match, go look for the name in the
        # context where it was used.

        # Check if 'identifier' refers to an object by Python name resolution
        # in our context. Walk up the object tree and see if 'identifier' refers
        # to an object by Python name resolution in each context.
        src: Optional['model.Documentable'] = self.obj
        while src is not None:
            target = src.resolveName(identifier)
            if target is not None:
                return target
            src = src.parent

        # Walk up the object tree again and see if 'identifier' refers to an
        # object in an "uncle" object.  (So if p.m1 has a class C, the
        # docstring for p.m2 can say L{C} to refer to the class in m1).
        # If at any level 'identifier' refers to more than one object, complain.
        src = self.obj
        while src is not None:
            target = self.look_for_name(identifier, src.contents.values(), lineno)
            if target is not None:
                return target
            src = src.parent

        # Examine every module and package in the system and see if 'identifier'
        # names an object in each one.  Again, if more than one object is
        # found, complain.
        target = self.look_for_name(
            # System.objectsOfType now supports passing the type as string.
            identifier, self.obj.system.objectsOfType('pydoctor.model.Module'), lineno)
        if target is not None:
            return target

        message = f'Cannot find link target for "{fullID}"'
        if identifier != fullID:
            message = f'{message}, resolved from "{identifier}"'
        root_idx = fullID.find('.')
        if root_idx != -1 and fullID[:root_idx] not in self.obj.system.root_names:
            message += ' (you can link to external docs with --intersphinx)'
        self.obj.report(message, 'resolve_identifier_xref', lineno)
        raise LookupError(identifier)


class _CachedEpydocLinker(_EpydocLinker):
    """
    This linker implements smart caching functionalities on top of public methods defined in L{_EpydocLinker}.

    The cache is implemented at the L{Tag} (Stan) level, letting us do transformation over cached L{Tag} instances
    and recycle already resolved URLs and adjust them to change formatting as requested by link_xref(). 
    """
    
    @attr.s(auto_attribs=True)
    class CacheEntry:
        name: str
        label: "Flattenable"
        link: Tag
        lookup_failed: bool
        warned_linenos: Set[int] = attr.ib(factory=set)

    class NewDerivedEntry(Exception):
        def __init__(self, *args: object, entry:'_CachedEpydocLinker.CacheEntry') -> None:
            super().__init__(*args)
            self.entry=entry

    _CacheType = Dict[str, Dict[bool, List['_CachedEpydocLinker.CacheEntry']]]
    _defaultCache: _CacheType = defaultdict(lambda:{True:[], False:[]})

    def __init__(self, obj: 'model.Documentable', same_page_optimization:bool=True) -> None:
        super().__init__(obj, same_page_optimization, strict=True)
        
        self._link_to_cache: '_CachedEpydocLinker._CacheType' = self._defaultCache.copy()
        self._link_xref_cache: '_CachedEpydocLinker._CacheType' = self._defaultCache.copy()
    
    def _get_cache(self, cache_kind: 'Literal["link_to", "link_xref"]' = "link_to") -> '_CachedEpydocLinker._CacheType':
        cache_dict = getattr(self, f"_{cache_kind}_cache")
        assert isinstance(cache_dict, dict)
        return cast('_CachedEpydocLinker._CacheType', cache_dict)

    def _new_derived_entry(self, 
                             cached_entry: '_CachedEpydocLinker.CacheEntry', 
                             label: Optional["Flattenable"], 
                             cache_kind: 'Literal["link_to", "link_xref"]' = "link_to") -> '_CachedEpydocLinker.CacheEntry':

        # Transform the URL to omit the filename when self.same_page_optimization is True and
        # add it when self.same_page_optimization is False.
        link = self._adjust_link(cached_entry.link, 
                                        # here we clone the link because we need to change the label anyway
                                        self.same_page_optimization) or (cached_entry.link.clone() if label else cached_entry.link)

        # Change the label if needed.
        if label:
            link.children = [label]

        return self._store_in_cache(
                        cached_entry.name, 
                        label if label else link.children[0], 
                        link=link, 
                        cache_kind=cache_kind,
                        lookup_failed=cached_entry.lookup_failed,
                        warned_linenos=cached_entry.warned_linenos # We do not use copy() here by design.
                    )
    
    def _adjust_link(self, link: Tag, use_same_page_optimization:bool) -> Optional[Tag]:
        # Returns a new link or None if the current link is correct.
        if use_same_page_optimization is False:
            if link.attributes.get('href', '').startswith("#"): # type:ignore
                link = link.clone()
                link.attributes['href'] = self.obj.page_object.url + link.attributes['href'] # type:ignore
                assert not link.attributes['href'].startswith("#") # type:ignore
                return link
        else:
            if link.attributes.get('href', '').startswith(self.obj.page_object.url+"#"): # type:ignore
                link = link.clone()
                link.attributes['href'] = link.attributes['href'][len(self.obj.page_object.url):] # type:ignore
                assert link.attributes['href'].startswith("#") # type:ignore
                return link
        return None

    def _lookup_cached_entry(self, target:str, label: "Flattenable", 
                          cache_kind: 'Literal["link_to", "link_xref"]' = "link_to") -> Optional['_CachedEpydocLinker.CacheEntry']:
        # Lookup an entry in the cache, raise NewDerivedEntry if the exact entry could not be found
        # but we could extrapolate the correct link from the link we already had in the cache.
        # Returns None if no coresponding entry has been found in the cache.
        
        # For xrefs, we first look into the link_to cache.
        if cache_kind == "link_xref":
            cached = self._lookup_cached_entry(target, label, cache_kind="link_to")
            if cached is not None: return cached
        
        # Get the cached entries
        cache = self._get_cache(cache_kind)
        not_same_value_for_same_page_optimization = False
        values = cache[target][self.same_page_optimization]
        
        # Fallback to the entries that have not the same value for same_page_optimization
        # This is ok because we have support for these URL transformation, see _adjust_link. 
        if not values: 
            values = cache[target][not self.same_page_optimization]
            not_same_value_for_same_page_optimization = True
        
        # Not found
        if not values: 
            return None

        # Here we iterate, but we could transform this into a dict access for more speed.
        # But at the same time, usually there are not a lot of different labels applied 
        # to the same link in the same docstring, so the current behaviour is good enough.
        for entry in values:
            if entry.label==label: 
                if not_same_value_for_same_page_optimization:
                    new_entry = self._new_derived_entry(entry, None, cache_kind)
                    raise self.NewDerivedEntry('new cache entry', entry=new_entry)
                return entry
        else: 
            # Automatically infer what would be the link 
            # with a different label
            entry = values[0]
            new_entry = self._new_derived_entry(entry, label, cache_kind)
            raise self.NewDerivedEntry('new cache entry', entry=new_entry)               
    
    def _store_in_cache(self, target: str, 
                        label: "Flattenable", 
                        link: Tag,  
                        cache_kind: 'Literal["link_to", "link_xref"]' = "link_to", 
                        lookup_failed:bool=False, 
                        warned_linenos: Optional[Set[int]]=None) -> '_CachedEpydocLinker.CacheEntry':
        # Store a new resolved link in the cache.

        cache = self._get_cache(cache_kind)
        values = cache[target][self.same_page_optimization]
        entry = self.CacheEntry(target, label, link=link, lookup_failed=lookup_failed)
        if warned_linenos:
            entry.warned_linenos = warned_linenos # We do not use copy() here by design.
        values.insert(0, entry)
        return entry

    def _lookup_cached_link_to(self, target: str, label: "Flattenable") -> Optional[Tag]:
        # Lookup a link_to() cached value.
        try:
            cached = self._lookup_cached_entry(target, label, cache_kind="link_to")
        except self.NewDerivedEntry as e:
            cached = e.entry
        if cached:
            return cached.link
        return None

    def link_to(self, target: str, label: "Flattenable") -> Tag:
        link = self._lookup_cached_link_to(target, label)
        if link is None: 
            failed=False 
            try:
                link = super().link_to(target, label)
            except self.LookupFailed as e:
                link = e.link
                failed=True
            self._store_in_cache(target, label, link, 
                                 cache_kind="link_to", 
                                 lookup_failed=failed)
        return link
    
    def _lookup_cached_link_xref(self, target: str, label: "Flattenable", lineno: int) -> Optional[Tag]:
        # Lookup a link_xref() cached value. 
        # Warns if the link is derived from a link that failed the URL lookup.
        try:
            cached = self._lookup_cached_entry(target, label, cache_kind="link_xref")
        except self.NewDerivedEntry as e:            
            cached = e.entry
            # Warns onlt if the line number differs from any other values we have already in cache.
            if cached.lookup_failed and lineno not in cached.warned_linenos:
                self.obj.report(f'Cannot find link target for "{cached.name}"', 'resolve_identifier_xref', lineno_offset=lineno)
                cached.warned_linenos.add(lineno) # Add lineno such that the warning does not trigger again for this line.
        
        if cached:
            return cached.link
        return None

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
        link: Optional["Flattenable"] = self._lookup_cached_link_xref(target, label, lineno)
        if link is None:
            failed=False 
            try:
                link = super().link_xref(target, label, lineno).children[0]
            except self.LookupFailed as e:
                link = e.link.children[0]
                failed=True
            if not isinstance(link, Tag): 
                link = tags.transparent(link)
            new_cached = self._store_in_cache(target, label, link, 
                                              cache_kind="link_xref", 
                                              lookup_failed=failed)
            if failed:
                new_cached.warned_linenos.add(lineno)
        return tags.code(link)
