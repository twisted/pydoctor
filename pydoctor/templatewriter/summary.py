"""Classes that generate the summary pages."""

from collections import defaultdict
from typing import (
    TYPE_CHECKING, DefaultDict, Dict, Iterable, List, Mapping, MutableSet,
    Sequence, Tuple, Type, Union, cast
)

from twisted.web.template import Element, Tag, TagLoader, renderer, tags

from pydoctor import epydoc2stan, model
from pydoctor.templatewriter import TemplateLookup
from pydoctor.templatewriter.pages import Page

if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    from typing_extensions import Final


def moduleSummary(module: model.Module, page_url: str) -> Tag:
    r: Tag = tags.li(
        tags.code(epydoc2stan.taglink(module, page_url)), ' - ',
        epydoc2stan.format_summary(module)
        )
    if module.isPrivate:
        r(class_='private')
    if not isinstance(module, model.Package):
        return r
    contents = list(module.submodules())
    if not contents:
        return r

    def fullName(obj: model.Documentable) -> str:
        return obj.fullName()

    ul = tags.ul()

    if len(contents) > 50 and not any(any(s.submodules()) for s in contents):
        # If there are more than 50 modules and no submodule has
        # further submodules we use a more compact presentation.
        li = tags.li(class_='compact-modules')
        for m in sorted(contents, key=fullName):
            span = tags.span()
            span(tags.code(epydoc2stan.taglink(m, m.url, label=m.name)))
            span(', ')
            if m.isPrivate:
                span(class_='private')
            li(span)
        # remove the last trailing comma
        li.children[-1].children.pop() # type: ignore
        ul(li)
    else:
        for m in sorted(contents, key=fullName):
            ul(moduleSummary(m, page_url))
    r(ul)
    return r

def _lckey(x: model.Documentable) -> Tuple[str, str]:
    return (x.fullName().lower(), x.fullName())

class ModuleIndexPage(Page):

    filename = 'moduleIndex.html'

    def __init__(self, system: model.System, template_lookup: TemplateLookup):

        # Override L{Page.loader} because here the page L{filename}
        # does not equal the template filename.
        super().__init__(system=system, template_lookup=template_lookup,
            loader=template_lookup.get_loader('summary.html') )

    def title(self) -> str:
        return "Module Index"

    @renderer
    def stuff(self, request: object, tag: Tag) -> Tag:
        tag.clear()
        tag([moduleSummary(o, self.filename) for o in self.system.rootobjects])
        return tag

    @renderer
    def heading(self, request: object, tag: Tag) -> Tag:
        tag().clear()
        tag("Module Index")
        return tag

def findRootClasses(
        system: model.System
        ) -> Sequence[Tuple[str, Union[model.Class, Sequence[model.Class]]]]:
    roots: Dict[str, Union[model.Class, List[model.Class]]] = {}
    for cls in system.objectsOfType(model.Class):
        if ' ' in cls.name or not cls.isVisible:
            continue
        if cls.bases:
            for name, base in zip(cls.bases, cls.baseobjects):
                if base is None or not base.isVisible:
                    # The base object is in an external library or filtered out (not visible)
                    # Take special care to avoid AttributeError: 'ZopeInterfaceClass' object has no attribute 'append'.
                    if isinstance(roots.get(name), model.Class):
                        roots[name] = [cast(model.Class, roots[name])]
                    cast(List[model.Class], roots.setdefault(name, [])).append(cls)
                elif base.system is not system:
                    # Edge case with multiple systems, is it even possible to run into this code?
                    roots[base.fullName()] = base
        else:
            # This is a common root class. 
            roots[cls.fullName()] = cls
    return sorted(roots.items(), key=lambda x:x[0].lower())

def isPrivate(obj: model.Documentable) -> bool:
    """Is the object itself private or does it live in a private context?"""

    while not obj.isPrivate:
        parent = obj.parent
        if parent is None:
            return False
        obj = parent

    return True

def isClassNodePrivate(cls: model.Class) -> bool:
    """Are a class and all its subclasses are private?"""

    if not isPrivate(cls):
        return False

    for sc in cls.subclasses:
        if not isClassNodePrivate(sc):
            return False

    return True

def subclassesFrom(
        hostsystem: model.System,
        cls: model.Class,
        anchors: MutableSet[str],
        page_url: str
        ) -> Tag:
    r: Tag = tags.li()
    if isClassNodePrivate(cls):
        r(class_='private')
    name = cls.fullName()
    if name not in anchors:
        r(tags.a(name=name))
        anchors.add(name)
    r(tags.code(epydoc2stan.taglink(cls, page_url)), ' - ',
      epydoc2stan.format_summary(cls))
    scs = [sc for sc in cls.subclasses if sc.system is hostsystem and ' ' not in sc.fullName()
           and sc.isVisible]
    if len(scs) > 0:
        ul = tags.ul()
        for sc in sorted(scs, key=_lckey):
            ul(subclassesFrom(hostsystem, sc, anchors, page_url))
        r(ul)
    return r

class ClassIndexPage(Page):

    filename = 'classIndex.html'

    def __init__(self, system: model.System, template_lookup: TemplateLookup):

        # Override L{Page.loader} because here the page L{filename}
        # does not equal the template filename.
        super().__init__(system=system, template_lookup=template_lookup,
            loader=template_lookup.get_loader('summary.html') )

    def title(self) -> str:
        return "Class Hierarchy"

    @renderer
    def stuff(self, request: object, tag: Tag) -> Tag:
        t = tag
        anchors: MutableSet[str] = set()
        for b, o in findRootClasses(self.system):
            if isinstance(o, model.Class):
                t(subclassesFrom(self.system, o, anchors, self.filename))
            else:
                item = tags.li(tags.code(b))
                if all(isClassNodePrivate(sc) for sc in o):
                    # This is an external class used only by private API;
                    # mark the whole node private.
                    item(class_='private')
                if o:
                    ul = tags.ul()
                    for sc in sorted(o, key=_lckey):
                        ul(subclassesFrom(self.system, sc, anchors, self.filename))
                    item(ul)
                t(item)
        return t

    @renderer
    def heading(self, request: object, tag: Tag) -> Tag:
        tag.clear()
        tag("Class Hierarchy")
        return tag


class LetterElement(Element):

    def __init__(self,
            loader: TagLoader,
            initials: Mapping[str, Sequence[model.Documentable]],
            letter: str
            ):
        super().__init__(loader=loader)
        self.initials = initials
        self.my_letter = letter

    @renderer
    def letter(self, request: object, tag: Tag) -> Tag:
        tag(self.my_letter)
        return tag

    @renderer
    def letterlinks(self, request: object, tag: Tag) -> Tag:
        letterlinks: List["Flattenable"] = []
        for initial in sorted(self.initials):
            if initial == self.my_letter:
                letterlinks.append(initial)
            else:
                letterlinks.append(tags.a(href='#'+initial)(initial))
            letterlinks.append(' - ')
        if letterlinks:
            del letterlinks[-1]
        tag(letterlinks)
        return tag

    @renderer
    def names(self, request: object, tag: Tag) -> "Flattenable":
        def link(obj: model.Documentable) -> Tag:
            # The "data-type" attribute helps doc2dash figure out what
            # category (class, method, etc.) an object belongs to.
            attributes = {}
            if obj.kind:
                attributes["data-type"] = epydoc2stan.format_kind(obj.kind)
            return tags.code(
                epydoc2stan.taglink(obj, NameIndexPage.filename), **attributes
                )
        name2obs: DefaultDict[str, List[model.Documentable]] = defaultdict(list)
        for obj in self.initials[self.my_letter]:
            name2obs[obj.name].append(obj)
        r = []
        for name in sorted(name2obs, key=lambda x:(x.lower(), x)):
            item: Tag = tag.clone()(name)
            obs = name2obs[name]
            if all(isPrivate(ob) for ob in obs):
                item(class_='private')
            if len(obs) == 1:
                item(' - ', link(obs[0]))
            else:
                ul = tags.ul()
                for ob in sorted(obs, key=_lckey):
                    subitem = tags.li(link(ob))
                    if isPrivate(ob):
                        subitem(class_='private')
                    ul(subitem)
                item(ul)
            r.append(item)
        return r


class NameIndexPage(Page):

    filename = 'nameIndex.html'

    def __init__(self, system: model.System, template_lookup: TemplateLookup):
        super().__init__(system=system, template_lookup=template_lookup)
        self.initials: Dict[str, List[model.Documentable]] = {}
        for ob in self.system.allobjects.values():
            if ob.isVisible:
                self.initials.setdefault(ob.name[0].upper(), []).append(ob)


    def title(self) -> str:
        return "Index of Names"

    @renderer
    def heading(self, request: object, tag: Tag) -> Tag:
        return tag.clear()("Index of Names")

    @renderer
    def index(self, request: object, tag: Tag) -> "Flattenable":
        r = []
        for i in sorted(self.initials):
            r.append(LetterElement(TagLoader(tag), self.initials, i))
        return r


class IndexPage(Page):

    filename = 'index.html'

    def title(self) -> str:
        return f"API Documentation for {self.system.projectname}"

    @renderer
    def onlyIfOneRoot(self, request: object, tag: Tag) -> "Flattenable":
        if len(self.system.rootobjects) != 1:
            return []
        else:
            root, = self.system.rootobjects
            return tag.clear()(
                "Start at ", tags.code(epydoc2stan.taglink(root, self.filename)),
                ", the root ", epydoc2stan.format_kind(root.kind).lower(), ".")

    @renderer
    def onlyIfMultipleRoots(self, request: object, tag: Tag) -> "Flattenable":
        if len(self.system.rootobjects) == 1:
            return []
        else:
            return tag

    @renderer
    def roots(self, request: object, tag: Tag) -> "Flattenable":
        r = []
        for o in self.system.rootobjects:
            r.append(tag.clone().fillSlots(root=tags.code(
                epydoc2stan.taglink(o, self.filename)
                )))
        return r

    @renderer
    def rootkind(self, request: object, tag: Tag) -> Tag:
        return tag.clear()('/'.join(sorted(
             epydoc2stan.format_kind(o.kind, plural=True).lower()
             for o in self.system.rootobjects
             )))


def hasdocstring(ob: model.Documentable) -> bool:
    for source in ob.docsources():
        if source.docstring is not None:
            return True
    return False

class UndocumentedSummaryPage(Page):

    filename = 'undoccedSummary.html'

    def __init__(self, system: model.System, template_lookup: TemplateLookup):
        # Override L{Page.loader} because here the page L{filename}
        # does not equal the template filename.
        super().__init__(system=system, template_lookup=template_lookup,
            loader=template_lookup.get_loader('summary.html') )

    def title(self) -> str:
        return "Summary of Undocumented Objects"

    @renderer
    def heading(self, request: object, tag: Tag) -> Tag:
        return tag.clear()("Summary of Undocumented Objects")

    @renderer
    def stuff(self, request: object, tag: Tag) -> Tag:
        undoccedpublic = [o for o in self.system.allobjects.values()
                          if o.isVisible and not hasdocstring(o)]
        undoccedpublic.sort(key=lambda o:o.fullName())
        for o in undoccedpublic:
            kind = o.kind
            assert kind is not None  # 'kind is None' makes the object invisible
            tag(tags.li(
                epydoc2stan.format_kind(kind), " - ",
                tags.code(epydoc2stan.taglink(o, self.filename))
                ))
        return tag

summarypages: 'Final[Iterable[Type[Page]]]' = [
    ModuleIndexPage,
    ClassIndexPage,
    IndexPage,
    NameIndexPage,
    UndocumentedSummaryPage,
    ]
