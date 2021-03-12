"""Classes that generate the summary pages."""

from typing import Dict, Iterable, List, Sequence, Tuple, Type, Union, cast

from pydoctor import epydoc2stan, model, __version__
from pydoctor.templatewriter import TemplateLookup
from pydoctor.templatewriter.pages import Page
from twisted.web.template import Element, Tag, TagLoader, renderer, tags


def moduleSummary(modorpack, page_url):
    r = tags.li(
        tags.code(epydoc2stan.taglink(modorpack, page_url)), ' - ',
        epydoc2stan.format_summary(modorpack)
        )
    if modorpack.isPrivate:
        r(class_='private')
    if not isinstance(modorpack, model.Package):
        return r
    contents = [m for m in modorpack.contents.values()
                if m.isVisible and m.name != '__init__']
    if not contents:
        return r
    ul = tags.ul()
    for m in sorted(contents, key=lambda m:m.fullName()):
        ul(moduleSummary(m, page_url))
    return r(ul)

def _lckey(x):
    return (x.fullName().lower(), x.fullName())

class ModuleIndexPage(Page):

    filename = 'moduleIndex.html'

    def __init__(self, system: model.System, template_lookup: TemplateLookup):

        # Override L{Page.loader} because here the page L{filename}
        # does not equal the template filename.
        super().__init__(system=system, template_lookup=template_lookup,
            loader=template_lookup.get_template('summary.html').loader )

    def title(self):
        return "Module Index"

    @renderer
    def stuff(self, request, tag):
        r = []
        for o in self.system.rootobjects:
            r.append(moduleSummary(o, self.filename))
        return tag.clear()(r)
    @renderer
    def heading(self, request, tag):
        return tag().clear()("Module Index")

def findRootClasses(
        system: model.System
        ) -> Sequence[Tuple[str, Union[model.Class, Sequence[model.Class]]]]:
    roots: Dict[str, Union[model.Class, List[model.Class]]] = {}
    for cls in system.objectsOfType(model.Class):
        if ' ' in cls.name or not cls.isVisible:
            continue
        if cls.bases:
            for n, b in zip(cls.bases, cls.baseobjects):
                if b is None or not b.isVisible:
                    cast(List[model.Class], roots.setdefault(n, [])).append(cls)
                elif b.system is not system:
                    roots[b.fullName()] = b
        else:
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

def subclassesFrom(hostsystem, cls, anchors, page_url):
    r = tags.li()
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
            loader=template_lookup.get_template('summary.html').loader )

    def title(self):
        return "Class Hierarchy"

    @renderer
    def stuff(self, request, tag):
        t = tag
        anchors = set()
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
    def heading(self, request, tag):
        return tag.clear()("Class Hierarchy")


class LetterElement(Element):

    def __init__(self, loader, initials, letter):
        super().__init__(loader=loader)
        self.initials = initials
        self.my_letter = letter

    @renderer
    def letter(self, request, tag):
        return tag(self.my_letter)

    @renderer
    def letterlinks(self, request, tag):
        letterlinks = []
        for initial in sorted(self.initials):
            if initial == self.my_letter:
                letterlinks.append(initial)
            else:
                letterlinks.append(tags.a(href='#'+initial)(initial))
            letterlinks.append(' - ')
        if letterlinks:
            del letterlinks[-1]
        return tag(letterlinks)

    @renderer
    def names(self, request, tag):
        def link(obj: model.Documentable) -> Tag:
            # The "data-type" attribute helps doc2dash figure out what
            # category (class, method, etc.) an object belongs to.
            tag: Tag = tags.code(
                epydoc2stan.taglink(obj, NameIndexPage.filename),
                **{"data-type": obj.kind}
                )
            return tag
        name2obs = {}
        for obj in self.initials[self.my_letter]:
            name2obs.setdefault(obj.name, []).append(obj)
        r = []
        for name in sorted(name2obs, key=lambda x:(x.lower(), x)):
            item = tag.clone()(name)
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


    def title(self):
        return "Index of Names"

    @renderer
    def heading(self, request, tag):
        return tag.clear()("Index of Names")

    @renderer
    def index(self, request, tag):
        r = []
        for i in sorted(self.initials):
            r.append(LetterElement(TagLoader(tag), self.initials, i))
        return r


class IndexPage(Page):

    filename = 'index.html'

    def title(self):
        return f"API Documentation for {self.system.projectname}"

    @renderer
    def onlyIfOneRoot(self, request, tag):
        if len(self.system.rootobjects) != 1:
            return []
        else:
            root, = self.system.rootobjects
            return tag.clear()(
                "Start at ", tags.code(epydoc2stan.taglink(root, self.filename)),
                ", the root ", root.kind.lower(), ".")

    @renderer
    def onlyIfMultipleRoots(self, request, tag):
        if len(self.system.rootobjects) == 1:
            return []
        else:
            return tag

    @renderer
    def roots(self, request, tag):
        r = []
        for o in self.system.rootobjects:
            r.append(tag.clone().fillSlots(root=tags.code(
                epydoc2stan.taglink(o, self.filename)
                )))
        return r

    @renderer
    def rootkind(self, request, tag):
        rootkinds = {}
        for o in self.system.rootobjects:
            rootkinds[o.kind.lower() + 's']  = 1
        return tag.clear()('/'.join(sorted(rootkinds)))

    @renderer
    def version(self, request, tag):
        return __version__

    @renderer
    def buildtime(self, request, tag):
        return self.system.buildtime.strftime("%Y-%m-%d %H:%M:%S")


def hasdocstring(ob):
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
            loader=template_lookup.get_template('summary.html').loader )

    def title(self):
        return "Summary of Undocumented Objects"

    @renderer
    def heading(self, request, tag):
        return tag.clear()("Summary of Undocumented Objects")

    @renderer
    def stuff(self, request, tag):
        undoccedpublic = [o for o in self.system.allobjects.values()
                          if o.isVisible and not hasdocstring(o)]
        undoccedpublic.sort(key=lambda o:o.fullName())
        for o in undoccedpublic:
            tag(tags.li(o.kind, " - ", tags.code(epydoc2stan.taglink(o, self.filename))))
        return tag

summarypages: Iterable[Type[Page]] = [
    ModuleIndexPage,
    ClassIndexPage,
    IndexPage,
    NameIndexPage,
    UndocumentedSummaryPage,
    ]
