from pydoctor import model, twisted, epydoc2stan

from nevow import rend, loaders, tags

import os, shutil, inspect, sys, urllib

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
        shutil.copyfile(sibpath(__file__, 'templates/apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))
        if self.system.options.htmlusesorttable:
            shutil.copyfile(sibpath(__file__, 'templates/sorttable.js'),
                            os.path.join(self.base, 'sorttable.js'))

    def writeIndividualFiles(self, obs, functionpages=False):
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)

    def writeModuleIndex(self, system):
        for pclass in summarypages:
            page = pclass(system)
            f = open(os.path.join(self.base, pclass.filename), 'w')
            f.write(page.renderSynchronously())
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
        fobj.write(page.renderSynchronously())

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

class ModuleIndexPage(rend.Page):
    filename = 'moduleIndex.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/summary.html'))
    def __init__(self, system):
        self.system = system
    def render_title(self, context, data):
        return context.tag.clear()["Module Index"]
    def render_stuff(self, context, data):
        r = []
        for o in self.system.rootobjects:
            r.append(moduleSummary(o))
        return context.tag.clear()[r]
    def render_heading(self, context, data):
        return context.tag().clear()["Module Index"]

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

class ClassIndexPage(rend.Page):
    filename = 'classIndex.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/summary.html'))
    def __init__(self, system):
        self.system = system
    def render_title(self, context, data):
        return context.tag.clear()["Class Hierarchy"]
    def render_stuff(self, context, data):
        t = context.tag
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
    def render_heading(self, context, data):
        return context.tag.clear()["Class Hierarchy"]


class NameIndexPage(rend.Page):
    filename = 'nameIndex.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/nameIndex.html'))
    def __init__(self, system):
        self.system = system
        used_initials = {}
        for ob in self.system.orderedallobjects:
            used_initials[ob.name[0].upper()] = True
        self.used_initials = sorted(used_initials)

    def render_title(self, context, data):
        return context.tag.clear()["Index Of Names"]
    def render_heading(self, context, data):
        return context.tag.clear()["Index Of Names"]
    def data_letters(self, context, data):
        # this is confusing
        # we return a list of lists of lists
        # if r is the return value, r[i][j] is a list of things with the same .name
        # all the things in the lists contained in r[i] share the same initial.
        initials = {}
        for ob in self.system.orderedallobjects:
            initials.setdefault(ob.name[0].upper(), {}).setdefault(ob.name, []).append(ob)
        r = []
        for k in sorted(initials):
            r.append(sorted(
                sorted(initials[k].values(), key=lambda v:v[0].name),
                key=lambda v:v[0].name.upper()))
        return r
    def render_letter(self, context, data):
        return context.tag.clear()[data[0][0].name[0].upper()]
    def render_letters(self, context, data):
        cur = data[0][0].name[0].upper()
        r = []
        for i in self.used_initials:
            if i != cur:
                r.append(tags.a(href='#' + i)[i])
            else:
                r.append(i)
            r.append(' - ')
        if r:
            del r[-1]
        return context.tag.clear()[r]
    def render_linkToThing(self, context, data):
        tag = context.tag.clear()
        if len(data) == 1:
            ob, = data
            return tag[ob.name, ' - ', taglink(ob)]
        else:
            ul = tags.ul()
            for d in sorted(data, key=lambda o:o.fullName()):
                ul[tags.li[taglink(d)]]
            return tag[data[0].name, ul]

class IndexPage(rend.Page):
    filename = 'index.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/index.html'))
    def __init__(self, system):
        self.system = system
    def render_project_link(self, context, data):
        if self.system.options.projecturl:
            return tags.a(href=self.system.options.projecturl)[self.system.options.projectname]
        else:
            return self.system.options.projectname
    def render_project(self, context, data):
        return self.system.options.projectname
    def render_recentChanges(self, context, data):
        return ()
    def render_onlyIfOneRoot(self, context, data):
        if len(self.system.rootobjects) != 1:
            return []
        else:
            root, = self.system.rootobjects
            return context.tag.clear()[
                "Start at ", taglink(root),
                ", the root ", root.kind.lower(), "."]
    def render_onlyIfMultipleRoots(self, context, data):
        if len(self.system.rootobjects) == 1:
            return []
        else:
            return context.tag.clear()

summarypages = [ModuleIndexPage, ClassIndexPage, IndexPage, NameIndexPage]


class CommonPage(rend.Page):
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/common.html'))
    def __init__(self, ob):
        self.ob = ob
    def render_title(self, context, data):
        return self.ob.fullName()
    def render_heading(self, context, data):
        tag = context.tag()
        tag.clear()
        kind = self.ob.kind
        return tag(class_=kind.lower())[kind + " " + mediumName(self.ob)]
    def render_part(self, context, data):
        tag = context.tag()
        tag.clear()
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

    def render_project(self, context, data):
        if self.ob.system.options.projecturl:
            return tags.a(href=self.ob.system.options.projecturl)[self.ob.system.options.projectname]
        else:
            return self.ob.system.options.projectname

    def render_source(self, context, data):
        sourceHref = srclink(self.ob)
        if not sourceHref:
            return ()
        return context.tag(href=sourceHref)

    def render_inhierarchy(self, context, data):
        return ()

    def render_extras(self, context, data):
        return ()

    def render_docstring(self, context, data):
        return epydoc2stan.doc2html(self.ob)

    def children(self):
        return self.ob.orderedcontents

    def render_packageInitTable(self, context, data):
        return ()

    def render_mainTable(self, context, data):
        children = self.children()
        if children:
            return TableFragment(self.ob.system, self.has_lineno_col(), children)
        else:
            return ()

    def has_lineno_col(self):
        if not self.ob.system.options.htmlusesorttable:
            return False
        return isinstance(self.ob, (model.Class, model.Module))

    def render_ifusesorttable(self, context, data):
        if self.ob.system.options.htmlusesorttable:
            return context.tag
        else:
            return ()

    def data_bases(self, context, data):
        return []

    def render_childlist(self, context, data):
        return ()

    def data_methods(self, context, data):
        return []

    def render_childlist(self, context, data):
        child = context.tag.patternGenerator('child')
        tag = context.tag
        for d in data:
            tag[child(data=d)]
        return tag

    def render_attributeHeader(self, context, data):
        if not isinstance(data, twisted.Attribute):
            return ()
        else:
            return context.tag

    def render_functionHeader(self, context, data):
        if not isinstance(data, model.Function):
            return ()
        else:
            return context.tag

    def render_functionName(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[data.name, '(', signature(data.argspec), '):']

    def render_attribute(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[data.name]

    def render_functionAnchor(self, context, data):
        return data.fullName()

    def render_shortFunctionAnchor(self, context, data):
        return data.name

    def render_functionBody(self, context, data):
        return epydoc2stan.doc2html(data)

    def render_functionSourceLink(self, context, data):
        sourceHref = srclink(data)
        if not sourceHref:
            return ()
        return context.tag(href=sourceHref)

class PackagePage(CommonPage):
    def children(self):
        return sorted([o for o in self.ob.orderedcontents
                       if o.name != '__init__'],
                      key=lambda o2:o2.fullName())

    def render_packageInitTable(self, context, data):
        children = self.ob.contents['__init__'].orderedcontents
        if children:
            return [tags.p["From the __init__.py module:"],
                    TableFragment(self.ob.system, self.ob.system.options.htmlusesorttable,
                                  children)]
        else:
            return ()

    def data_methods(self, context, data):
        return [o for o in self.ob.contents['__init__'].orderedcontents
                if isinstance(o, model.Function)]

class TableFragment(rend.Fragment):
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/table.html'))
    last_id = 0
    def __init__(self, system, has_lineno_col, children):
        self.system = system
        self.has_lineno_col = has_lineno_col
        self.children = children
        TableFragment.last_id += 1
        self.id = TableFragment.last_id

    def has_lineno_col(self):
        return True

    def data_children(self, context, data):
        return self.children

    def render_maybelineno(self, context, data):
        if self.has_lineno_col:
            return context.tag
        else:
            return ()

    def render_maybeheadings(self, context, data):
        if self.system.options.htmlusesorttable:
            return context.tag()
        else:
            return ()

    def render_tableid(self, context, data):
        return "tableid" + str(self.id)

    def render_table(self, context, data):
        tag = context.tag
        tag[tag.onePattern('header')]
        pattern = tag.patternGenerator('item')
        for child in self.children:
            if child.document_in_parent_page:
                link_ = tags.a(href=link(child.parent) + '#' + child.name)[child.name]
            else:
                link_ = tags.a(href=link(child))[child.name]
            d = dict(class_=child.kind.lower(),
                     kind=child.kind,
                     name=link_,
                     line=getattr(child, 'linenumber', None),
                     summaryDoc=epydoc2stan.doc2html(child, summary=True))
            tag[pattern(data=d)]
        return tag

class BaseTableFragment(TableFragment):
    def render_childclass(self, context, data):
        return 'base' + data.kind.lower()

    def render_childname(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[tags.a(href=link(data))[data.name]]

class ModulePage(CommonPage):
    def data_methods(self, context, data):
        return [o for o in self.ob.orderedcontents
                if isinstance(o, model.Function)]

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
    def render_extras(self, context, data):
        r = super(ClassPage, self).render_extras(context, data)
        if self.ob.subclasses:
            if r == ():
                r = context.tag.clear()
            sc = self.ob.subclasses[0]
            p = tags.p()
            p["Known subclasses: ", taglink(sc)]
            for sc in self.ob.subclasses[1:]:
                p[', ', taglink(sc)]
            r[p]
        return r

    def render_heading(self, context, data):
        tag = super(ClassPage, self).render_heading(context, data)
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

    def render_inhierarchy(self, context, data):
        return context.tag(href="classIndex.html#"+self.ob.fullName())

    def data_methods(self, context, data):
        return [o for o in self.ob.orderedcontents
                if isinstance(o, model.Function)]

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

    def data_bases(self, context, data):
        r = []
        for baselist in self.nested_bases(self.ob)[1:]:
            if self.unmasked_attrs(baselist):
                r.append(baselist)
        return r

    def render_base_name(self, context, data):
        tag = context.tag.clear()
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

    def render_baseTable(self, context, data):
        return BaseTableFragment(self.ob.system, self.has_lineno_col(),
                                 [o for o in data[0].orderedcontents
                                  if o.name in self.unmasked_attrs(data)])

class TwistedClassPage(ClassPage):
    def data_methods(self, context, data):
        return [o for o in self.ob.orderedcontents if o.document_in_parent_page]

    def render_extras(self, context, data):
        r = super(TwistedClassPage, self).render_extras(context, data)
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
            if r == ():
                r = context.tag.clear()
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

    def render_functionBody(self, context, data):
        imeth = self.interfaceMeth(data.name)
        tag = context.tag()
        tag.clear()
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
    def render_heading(self, context, data):
        tag = super(FunctionPage, self).render_heading(context, data)
        return tag['(', signature(self.ob.argspec), '):']
