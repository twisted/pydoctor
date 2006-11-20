from nevow import page, loaders, tags

from pydoctor import epydoc2stan, model
from pydoctor.nevowhtml.util import fillSlots, taglink, templatefile

def moduleSummary(modorpack):
    r = tags.li[taglink(modorpack), ' - ', epydoc2stan.doc2html(modorpack, summary=True)]
    if isinstance(modorpack, model.Package) and len(modorpack.orderedcontents) > 1:
        ul = tags.ul()
        for m in sorted(modorpack.orderedcontents,
                        key=lambda m:m.fullName()):
            if m.name != '__init__':
                ul[moduleSummary(m)]
        r[ul]
    return r

class ModuleIndexPage(page.Element):
    filename = 'moduleIndex.html'
    docFactory = loaders.xmlfile(templatefile('summary.html'))
    def __init__(self, system):
        self.system = system
    @page.renderer
    def title(self, request, tag):
        return tag.clear()["Module Index"]
    @page.renderer
    def stuff(self, request, tag):
        r = []
        for o in self.system.rootobjects:
            r.append(moduleSummary(o))
        return tag.clear()[r]
    @page.renderer
    def heading(self, request, tag):
        return tag().clear()["Module Index"]

def findRootClasses(system):
    roots = {}
    for cls in system.objectsOfType(model.Class):
        if ' ' in cls.name:
            continue
        if cls.bases:
            for n, b in zip(cls.bases, cls.baseobjects):
                if b is None:
                    roots.setdefault(n, []).append(cls)
                elif b.system is not system:
                    roots[b.fullName()] = b
        else:
            roots[cls.fullName()] = cls
    return sorted(roots.items())

def subclassesFrom(hostsystem, cls, anchors):
    r = tags.li()
    name = cls.fullName()
    if name not in anchors:
        r[tags.a(name=name)]
        anchors.add(name)
    r[taglink(cls), ' - ', epydoc2stan.doc2html(cls, summary=True)]
    scs = [sc for sc in cls.subclasses if sc.system is hostsystem and ' ' not in sc.fullName()]
    if len(scs) > 0:
        ul = tags.ul()
        for sc in sorted(scs, key=lambda sc2:sc2.fullName()):
            ul[subclassesFrom(hostsystem, sc, anchors)]
        r[ul]
    return r

class ClassIndexPage(page.Element):
    filename = 'classIndex.html'
    docFactory = loaders.xmlfile(templatefile('summary.html'))
    def __init__(self, system):
        self.system = system
    @page.renderer
    def title(self, request, tag):
        return tag.clear()["Class Hierarchy"]
    @page.renderer
    def stuff(self, request, tag):
        t = tag
        anchors = set()
        for b, o in findRootClasses(self.system):
            if isinstance(o, model.Class):
                t[subclassesFrom(self.system, o, anchors)]
            else:
                item = tags.li[b]
                if o:
                    ul = tags.ul()
                    for sc in sorted(o, key=lambda sc2:sc2.fullName()):
                        ul[subclassesFrom(self.system, sc, anchors)]
                    item[ul]
                t[item]
        return t
    @page.renderer
    def heading(self, request, tag):
        return tag.clear()["Class Hierarchy"]


class NameIndexPage(page.Element):
    filename = 'nameIndex.html'
    docFactory = loaders.xmlfile(templatefile('nameIndex.html'))
    def __init__(self, system):
        self.system = system

    @page.renderer
    def title(self, request, tag):
        return tag.clear()["Index Of Names"]

    @page.renderer
    def heading(self, request, tag):
        return tag.clear()["Index Of Names"]

    @page.renderer
    def index(self, request, tag):
        letter = tag.patternGenerator('letter')
        singleName = tag.patternGenerator('singleName')
        manyNames = tag.patternGenerator('manyNames')
        initials = {}
        for ob in self.system.orderedallobjects:
            initials.setdefault(ob.name[0].upper(), []).append(ob)
        for initial in sorted(initials):
            letterlinks = []
            for initial2 in sorted(initials):
                if initial == initial2:
                    letterlinks.append(initial2)
                else:
                    letterlinks.append(tags.a(href='#'+initial2)[initial2])
                letterlinks.append(' - ')
            if letterlinks:
                del letterlinks[-1]
            name2obs = {}
            for obj in initials[initial]:
                name2obs.setdefault(obj.name, []).append(obj)
            lettercontents = []
            for name in sorted(name2obs, key=lambda x:x.lower()):
                obs = sorted(name2obs[name], key=lambda x:x.fullName().lower())
                if len(obs) == 1:
                    ob, = obs
                    lettercontents.append(fillSlots(singleName,
                                                    name=ob.name,
                                                    link=taglink(ob)))
                else:
                    lettercontents.append(fillSlots(manyNames,
                                                    name=obs[0].name,
                                                    manyNames=[tags.li[taglink(ob)] for ob in obs]))

            tag[fillSlots(letter,
                          letter=initial,
                          letterlinks=letterlinks,
                          lettercontents=lettercontents)]
        return tag

class IndexPage(page.Element):
    filename = 'index.html'
    docFactory = loaders.xmlfile(templatefile('index.html'))
    def __init__(self, system):
        self.system = system
    @page.renderer
    def project_link(self, request, tag):
        if self.system.options.projecturl:
            return tags.a(href=self.system.options.projecturl)[self.system.options.projectname]
        else:
            return self.system.options.projectname
    @page.renderer
    def project(self, request, tag):
        return self.system.options.projectname
    @page.renderer
    def recentChanges(self, request, tag):
        return ()
    @page.renderer
    def onlyIfOneRoot(self, request, tag):
        if len(self.system.rootobjects) != 1:
            return []
        else:
            root, = self.system.rootobjects
            return tag.clear()[
                "Start at ", taglink(root),
                ", the root ", root.kind.lower(), "."]
    @page.renderer
    def onlyIfMultipleRoots(self, request, tag):
        if len(self.system.rootobjects) == 1:
            return []
        else:
            return tag.clear()

summarypages = [ModuleIndexPage, ClassIndexPage, IndexPage, NameIndexPage]

