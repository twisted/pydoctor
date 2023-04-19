"""
This module provides implementations of epydoc's L{DocstringLinker} class.
"""

import contextlib
from twisted.web.template import Tag, tags
from typing import  (
     ContextManager, TYPE_CHECKING, Iterable, 
     Optional, Union
)

from pydoctor.epydoc.markup import DocstringLinker

if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    
    # This import must be kept in the TYPE_CHECKING block for circular references issues.
    from pydoctor import model

def taglink(o: 'model.Documentable', page_url: str, 
            label: Optional["Flattenable"] = None) -> Tag:
    """
    Create a link to an object that exists in the system.

    @param o: The object to link to
    @param page_url: The URL of the current page, pass empty string to
        always generate full urls that includes the filename.
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

    def __init__(self, obj: 'model.Documentable') -> None:
        self.reporting_obj:Optional['model.Documentable'] = obj
        """
        Object used for reporting link not found errors. Changed when the linker L{switch_context}.
        """
        
        self._init_obj = obj
        self._page_object: Optional['model.Documentable'] = obj.page_object
    
    @property
    def obj(self) -> 'model.Documentable':
        """
        Object used for resolving the target name, it's NOT changed when the linker L{switch_context}.
        """
        return self._init_obj
    
    @property
    def page_url(self) -> str:
        """
        URL of the page used to compute the relative links from. 
        Can be an empty string to always generate full urls. 
        """
        pageob = self._page_object
        if pageob is not None:
            return pageob.url
        return ''

    @contextlib.contextmanager #type:ignore[arg-type]
    def switch_context(self, ob:Optional['model.Documentable']) -> ContextManager[None]: # type:ignore[misc]
        
        old_page_object = self._page_object
        old_reporting_object = self.reporting_obj

        self._page_object = None if ob is None else ob.page_object
        self.reporting_obj = ob
        
        yield
        
        self._page_object = old_page_object
        self.reporting_obj = old_reporting_object

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
        elif len(potential_targets) > 1 and self.reporting_obj:
            self.reporting_obj.report(
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
        fullID = self.obj.expandName(identifier)

        target = self.obj.system.objForFullName(fullID)
        if target is not None:
            return taglink(target, self.page_url, label)

        url = self.look_for_intersphinx(fullID)
        if url is not None:
            return self._create_intersphinx_link(label, url=url)

        link = tags.transparent(label)
        return link

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
        xref: "Flattenable"
        try:
            resolved = self._resolve_identifier_xref(target, lineno)
        except LookupError:
            xref = label
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
        if self.reporting_obj:
            self.reporting_obj.report(message, 'resolve_identifier_xref', lineno)
        raise LookupError(identifier)
    
