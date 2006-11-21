from nevow import inevow, loaders, tags
from zope.interface import implements

from pydoctor import epydoc2stan, model
from pydoctor.nevowhtml.util import templatefile, link, fillSlots, srclink, taglink

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

class CommonPage(object):
    implements(inevow.IRenderer)
    docFactory = loaders.xmlfile(templatefile('common.html'))

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
    docFactory = loaders.xmlfile(templatefile('table.html'))
    last_id = 0
    classprefix = ''
    def __init__(self, system, has_lineno_col, children):
        self.system = system
        self.has_lineno_col = has_lineno_col
        self.children = children
        TableFragment.last_id += 1
        self._id = TableFragment.last_id

    def id(self):
        return 'id'+str(self._id)

    def header(self, header):
        if self.system.options.htmlusesorttable:
            if self.has_lineno_col:
                return fillSlots(header,
                                 linenohead=header.onePattern('linenohead'))
            else:
                return fillSlots(header,
                                 linenohead=())
        else:
            return ()

    def rows(self, row, linenocell):
        rows = []
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
                linenocell_ = fillSlots(linenocell,
                                        lineno=line)
            else:
                linenocell_ = ()
            rows.append(fillSlots(row,
                                  class_=self.classprefix + child.kind.lower(),
                                  kind=child.kind,
                                  name=link_,
                                  linenocell=linenocell_,
                                  summaryDoc=epydoc2stan.doc2html(child, summary=True)))
        return rows

    def rend(self, ctx, data):
        tag = tags.invisible[self.docFactory.load()]
        return fillSlots(tag,
                         id=self.id(),
                         header=self.header(tag.onePattern('header')),
                         rows=self.rows(tag.patternGenerator('row'),
                                        tag.patternGenerator('linenocell')))

class BaseTableFragment(TableFragment):
    classprefix = 'base'

class ModulePage(CommonPage):
    pass

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
