from pydoctor import model, twisted, epydoc2stan

from nevow import loaders, tags, page, flat, inevow
from zope.interface import implements

import os, shutil, inspect, sys, urllib

def fillSlots(tag, **kw):
    for k, v in kw.iteritems():
        tag = tag.fillSlots(k, v)
    return tag

def link(o):
    return o.system.urlprefix+urllib.quote(o.fullName()+'.html')

def srclink(o):
    system = o.system
    if not system.sourcebase:
        return None
    m = o
    while not isinstance(m, (model.Module, model.Package)):
        m = m.parent
        if m is None:
            return None
    sourceHref = '%s/%s'%(system.sourcebase, m.fullName().replace('.', '/'),)
    if isinstance(m, model.Module):
        sourceHref += '.py'
    if isinstance(o, model.Module):
        sourceHref += '#L1'
    elif hasattr(o, 'linenumber'):
        sourceHref += '#L'+str(o.linenumber)
    return sourceHref

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

def getBetterThanArgspec(argspec):
    """Ok, maybe argspec's format isn't the best after all: This takes an
    argspec and returns (regularArguments, [(kwarg, kwval), (kwarg, kwval)])."""
    args = argspec[0]
    defaults = argspec[-1]
    if not defaults:
        return (args, [])
    backargs = args[:]
    backargs.reverse()
    defaults = list(defaults)
    defaults.reverse()
    kws = zip(backargs, defaults)
    kws.reverse()
    allargs = args[:-len(kws)] + kws
    return (args[:-len(kws)], kws)

def _strtup(tup):
    # Ugh
    if not isinstance(tup, (tuple, list)):
        return str(tup)
    return '(' + ', '.join(map(_strtup, tup)) + ')'

def signature(argspec):
    """Return a nicely-formatted source-like signature, formatted from an
    argspec.
    """
    regargs, kwargs = getBetterThanArgspec(argspec)
    varargname, varkwname = argspec[1:3]
    things = []
    for regarg in regargs:
        if isinstance(regarg, list):
            things.append(_strtup(regarg))
        else:
            things.append(regarg)
    if varargname:
        things.append('*%s' % varargname)
    things += ['%s=%s' % (t[0], t[1]) for t in kwargs]
    if varkwname:
        things.append('**%s' % varkwname)
    return ', '.join(things)

class NevowWriter:
    def __init__(self, filebase):
        self.base = filebase
        self.written_pages = 0

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(sibpath(__file__, '../templates/apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))
        if self.system.options.htmlusesorttable:
            shutil.copyfile(sibpath(__file__, '../templates/sorttable.js'),
                            os.path.join(self.base, 'sorttable.js'))

    def writeIndividualFiles(self, obs, functionpages=False):
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)

    def writeModuleIndex(self, system):
        for pclass in summarypages:
            page = pclass(system)
            f = open(os.path.join(self.base, pclass.filename), 'w')
            f.write(flat.flatten(page))
            f.close()

    def writeDocsFor(self, ob, functionpages):
        isfunc = ob.document_in_parent_page
        if (isfunc and functionpages) or not isfunc:
            f = open(os.path.join(self.base, link(ob)), 'w')
            self.writeDocsForOne(ob, f)
            f.close()
        for o in ob.orderedcontents:
            self.writeDocsFor(o, functionpages)

    def writeDocsForOne(self, ob, fobj):
        # brrrrrrrr!
        for c in ob.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in globals():
                pclass = globals()[n]
                break
        else:
            pclass = CommonPage
        page = pclass(ob)
        self.written_pages += 1
        print '\rwritten', self.written_pages, 'pages',
        sys.stdout.flush()
        fobj.write(flat.flatten(page))

def mediumName(obj):
    fn = obj.fullName()
    if '.' not in fn:
        return fn
    path, name = fn.rsplit('.', 1)
    def process(part):
        return obj.system.abbrevmapping.get(part, part[0])
    return '.'.join([process(p) for p in path.split('.')]) + '.' + name

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
    docFactory = loaders.xmlfile(sibpath(__file__, '../templates/summary.html'))
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
    docFactory = loaders.xmlfile(sibpath(__file__, '../templates/summary.html'))
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
    docFactory = loaders.xmlfile(sibpath(__file__, '../templates/nameIndex.html'))
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
    docFactory = loaders.xmlfile(sibpath(__file__, '../templates/index.html'))
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


class CommonPage(object):
    implements(inevow.IRenderer)
    docFactory = loaders.xmlfile(sibpath(__file__, '../templates/common.html'))
    def __init__(self, ob):
        self.ob = ob

    def title(self):
        return self.ob.fullName()

    def heading(self):
        kind = self.ob.kind
        return tags.h1(class_=kind.lower())[kind + " " + mediumName(self.ob)]

    def part(self):
        tag = tags.invisible()
        if self.ob.parent:
            parent = self.ob.parent
            if isinstance(parent, model.Module) and parent.name == '__init__':
                parent = parent.parent
            parts = []
            while parent.parent:
                parts.append(tags.a(href=link(parent))[parent.name])
                parts.append('.')
                parent = parent.parent
            parts.append(tags.a(href=link(parent))[parent.name])
            parts.reverse()
            return tag['Part of ', parts]
        else:
            return tag

    def project(self):
        if self.ob.system.options.projecturl:
            return tags.a(href=self.ob.system.options.projecturl)[self.ob.system.options.projectname]
        else:
            return self.ob.system.options.projectname

    def source(self, tag):
        sourceHref = srclink(self.ob)
        if not sourceHref:
            return ()
        return tag(href=sourceHref)

    def inhierarchy(self, tag):
        return ()

    def extras(self):
        return tags.invisible()

    def docstring(self):
        return epydoc2stan.doc2html(self.ob)

    def children(self):
        return self.ob.orderedcontents

    def packageInitTable(self):
        return ()

    def baseTables(self, tag):
        return ()

    def mainTable(self):
        children = self.children()
        if children:
            return TableFragment(self.ob.system, self.has_lineno_col(), children)
        else:
            return ()

    def has_lineno_col(self):
        if not self.ob.system.options.htmlusesorttable:
            return False
        return isinstance(self.ob, (model.Class, model.Module))

    def ifusesorttable(self, tag):
        if self.ob.system.options.htmlusesorttable:
            return tag
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.orderedcontents
                if o.document_in_parent_page]

    def childlist(self, childlist):
        tag = tags.invisible()
        functionHeader = childlist.patternGenerator('functionHeader')
        attributeHeader = childlist.patternGenerator('attributeHeader')
        sourceLink = childlist.patternGenerator('sourceLink')
        child = childlist.patternGenerator('child')
        for data in self.methods():
            if isinstance(data, model.Function):
                sourceHref = srclink(data)
                if not sourceHref:
                    functionSourceLink = ()
                else:
                    functionSourceLink = fillSlots(sourceLink,
                                                   sourceHref=sourceHref)
                header = fillSlots(functionHeader,
                                   functionName=[data.name, '(', signature(data.argspec), '):'],
                                   functionSourceLink=functionSourceLink)
            else:
                header = fillSlots(attributeHeader,
                                   attribute=data.name)
            tag[fillSlots(child,
                          header=header,
                          functionAnchor=data.fullName(),
                          shortFunctionAnchor=data.name,
                          functionBody=self.functionBody(data))]
        return tag

    def functionBody(self, data):
        return epydoc2stan.doc2html(data)

    def rend(self, ctx, data):
        tag = tags.invisible[self.docFactory.load()]
        return fillSlots(tag,
                         title=self.title(),
                         ifusesorttable=self.ifusesorttable(tag.onePattern('ifusesorttable')),
                         heading=self.heading(),
                         part=self.part(),
                         source=self.source(tag.onePattern('source')),
                         inhierarchy=self.inhierarchy(tag.onePattern('inhierarchy')),
                         extras=self.extras(),
                         docstring=self.docstring(),
                         mainTable=self.mainTable(),
                         packageInitTable=self.packageInitTable(),
                         baseTables=self.baseTables(tag.patternGenerator('baseTable')),
                         childlist=self.childlist(tag.onePattern('childlist')),
                         project=self.project(),
                         )


class PackagePage(CommonPage):
    def children(self):
        return sorted([o for o in self.ob.orderedcontents
                       if o.name != '__init__'],
                      key=lambda o2:o2.fullName())

    def packageInitTable(self):
        children = self.ob.contents['__init__'].orderedcontents
        if children:
            return [tags.p["From the __init__.py module:"],
                    TableFragment(self.ob.system, self.ob.system.options.htmlusesorttable,
                                  children)]
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.contents['__init__'].orderedcontents
                if o.document_in_parent_page]

class TableFragment(object):
    implements(inevow.IRenderer)
    docFactory = loaders.xmlfile(sibpath(__file__, '../templates/table.html'))
    last_id = 0
    classprefix = ''
    def __init__(self, system, has_lineno_col, children):
        self.system = system
        self.has_lineno_col = has_lineno_col
        self.children = children
        TableFragment.last_id += 1
        self.id = TableFragment.last_id

    def table(self, request, tag):
        tag.fillSlots('id', 'id'+str(self.id))
        if self.system.options.htmlusesorttable:
            header = tag.onePattern('header')
            if self.has_lineno_col:
                header = fillSlots(header,
                                   linenohead=header.onePattern('linenohead'))
            else:
                header = fillSlots(header,
                                   linenohead=())
            tag[header]
        item = tag.patternGenerator('item')
        linenorow = tag.patternGenerator('linenorow')
        for child in self.children:
            if child.document_in_parent_page:
                link_ = tags.a(href=link(child.parent) + '#' + child.name)[child.name]
            else:
                link_ = tags.a(href=link(child))[child.name]
            if self.has_lineno_col:
                if hasattr(child, 'linenumber'):
                    sourceHref = srclink(child)
                    if not sourceHref:
                        line = child.linenumber
                    else:
                        line = tags.a(href=sourceHref)[child.linenumber]
                else:
                    line = ()
                linenorow_ = fillSlots(linenorow,
                                       lineno=line)
            else:
                linenorow_ = ()
            tag[fillSlots(item,
                          class_=self.classprefix + child.kind.lower(),
                          kind=child.kind,
                          name=link_,
                          linenorow=linenorow_,
                          summaryDoc=epydoc2stan.doc2html(child, summary=True))]
        return tag

    def rend(self, ctx, data):
        tag = tags.invisible[self.docFactory.load()]
        return tag

class BaseTableFragment(TableFragment):
    classprefix = 'base'

class ModulePage(CommonPage):
    pass

def taglink(o, label=None):
    if label is None:
        label = o.fullName()
    if o.document_in_parent_page:
        p = o.parent
        if isinstance(p, model.Module) and p.name == '__init__':
            p = p.parent
        linktext = link(p) + '#' + urllib.quote(o.name)
    else:
        linktext = link(o)
    return tags.a(href=linktext)[label]

class ClassPage(CommonPage):
    def extras(self):
        r = super(ClassPage, self).extras()
        if self.ob.subclasses:
            sc = self.ob.subclasses[0]
            p = tags.p()
            p["Known subclasses: ", taglink(sc)]
            for sc in self.ob.subclasses[1:]:
                p[', ', taglink(sc)]
            r[p]
        return r

    def heading(self):
        tag = super(ClassPage, self).heading()
        zipped = zip(self.ob.rawbases, self.ob.baseobjects)
        if zipped:
            tag['(']
            for i, (n, o) in enumerate(zipped):
                if o is None:
                    tag[n]
                else:
                    tag[tags.a(href=link(o))[n]]
                if i != len(zipped)-1:
                    tag[', ']
            tag[')']
        tag[':']
        return tag

    def inhierarchy(self, tag):
        return tag(href="classIndex.html#"+self.ob.fullName())

    def nested_bases(self, b):
        r = [(b,)]
        for b2 in b.baseobjects:
            if b2 is None:
                continue
            for n in self.nested_bases(b2):
                r.append(n + (b,))
        return r

    def unmasked_attrs(self, baselist):
        maybe_masking = set()
        for b in baselist[1:]:
            maybe_masking.update(set([o.name for o in b.orderedcontents]))
        return set([o.name for o in baselist[0].orderedcontents]) - maybe_masking

    def bases(self):
        r = []
        for baselist in self.nested_bases(self.ob)[1:]:
            if self.unmasked_attrs(baselist):
                r.append(baselist)
        return r

    def baseTables(self, item):
        tag = tags.invisible()
        for b in self.bases():
            tag[fillSlots(item,
                          baseName=self.baseName(b),
                          baseTable=self.baseTable(b))]
        return tag

    def baseName(self, data):
        tag = tags.invisible()
        source_base = data[0]
        tag[tags.a(href=link(source_base))[source_base.name]]
        bases_to_mention = data[1:-1]
        if bases_to_mention:
            tail = []
            for b in reversed(bases_to_mention):
                tail.append(tags.a(href=link(b))[b.name])
                tail.append(', ')
            del tail[-1]
            tag[' (via ', tail, ')']
        return tag

    def baseTable(self, data):
        return BaseTableFragment(self.ob.system, self.has_lineno_col(),
                                 [o for o in data[0].orderedcontents
                                  if o.name in self.unmasked_attrs(data)])

class TwistedClassPage(ClassPage):
    def extras(self):
        r = super(TwistedClassPage, self).extras()
        system = self.ob.system
        def tl(s):
            if s in system.allobjects:
                return taglink(system.allobjects[s])
            else:
                return s
        if self.ob.isinterface:
            namelist = self.ob.implementedby_directly
            label = 'Known implementations: '
        else:
            namelist = self.ob.implements_directly
            label = 'Implements interfaces: '
        if namelist:
            tag = tags.p()[label, tl(namelist[0])]
            for impl in namelist[1:]:
                tag[', ', tl(impl)]
            r[tag]
        return r

    def interfaceMeth(self, methname):
        system = self.ob.system
        for interface in self.ob.implements_directly + self.ob.implements_indirectly:
            if interface in system.allobjects:
                io = system.allobjects[interface]
                if methname in io.contents:
                    return io.contents[methname]
        return None

    def functionBody(self, data):
        imeth = self.interfaceMeth(data.name)
        tag = tags.invisible()
        if imeth:
            tag[tags.div(class_="interfaceinfo")
                ['from ', tags.a(href=link(imeth.parent) + '#' + imeth.name)
                 [imeth.parent.fullName()]]]
        for b in self.ob.allbases():
            if data.name not in b.contents:
                continue
            overridden = b.contents[data.name]
            tag[tags.div(class_="interfaceinfo")
                ['overrides ',
                 tags.a(href=link(overridden.parent) + '#' + overridden.name)
                 [overridden.fullName()]]]
            break
        ocs = list(overriding_subclasses(self.ob, data.name))
        if ocs:
            def one(sc):
                return tags.a(
                    href=link(sc) + '#' + sc.contents[data.name].name
                    )[sc.fullName()]
            t = tags.div(class_="interfaceinfo")['overridden in ']
            t[one(ocs[0])]
            for sc in ocs[1:]:
                t[', ', one(sc)]
            tag[t]
        tag[epydoc2stan.doc2html(data)]
        return tag

def overriding_subclasses(c, name, firstcall=True):
    if not firstcall and name in c.contents:
        yield c
    else:
        for sc in c.subclasses:
            for sc2 in overriding_subclasses(sc, name, False):
                yield sc2

class FunctionPage(CommonPage):
    def heading(self):
        tag = super(FunctionPage, self).heading()
        return tag['(', signature(self.ob.argspec), '):']
