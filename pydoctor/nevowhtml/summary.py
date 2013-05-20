"""Classes that generate the summary pages."""

from twisted.web.template import tags
from twisted.web.template import Element, renderer, TagLoader, XMLFile

from pydoctor import epydoc2stan, model
from pydoctor.nevowhtml.util import taglink, templatefile

def moduleSummary(modorpack):
    r = tags.li(taglink(modorpack), ' - ', epydoc2stan.doc2html(modorpack, summary=True, tags=tags)[0])
    if not isinstance(modorpack, model.Package):
        return r
    contents = [m for m in modorpack.orderedcontents
                if m.isVisible and m.name != '__init__']
    if not contents:
        return r
    ul = tags.ul()
    for m in sorted(contents, key=lambda m:m.fullName()):
        ul(moduleSummary(m))
    return r(ul)

def _lckey(x):
    return (x.fullName().lower(), x.fullName())


class ModuleIndexPage(Element):
    filename = 'moduleIndex.html'
    loader = XMLFile(templatefile('summary.html'))
    def __init__(self, system):
        self.system = system
    @renderer
    def title(self, request, tag):
        return tag.clear()("Module Index")
    @renderer
    def stuff(self, request, tag):
        r = []
        for o in self.system.rootobjects:
            r.append(moduleSummary(o))
        return tag.clear()(r)
    @renderer
    def heading(self, request, tag):
        return tag().clear()("Module Index")

def findRootClasses(system):
    roots = {}
    for cls in system.objectsOfType(model.Class):
        if ' ' in cls.name or not cls.isVisible:
            continue
        if cls.bases:
            for n, b in zip(cls.bases, cls.baseobjects):
                if b is None or not b.isVisible:
                    roots.setdefault(n, []).append(cls)
                elif b.system is not system:
                    roots[b.fullName()] = b
        else:
            roots[cls.fullName()] = cls
    return sorted(roots.items(), key=lambda x:x[0].lower())

def subclassesFrom(hostsystem, cls, anchors):
    r = tags.li()
    name = cls.fullName()
    if name not in anchors:
        r(tags.a(name=name))
        anchors.add(name)
    r(taglink(cls), ' - ', epydoc2stan.doc2html(cls, summary=True, tags=tags)[0])
    scs = [sc for sc in cls.subclasses if sc.system is hostsystem and ' ' not in sc.fullName()
           and sc.isVisible]
    if len(scs) > 0:
        ul = tags.ul()
        for sc in sorted(scs, key=_lckey):
            ul(subclassesFrom(hostsystem, sc, anchors))
        r(ul)
    return r

class ClassIndexPage(Element):
    filename = 'classIndex.html'
    loader = XMLFile(templatefile('summary.html'))

    def __init__(self, system):
        self.system = system

    @renderer
    def title(self, request, tag):
        return tag.clear()("Class Hierarchy")

    @renderer
    def stuff(self, request, tag):
        t = tag
        anchors = set()
        for b, o in findRootClasses(self.system):
            if isinstance(o, model.Class):
                t(subclassesFrom(self.system, o, anchors))
            else:
                item = tags.li(b)
                if o:
                    ul = tags.ul()
                    for sc in sorted(o, key=_lckey):
                        ul(subclassesFrom(self.system, sc, anchors))
                    item(ul)
                t(item)
        return t

    @renderer
    def heading(self, request, tag):
        return tag.clear()("Class Hierarchy")


class LetterElement(Element):
    def __init__(self, loader, initials, letter):
        Element.__init__(self, loader)
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
        name2obs = {}
        for obj in self.initials[self.my_letter]:
            name2obs.setdefault(obj.name, []).append(obj)
        r = []
        for name in sorted(name2obs, key=lambda x:(x.lower(), x)):
            obs = name2obs[name]
            if len(obs) == 1:
                r.append(tag.clone()(name, ' - ', taglink(obs[0])))
            else:
                ul = tags.ul()
                for ob in sorted(obs, key=_lckey):
                    ul(tags.li(taglink(ob)))
                r.append(tag.clone()(name, ul))
        return r


class NameIndexPage(Element):
    filename = 'nameIndex.html'
    loader = XMLFile(templatefile('nameIndex.html'))

    def __init__(self, system):
        self.system = system
        self.initials = {}
        for ob in self.system.orderedallobjects:
            if ob.isVisible:
                self.initials.setdefault(ob.name[0].upper(), []).append(ob)

    @renderer
    def title(self, request, tag):
        return tag.clear()("Index Of Names")

    @renderer
    def heading(self, request, tag):
        return tag.clear()("Index Of Names")

    @renderer
    def index(self, request, tag):
        r = []
        for i in sorted(self.initials):
            r.append(LetterElement(TagLoader(tag), self.initials, i))
        return r


class IndexPage(Element):
    filename = 'index.html'
    loader = XMLFile(templatefile('index.html'))

    def __init__(self, system):
        self.system = system

    @renderer
    def project_link(self, request, tag):
        if self.system.options.projecturl:
            return tags.a(href=self.system.options.projecturl)(
                self.system.options.projectname)
        elif self.system.options.projectname:
            return self.system.options.projectname
        else:
            return self.system.guessedprojectname

    @renderer
    def project(self, request, tag):
        if self.system.options.projectname:
            return self.system.options.projectname
        else:
            return self.system.guessedprojectname

    @renderer
    def recentChanges(self, request, tag):
        return ()

    @renderer
    def problemObjects(self, request, tag):
        return ()

    @renderer
    def onlyIfOneRoot(self, request, tag):
        if len(self.system.rootobjects) != 1:
            return []
        else:
            root, = self.system.rootobjects
            return tag.clear()(
                "Start at ", taglink(root),
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
            r.append(tag.clone().fillSlots(root=taglink(o)))
        return r

    @renderer
    def rootkind(self, request, tag):
        rootkinds = {}
        for o in self.system.rootobjects:
            rootkinds[o.kind.lower() + 's']  = 1
        return tag.clear()('/'.join(sorted(rootkinds)))

    @renderer
    def buildtime(self, request, tag):
        return self.system.buildtime.strftime("%Y-%m-%d %H:%M:%S")


def hasdocstring(ob):
    for source in ob.docsources():
        if source.docstring is not None:
            return True
    return False

class UndocumentedSummaryPage(Element):
    filename = 'undoccedSummary.html'
    loader = XMLFile(templatefile('summary.html'))
    def __init__(self, system):
        self.system = system

    @renderer
    def title(self, request, tag):
        return tag.clear()["Summary of Undocumented Objects"]

    @renderer
    def heading(self, request, tag):
        return tag.clear()["Summary of Undocumented Objects"]

    @renderer
    def stuff(self, request, tag):
        undoccedpublic = [o for o in self.system.orderedallobjects
                          if o.isVisible and not hasdocstring(o)]
        undoccedpublic.sort(key=lambda o:o.fullName())
        for o in undoccedpublic:
            tag[tags.li[o.kind, " - ", taglink(o)]]
        return tag

summarypages = [
    ModuleIndexPage,
    ClassIndexPage,
    IndexPage,
    NameIndexPage,
    UndocumentedSummaryPage,
    ]

