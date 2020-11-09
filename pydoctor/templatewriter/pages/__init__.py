"""The classes that turn  L{Documentable} instances into objects we can render."""

from typing import List, Optional, Union

from twisted.web.template import tags, Element, renderer, Tag, XMLFile

from pydoctor import epydoc2stan, model, __version__
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.templatewriter import util

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
    kws = list(zip(backargs, defaults))
    kws.reverse()
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
        things.append(f'*{varargname}')

    for k, v in kwargs:
        things.append(f'{k}={v}')
    if varkwname:
        things.append(f'**{varkwname}')
    return ', '.join(things)

class DocGetter:
    def get(self, ob, summary=False):
        if summary:
            return epydoc2stan.format_summary(ob)
        else:
            doc = epydoc2stan.format_docstring(ob)
            typ = epydoc2stan.type2stan(ob)
            if typ is None:
                return doc
            else:
                return [doc, ' (type: ', typ, ')']

class CommonPage(Element):

    def __init__(self, ob, docgetter=None):
        self.ob = ob
        if docgetter is None:
            docgetter = DocGetter()
        self.docgetter = docgetter

    @property
    def loader(self):
        return XMLFile(util.templatefilepath('common.html'))

    def title(self):
        return self.ob.fullName()

    def mediumName(self, obj):
        return self.ob.fullName()

    def heading(self):
        return tags.h1(class_=self.ob.css_class)(
            tags.code(self.namespace(self.ob))
            )

    def category(self) -> str:
        return f"{self.ob.kind.lower()} documentation"

    def namespace(self, obj: model.Documentable) -> List[Union[Tag, str]]:
        parts: List[Union[Tag, str]] = []
        ob: Optional[model.Documentable] = obj
        while ob:
            if ob.documentation_location is model.DocLocation.OWN_PAGE:
                if parts:
                    parts.append('.')
                parts.append(util.taglink(ob, ob.name))
            ob = ob.parent
        parts.reverse()
        return parts

    # Deprecated: pydoctor's templates no longer use this, but it is kept
    #             for now to not break customized templates like Twisted's.
    #             NOTE: Remember to remove the CSS as well.
    def part(self):
        parent = self.ob.parent
        if parent:
            return 'Part of ', tags.code(self.namespace(parent))
        else:
            return []

    def project(self):
        if self.ob.system.options.projecturl:
            return tags.a(href=self.ob.system.options.projecturl)(self.ob.system.projectname)
        else:
            return self.ob.system.projectname

    @renderer
    def deprecated(self, request, tag):
        if hasattr(self.ob, "_deprecated_info"):
            return (tags.div(self.ob._deprecated_info, role="alert", class_="deprecationNotice alert alert-warning"),)
        else:
            return ()

    @renderer
    def source(self, request, tag):
        sourceHref = util.srclink(self.ob)
        if not sourceHref:
            return ()
        return tag(href=sourceHref)

    @renderer
    def inhierarchy(self, request, tag):
        return ()

    def extras(self):
        return []

    def docstring(self):
        return self.docgetter.get(self.ob)

    def children(self):
        return sorted(
            [o for o in self.ob.contents.values() if o.isVisible],
            key=lambda o:-o.privacyClass.value)

    def packageInitTable(self):
        return ()

    @renderer
    def baseTables(self, request, tag):
        return ()

    def mainTable(self):
        children = self.children()
        if children:
            return ChildTable(self.docgetter, self.ob, children)
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.contents.values()
                if o.documentation_location is model.DocLocation.PARENT_PAGE
                and o.isVisible]

    def childlist(self):
        from pydoctor.templatewriter.pages.attributechild import AttributeChild
        from pydoctor.templatewriter.pages.functionchild import FunctionChild
        r = []
        for c in self.methods():
            if isinstance(c, model.Function):
                r.append(FunctionChild(self.docgetter, c, self.functionExtras(c)))
            else:
                r.append(AttributeChild(self.docgetter, c, self.functionExtras(c)))
        return r

    def functionExtras(self, data):
        return []

    def functionBody(self, data):
        return self.docgetter.get(data)

    @renderer
    def all(self, request, tag):
        return tag.fillSlots(
            title=self.title(),
            heading=self.heading(),
            category=self.category(),
            part=self.part(),
            extras=self.extras(),
            docstring=self.docstring(),
            mainTable=self.mainTable(),
            packageInitTable=self.packageInitTable(),
            childlist=self.childlist(),
            project=self.project(),
            version=__version__.public(),
            buildtime=self.ob.system.buildtime.strftime("%Y-%m-%d %H:%M:%S"))


class ModulePage(CommonPage):
    def extras(self):
        r = super().extras()

        sourceHref = util.srclink(self.ob)
        if sourceHref:
            r.append(tags.a("(source)", href=sourceHref))

        return r


class PackagePage(ModulePage):
    def children(self):
        return sorted((o for o in self.ob.contents.values()
                       if o.name != '__init__' and o.isVisible),
                      key=lambda o2:(-o2.privacyClass.value, o2.fullName()))

    def packageInitTable(self):
        init = self.ob.contents['__init__']
        children = sorted(
            [o for o in init.contents.values() if o.isVisible],
            key=lambda o2:(-o2.privacyClass.value, o2.fullName()))
        if children:
            return [tags.p("From the ", tags.code("__init__.py"), " module:",
                           class_="fromInitPy"),
                    ChildTable(self.docgetter, init, children)]
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.contents['__init__'].contents.values()
                if o.documentation_location is model.DocLocation.PARENT_PAGE
                and o.isVisible]


def overriding_subclasses(c, name, firstcall=True):
    if not firstcall and name in c.contents:
        yield c
    else:
        for sc in c.subclasses:
            if sc.isVisible:
                yield from overriding_subclasses(sc, name, False)

def nested_bases(b):
    r = [(b,)]
    for b2 in b.baseobjects:
        if b2 is None:
            continue
        for n in nested_bases(b2):
            r.append(n + (b,))
    return r

def unmasked_attrs(baselist):
    maybe_masking = {
        o.name
        for b in baselist[1:]
        for o in b.contents.values()
        }
    return [o for o in baselist[0].contents.values()
            if o.isVisible and o.name not in maybe_masking]


def assembleList(system, label, lst, idbase):
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
            return util.taglink(system.allobjects[item])
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
    p.extend(commasep(lst))
    return p


class ClassPage(CommonPage):
    def __init__(self, ob, docgetter=None):
        CommonPage.__init__(self, ob, docgetter)
        self.baselists = []
        for baselist in nested_bases(self.ob):
            attrs = unmasked_attrs(baselist)
            if attrs:
                self.baselists.append((baselist, attrs))
        self.overridenInCount = 0

    def extras(self):
        r = super().extras()

        sourceHref = util.srclink(self.ob)
        if sourceHref:
            source = (" ", tags.a("(source)", href=sourceHref))
        else:
            source = tags.transparent
        r.append(tags.p(tags.code(
            tags.span("class", class_='py-keyword'), " ",
            self.mediumName(self.ob), ":", source
            )))

        scs = sorted(self.ob.subclasses, key=lambda o:o.fullName().lower())
        if not scs:
            return r
        p = assembleList(self.ob.system, "Known subclasses: ",
                         [o.fullName() for o in scs], "moreSubclasses")
        if p is not None:
            r.append(tags.p(p))
        return r

    def mediumName(self, ob):
        r = [super().mediumName(ob)]
        zipped = list(zip(self.ob.rawbases, self.ob.bases, self.ob.baseobjects))
        if zipped:
            r.append('(')
            for i, (n, m, o) in enumerate(zipped):
                if o is None:
                    r.append(tags.span(title=m)(n))
                else:
                    r.append(util.taglink(o, n))
                if i != len(zipped)-1:
                    r.append(', ')
            r.append(')')
        return r

    @renderer
    def inhierarchy(self, request, tag):
        return tag(href="classIndex.html#"+self.ob.fullName())

    @renderer
    def baseTables(self, request, item):
        baselists = self.baselists[:]
        if not baselists:
            return []
        if baselists[0][0][0] == self.ob:
            del baselists[0]
        return [item.clone().fillSlots(
                          baseName=self.baseName(b),
                          baseTable=ChildTable(self.docgetter, self.ob,
                                               sorted(attrs, key=lambda o:-o.privacyClass.value)))
                for b, attrs in baselists]

    def baseName(self, data):
        r = []
        source_base = data[0]
        r.append(util.taglink(source_base, source_base.name))
        bases_to_mention = data[1:-1]
        if bases_to_mention:
            tail = []
            for b in reversed(bases_to_mention):
                tail.append(util.taglink(b, b.name))
                tail.append(', ')
            del tail[-1]
            r.extend([' (via ', tail, ')'])
        return r

    def functionExtras(self, data):
        r = []
        for b in self.ob.allbases(include_self=False):
            if data.name not in b.contents:
                continue
            overridden = b.contents[data.name]
            r.append(tags.div(class_="interfaceinfo")('overrides ', util.taglink(overridden)))
            break
        ocs = sorted(overriding_subclasses(self.ob, data.name), key=lambda o:o.fullName().lower())
        if ocs:
            self.overridenInCount += 1
            idbase = 'overridenIn' + str(self.overridenInCount)
            l = assembleList(self.ob.system, 'overridden in ',
                             [o.fullName() for o in ocs], idbase)
            if l is not None:
                r.append(tags.div(class_="interfaceinfo")(l))
        return r


class ZopeInterfaceClassPage(ClassPage):
    def extras(self):
        r = [super().extras()]
        if self.ob.isinterface:
            namelist = sorted(
                    (o.fullName() for o in self.ob.implementedby_directly),
                    key=lambda x:x.lower())
            label = 'Known implementations: '
        else:
            namelist = sorted(self.ob.implements_directly, key=lambda x:x.lower())
            label = 'Implements interfaces: '
        if namelist:
            l = assembleList(self.ob.system, label, namelist, "moreInterface")
            if l is not None:
                r.append(tags.p(l))
        return r

    def interfaceMeth(self, methname):
        system = self.ob.system
        for interface in self.ob.allImplementedInterfaces:
            if interface in system.allobjects:
                io = system.allobjects[interface]
                for io2 in io.allbases(include_self=True):
                    if methname in io2.contents:
                        return io2.contents[methname]
        return None

    def functionExtras(self, data):
        imeth = self.interfaceMeth(data.name)
        r = []
        if imeth:
            r.append(tags.div(class_="interfaceinfo")('from ', util.taglink(imeth, imeth.parent.fullName())))
        r.extend(super().functionExtras(data))
        return r

class FunctionPage(CommonPage):
    def mediumName(self, ob):
        return [super().mediumName(ob), '(', signature(self.ob.argspec), ')']
