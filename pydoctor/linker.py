"""
This module provides implementations of epydoc's L{DocstringLinker} class.
"""

from collections import defaultdict
import contextlib
from twisted.web.template import Tag, tags
from typing import  (
     ContextManager, Tuple, TYPE_CHECKING, Dict, Iterable, 
     List, Optional, Set, Union, cast
)

from pydoctor.epydoc.markup import DocstringLinker

if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    from typing_extensions import Literal
    
    # This import must be kept in the TYPE_CHECKING block for circular references issues.
    from pydoctor import model

def taglink(o: 'model.Documentable', page_url: str, 
            label: Optional["Flattenable"] = None) -> Tag:
    """
    Create a link to an object that exists in the system.

    @param o: The object to link to
    @param page_url: The URL of the current page, pass empty string to
        aloways generate full urls that includes the filename.
    @param label: The label to use for the link
    """
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())

    if label is None:
        label = o.fullName()

    url = o.url
    if page_url and url.startswith(page_url + '#'):
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

    def __init__(self, obj: 'model.Documentable', strict:bool=False) -> None:
        self.obj = obj
        self.strict=strict
        self._page_object: Optional['model.Documentable'] = self.obj.page_object
    
    @property
    def page_url(self) -> str:
        pageob = self._page_object
        if pageob is not None:
            return pageob.url
        return ''

    @contextlib.contextmanager #type:ignore[arg-type]
    def switch_page_context(self, ob:Optional['model.Documentable']) -> ContextManager[None]: # type:ignore[misc]
        
        old_page_object = self._page_object
        self._page_object = ob if ob is None else ob.page_object
        yield
        self._page_object = old_page_object
    
    def disable_same_page_optimization(self) -> ContextManager[None]:
        return self.switch_page_context(None)

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
            return taglink(target, self.page_url, label)

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
                xref = taglink(resolved, self.page_url, label)
                
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
    
    


class CacheEntry:
    def __init__(self, name:str, 
                 label:'Flattenable', 
                 attributes: Dict[Union[str, bytes], "Flattenable"], 
                 lookup_failed: bool, 
                 warned_linenos: Optional[Set[int]]=None, ) -> None:
        # Core fields of cache entry
        self.name: str = name
        self.label: "Flattenable" = label
        self.attributes: Dict[Union[str, bytes], "Flattenable"] = attributes
        
        # Warning tracking attributes
        self.lookup_failed: bool = lookup_failed
        self.warned_linenos: Set[int] = warned_linenos or set()

        # Not to compute it several times
        if lookup_failed:
            self._stan = Tag('transparent', attributes=self.attributes)(self.label)
        else:
            # Do not create links when there is nothing to link to. 
            self._stan = Tag('a', attributes=self.attributes)(self.label)
        
        self._href = str(self.attributes.get('href',''))
    
    @property
    def href(self) -> str:
        return self._href

    def __repr__(self) -> str:
        return f"<CacheEntry name={self.name!r} label={self.label!r} attributes={self.attributes!r}>"
    
    def get_stan(self) -> Tag:
        return self._stan
    
    @staticmethod
    def _could_be_anchor_link(href:str, page_url:str) -> bool:
        return bool(page_url and href.startswith(page_url+"#"))

    @staticmethod
    def _should_be_full_link(href:str, initial_page_url:str, current_page_url:str) -> bool:
        return bool(href.startswith("#") and initial_page_url != current_page_url)

    def deduct_new_href(self, initial_page_url:str, current_page_url:str) -> Optional[str]:
        
        href = self.href

        # Reason about page object context
        if self._could_be_anchor_link(href, current_page_url):
            # The link could be optimized, use only the anchor
            return href[len(current_page_url):]
        if self._should_be_full_link(href, initial_page_url, current_page_url):
            # The page context has been changed, use a full URL.
            return initial_page_url+href
        
        return None
    
    def matches(self, name:str, label:'Flattenable', 
                initial_page_url:str,
                current_page_url:str) -> bool:
        """
        Whether this cache entry matches the received request.
        """
        if self.name == name \
            and self.label == label:

            href = self.href
            if not href:
                return True
            
            if self._could_be_anchor_link(href, current_page_url) or \
                self._should_be_full_link(href, initial_page_url, current_page_url):
                return False
            else:
                return True
        else:
            return False

class _CachedEpydocLinker(_EpydocLinker):
    """
    This linker implements smart caching functionalities on top of public methods defined in L{_EpydocLinker}.

    The cache is implemented at the L{Tag} (Stan) level, letting us do transformation over cached L{Tag} instances
    and recycle already resolved URLs and adjust them to change formatting as requested by link_xref(). 

    It compares the link label and href, so 
    """
    _CacheType = Dict[str, Dict[str, List['CacheEntry']]]
    # Dict name to dict page object url to list of cached entries


    def __init__(self, obj: 'model.Documentable') -> None:
        super().__init__(obj, strict=True)
        
        self._link_to_cache: '_CachedEpydocLinker._CacheType' = defaultdict(lambda:defaultdict(list))
        self._link_xref_cache: '_CachedEpydocLinker._CacheType' = defaultdict(lambda:defaultdict(list))
    
    def _get_cache(self, cache_kind: 'Literal["link_to", "link_xref"]' = "link_to") -> '_CachedEpydocLinker._CacheType':
        cache_dict = getattr(self, f"_{cache_kind}_cache")
        assert isinstance(cache_dict, dict)
        return cast('_CachedEpydocLinker._CacheType', cache_dict)

    def _new_deducted_entry(self, 
                    cached_entry: 'CacheEntry', 
                    label: "Flattenable", 
                    cache_kind: 'Literal["link_to", "link_xref"]' = "link_to") -> 'CacheEntry':
        """
        Get an entry from the cache.

        @returns: A new deducted cached entry or none if the 
            entry has just the label to change, not the link.
        """
        # Transform the :
        # - omit the filename when linking on the same page.

        new_href = cached_entry.deduct_new_href(self.obj.page_object.url, self.page_url)
        if new_href is None:
            # Only the label changes
            new_attribs = cached_entry.attributes
        else:
            # Copy the new link into a new attributes dict
            new_attribs = cached_entry.attributes.copy()
            new_attribs['href'] = new_href

        return self._store_in_cache(
                        cached_entry.name, 
                        label, 
                        attributes=new_attribs, 
                        cache_kind=cache_kind,
                        lookup_failed=cached_entry.lookup_failed,
                        warned_linenos=cached_entry.warned_linenos # We do not use copy() here by design.
                    )
    
    def _lookup_cached_entry(self, target:str, label: "Flattenable", 
                          cache_kind: 'Literal["link_to", "link_xref"]' = "link_to") -> Optional[Tuple['CacheEntry', bool]]:
        # Lookup an entry in the cache,
        # 
        # if the exact entry could not be found
        # but we could extrapolate the correct link from the link we already had in the cache.
        # Returns None if no coresponding entry has been found in the cache.
        
        # For xrefs, we first look into the link_to cache.
        if cache_kind == "link_xref":
            cached = self._lookup_cached_entry(target, label, cache_kind="link_to")
            if cached is not None: return cached
        
        # Get the cached entries
        cache = self._get_cache(cache_kind)
        values:List[CacheEntry] = []

        for v in cache[target].values():
            values.extend(v)
            
        # Not found
        if not values: 
            return None
        
        # Here we iterate, but we could transform this into a dict access for more speed.
        # But at the same time, usually there are not a lot of different labels applied 
        # to the same link in the same docstring, so the current behaviour is good enough.
        def new_entry(e:CacheEntry) -> CacheEntry:
            return self._new_deducted_entry(e, label, cache_kind)
        
        _initial_page_url = self.obj.page_object.url
        _current_page_url = self.page_url
        _exact_matches = [v for v in values if v.matches(
                                target, label, _initial_page_url, _current_page_url)]
        
        for entry in _exact_matches:
            return entry, False
        else:
            # Automatically deduce what would 
            # be the link with a different label and/or relative or full link.
            # This will add a new entry in the cache.
            _first_match = next(v for v in values if v not in _exact_matches)
            return new_entry(_first_match), True

    
    def _store_in_cache(self, 
                        target: str, 
                        label: "Flattenable", 
                        attributes: Dict[Union[str, bytes], "Flattenable"],
                        cache_kind: 'Literal["link_to", "link_xref"]' = "link_to", 
                        lookup_failed:bool=False, 
                        warned_linenos: Optional[Set[int]]=None) -> 'CacheEntry':

        # Store a new resolved link in the cache.

        cache = self._get_cache(cache_kind)
        values = cache[target][self.page_url]
        entry = CacheEntry(target, label, attributes=attributes, lookup_failed=lookup_failed)
        if warned_linenos:
            entry.warned_linenos = warned_linenos # We do not use copy() here by design.
        values.insert(0, entry)
        return entry

    def _lookup_cached_link_to(self, target: str, label: "Flattenable") -> Optional[Tag]:
        # Lookup a link_to() cached value.
        cached = self._lookup_cached_entry(target, label, cache_kind="link_to")
        if cached:
            return cached[0].get_stan()
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
            self._store_in_cache(target, label, link.attributes, 
                                 cache_kind="link_to", 
                                 lookup_failed=failed)
        return link
    
    def _lookup_cached_link_xref(self, target: str, label: "Flattenable", lineno: int) -> Optional[Tag]:
        # Lookup a link_xref() cached value. 
        # Warns if the link is derived from a link that failed the URL lookup.
        cached = self._lookup_cached_entry(target, label, cache_kind="link_xref")
        if cached:
            entry, new = cached  
            if new:     
                # Warns only if the line number differs from any other values we have already in cache.
                if entry.lookup_failed and lineno not in entry.warned_linenos:
                    self.obj.report(f'Cannot find link target for "{entry.name}"', 'resolve_identifier_xref', lineno_offset=lineno)
                    entry.warned_linenos.add(lineno) # Add lineno such that the warning does not trigger again for this line.
        
            return entry.get_stan()
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
            new_cached = self._store_in_cache(target, label, link.attributes, 
                                              cache_kind="link_xref", 
                                              lookup_failed=failed)
            if failed:
                new_cached.warned_linenos.add(lineno)
        return tags.code(link)
