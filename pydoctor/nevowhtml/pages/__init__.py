from nevow import inevow, loaders, tags
from zope.interface import implements

from pydoctor import ast_pp, epydoc2stan, model
from pydoctor.nevowhtml.pages.table import ChildTable
from pydoctor.nevowhtml.util import \
     templatefile, fillSlots, srclink, taglink

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

def mediumName(obj):
    fn = obj.fullName()
    if '.' not in fn:
        return fn
    path, name = fn.rsplit('.', 1)
    def process(part):
        return obj.system.abbrevmapping.get(part, part[0])
    return '.'.join([process(p) for p in path.split('.')]) + '.' + name

class DocGetter(object):
    def get(self, ob, summary=False):
        return epydoc2stan.doc2html(ob, summary=summary)[0]

class CommonPage(object):
    implements(inevow.IRenderer)
    docFactory = loaders.xmlfile(templatefile('common.html'))

    def __init__(self, ob, docgetter=None):
        self.ob = ob
        if docgetter is None:
            docgetter = DocGetter()
        self.docgetter = docgetter
        self.usesorttable = ob.system.options.htmlusesorttable
        self.usesplitlinks = ob.system.options.htmlusesplitlinks
        self.shortenlists = ob.system.options.htmlshortenlists

    def title(self):
        return self.ob.fullName()

    def heading(self):
        return tags.h1(class_=self.ob.lckind)[
            self.ob.kind + " " + mediumName(self.ob)]

    def part(self):
        tag = tags.invisible()
        if self.ob.parent:
            parent = self.ob.parent
            if isinstance(parent, model.Module) and parent.name == '__init__':
                parent = parent.parent
            parts = []
            while parent.parent:
                parts.append(taglink(parent, parent.name))
                parts.append('.')
                parent = parent.parent
            parts.append(taglink(parent, parent.name))
            parts.reverse()
            return tag['Part of ', parts]
        else:
            return tag

    def project(self):
        if self.ob.system.options.projecturl:
            return tags.a(href=self.ob.system.options.projecturl)[self.ob.system.options.projectname]
        elif self.ob.system.options.projectname:
            return self.ob.system.options.projectname
        else:
            return self.ob.system.guessedprojectname

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
        return self.docgetter.get(self.ob)

    def children(self):
        return sorted(
            [o for o in self.ob.orderedcontents if o.isVisible],
            key=lambda o:-o.privacyClass)

    def packageInitTable(self):
        return ()

    def baseTables(self, tag):
        return ()

    def bigTable(self, tag):
        return ()

    def mainTable(self):
        children = self.children()
        if children:
            return ChildTable(self.docgetter, self.ob, self.has_lineno_col(), children)
        else:
            return ()

    def has_lineno_col(self):
        if not self.usesorttable:
            return False
        return isinstance(self.ob, (model.Class, model.Module))

    def ifusesorttable(self, tag):
        if self.usesorttable:
            return tag
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.orderedcontents
                if o.document_in_parent_page and o.isVisible]

    def childlist(self):
        from pydoctor.nevowhtml.pages.attributechild import AttributeChild
        from pydoctor.nevowhtml.pages.functionchild import FunctionChild
        r = []
        for c in self.methods():
            if isinstance(c, model.Function):
                r.append(FunctionChild(self.docgetter, c, self.functionExtras(c)))
            else:
                r.append(AttributeChild(self.docgetter, c))
        return r

    def functionExtras(self, data):
        return []

    def functionBody(self, data):
        return self.docgetter.get(data)

    def ifhasplitlinks(self, tag):
        return ()

    def pydoctorjs(self, tag):
        if self.usesplitlinks or self.shortenlists:
            return tag
        else:
            return ()

    def rend(self, ctx, data):
        tag = tags.invisible[self.docFactory.load()]
        return fillSlots(tag,
                         title=self.title(),
                         ifusesorttable=self.ifusesorttable(tag.onePattern('ifusesorttable')),
                         pydoctorjs=self.pydoctorjs(tag.onePattern('pydoctorjs')),
                         heading=self.heading(),
                         part=self.part(),
                         source=self.source(tag.onePattern('source')),
                         inhierarchy=self.inhierarchy(tag.onePattern('inhierarchy')),
                         extras=self.extras(),
                         docstring=self.docstring(),
                         splittingLinks=self.ifhasplitlinks(tag.onePattern('splittingLinks')),
                         mainTable=self.mainTable(),
                         baseTables=self.baseTables(tag.patternGenerator('baseTable')),
                         bigTable=self.bigTable(tag.patternGenerator('bigTable')),
                         packageInitTable=self.packageInitTable(),
                         childlist=self.childlist(),
                         project=self.project(),
                         buildtime=self.ob.system.buildtime.strftime("%Y-%m-%d %H:%M:%S"),
                         )


class PackagePage(CommonPage):
    def children(self):
        return sorted([o for o in self.ob.orderedcontents
                       if o.name != '__init__' and o.isVisible],
                      key=lambda o2:(-o2.privacyClass, o2.fullName()))

    def packageInitTable(self):
        init = self.ob.contents['__init__']
        children = sorted(
            [o for o in init.orderedcontents if o.isVisible],
            key=lambda o2:(-o2.privacyClass, o2.fullName()))
        if children:
            return [tags.p["From the __init__.py module:"],
                    ChildTable(self.docgetter, init, self.usesorttable, children)]
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.contents['__init__'].orderedcontents
                if o.document_in_parent_page and o.isVisible]

class ModulePage(CommonPage):
    pass

def overriding_subclasses(c, name, firstcall=True):
    if not firstcall and name in c.contents:
        yield c
    else:
        for sc in c.subclasses:
            if sc.isVisible:
                for sc2 in overriding_subclasses(sc, name, False):
                    yield sc2

def nested_bases(b):
    r = [(b,)]
    for b2 in b.baseobjects:
        if b2 is None:
            continue
        for n in nested_bases(b2):
            r.append(n + (b,))
    return r

def unmasked_attrs(baselist):
    maybe_masking = set()
    for b in baselist[1:]:
        maybe_masking.update(set([o.name for o in b.orderedcontents]))
    return [o for o in baselist[0].orderedcontents if o.name not in maybe_masking]


def maybeShortenList(system, label, lst, idbase):
    lst2 = []
    for name in lst:
        o = system.allobjects.get(name)
        if o is None or o.isVisible:
            lst2.append(name)
    lst = lst2
    if not lst:
        return None
    def one(item):
        if item in system.allobjects:
            return taglink(system.allobjects[item])
        else:
            return item
    def commasep(items):
        r = []
        for item in items:
            r.append(one(item))
            r.append(', ')
        del r[-1]
        return r
    p = [label]
    if len(lst) <= 5 or not system.options.htmlshortenlists:
        p.extend(commasep(lst))
    else:
        p.extend(commasep(lst[:3]))
        q = [', ']
        q.extend(commasep(lst[3:]))
        q.append(tags.span(class_='showIfJS')[
            ' ',
            tags.a(href="#",
                   onclick="showAndHide('%s');"%idbase,
                   class_="jslink")
            ['(hide last %d again)'%len(lst[3:])]])
        p.append(tags.span(id=idbase, class_='hideIfJS')[q])
        p.append(tags.span(id=idbase+'Link', class_='showIfJS')[
            ' ',
            tags.a(href="#",
                   onclick="hideAndShow('%s');"%idbase,
                   class_="jslink")
            ['... and %d more'%len(lst[3:])]])
    return p

class ClassPage(CommonPage):
    def __init__(self, ob, docgetter=None):
        CommonPage.__init__(self, ob, docgetter)
        self.baselists = []
        self.usesplitlinks = ob.system.options.htmlusesplitlinks
        for baselist in nested_bases(self.ob):
            attrs = unmasked_attrs(baselist)
            if attrs:
                self.baselists.append((baselist, attrs))
        self.overridenInCount = 0

    def extras(self):
        r = super(ClassPage, self).extras()
        scs = sorted(self.ob.subclasses, key=lambda o:o.fullName().lower())
        if not scs:
            return r
        p = maybeShortenList(self.ob.system, "Known subclasses: ",
                             [o.fullName() for o in scs], "moreSubclasses")
        if p is not None:
            r[tags.p[p]]
        return r

    def ifhasplitlinks(self, tag):
        if self.usesplitlinks and len(self.baselists) > 1:
            return tag
        else:
            return ()

    def heading(self):
        tag = super(ClassPage, self).heading()
        zipped = zip(self.ob.rawbases, self.ob.bases, self.ob.baseobjects)
        if zipped:
            tag['(']
            for i, (n, m, o) in enumerate(zipped):
                if o is None:
                    tag[tags.span(title=m)[n]]
                else:
                    tag[taglink(o, n)]
                if i != len(zipped)-1:
                    tag[', ']
            tag[')']
        tag[':']
        return tag

    def inhierarchy(self, tag):
        return tag(href="classIndex.html#"+self.ob.fullName())

    def baseTables(self, item):
        return [fillSlots(item,
                          baseName=self.baseName(b),
                          baseTable=ChildTable(self.docgetter, self.ob, self.has_lineno_col(),
                                                  sorted(attrs, key=lambda o:-o.privacyClass)))
                for b, attrs in self.baselists[1:]]

    def baseName(self, data):
        tag = tags.invisible()
        source_base = data[0]
        tag[taglink(source_base, source_base.name)]
        bases_to_mention = data[1:-1]
        if bases_to_mention:
            tail = []
            for b in reversed(bases_to_mention):
                tail.append(taglink(b, b.name))
                tail.append(', ')
            del tail[-1]
            tag[' (via ', tail, ')']
        return tag

    def bigTable(self, tag):
        if not self.usesplitlinks or len(self.baselists) == 1:
            return ()
        all_attrs = []
        for b, attrs in self.baselists:
            all_attrs.extend(attrs)
        all_attrs.sort(key=lambda o:(-o.privacyClass, o.name.lower()))
        return tag[ChildTable(self.docgetter, self.ob, self.has_lineno_col(), all_attrs)]

    def functionExtras(self, data):
        r = []
        for b in self.ob.allbases():
            if data.name not in b.contents:
                continue
            overridden = b.contents[data.name]
            r.append(tags.div(class_="interfaceinfo")['overrides ', taglink(overridden)])
            break
        ocs = sorted(overriding_subclasses(self.ob, data.name), key=lambda o:o.fullName().lower())
        if ocs:
            self.overridenInCount += 1
            idbase = 'overridenIn' + str(self.overridenInCount)
            l = maybeShortenList(self.ob.system, 'overridden in ',
                                 [o.fullName() for o in ocs], idbase)
            if l is not None:
                r.append(tags.div(class_="interfaceinfo")[l])
        return r


class ZopeInterfaceClassPage(ClassPage):
    def extras(self):
        r = super(ZopeInterfaceClassPage, self).extras()
        system = self.ob.system
        def tl(s):
            if s in system.allobjects:
                return taglink(system.allobjects[s])
            else:
                return s
        if self.ob.isinterface:
            namelist = sorted(self.ob.implementedby_directly, key=lambda x:x.lower())
            label = 'Known implementations: '
        else:
            namelist = sorted(self.ob.implements_directly, key=lambda x:x.lower())
            label = 'Implements interfaces: '
        if namelist:
            l = maybeShortenList(self.ob.system, label, namelist, "moreInterface")
            if l is not None:
                r[tags.p[l]]
        return r

    def interfaceMeth(self, methname):
        system = self.ob.system
        for interface in self.ob.allImplementedInterfaces:
            if interface in system.allobjects:
                io = system.allobjects[interface]
                if methname in io.contents:
                    return io.contents[methname]
        return None

    def functionExtras(self, data):
        imeth = self.interfaceMeth(data.name)
        r = []
        if imeth:
            r.append(tags.div(class_="interfaceinfo")['from ', taglink(imeth, imeth.parent.fullName())])
        r.extend(super(ZopeInterfaceClassPage, self).functionExtras(data))
        return r

class FunctionPage(CommonPage):
    def heading(self):
        tag = super(FunctionPage, self).heading()
        return tag['(', signature(self.ob.argspec), '):']
