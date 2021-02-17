"""The classes that turn  L{Documentable} instances into objects we can render."""

from typing import Any, Iterator, List, Optional, Mapping, Sequence, Union, Type
import ast
import abc
import zope.interface.verify

from twisted.web.template import tags, Element, renderer, Tag
import astor

from twisted.web.iweb import IRenderable, ITemplateLoader, IRequest
from pydoctor import epydoc2stan, model, __version__
from pydoctor.astbuilder import node2fullname
from pydoctor.templatewriter import Template, util, TemplateLookup

def format_decorators(obj: Union[model.Function, model.Attribute]) -> Iterator[Any]:
    for dec in obj.decorators or ():
        if isinstance(dec, ast.Call):
            fn = node2fullname(dec.func, obj)
            # We don't want to show the deprecated decorator;
            # it shows up as an infobox.
            if fn in ("twisted.python.deprecate.deprecated",
                      "twisted.python.deprecate.deprecatedProperty"):
                break

        text = '@' + astor.to_source(dec).strip()
        yield text, tags.br()

def signature(function: model.Function) -> str:
    """Return a nicely-formatted source-like function signature."""
    return str(function.signature)

class DocGetter:
    """L{epydoc2stan} bridge."""
    def get(self, ob: model.Documentable, summary: bool = False) -> Tag:
        if summary:
            return epydoc2stan.format_summary(ob)
        else:
            return epydoc2stan.format_docstring(ob)
    def get_type(self, ob: model.Documentable) -> Optional[Tag]:
        return epydoc2stan.type2stan(ob)

class TemplateElement(Element, abc.ABC):
    """
    Element based on a template file. 
    """
    def __init__(self, system: model.System, loader: ITemplateLoader ) -> None:
        """
        Init a new element. 

        @raises TypeError: If C{loader} is not a L{ITemplateLoader} provider. 
        """
        self.system = system
        try:
            zope.interface.verify.verifyObject(ITemplateLoader, loader)
        except Exception as e:
            raise TypeError(f"Cannot create HTML element {self} because template loader "
                            f"is not a ITemplateLoader provider: {type(loader)}") from e
        super().__init__(loader)

    @classmethod
    def lookup_loader(cls, template_lookup: TemplateLookup) -> ITemplateLoader:
        """
        Lookup the template loader with the the C{TemplateLookup}. 

        @raise TypeError: If the C{filename} property is not set. 
        """
        if cls.filename:
            template = cls.template(template_lookup)
            loader = template.loader
            assert loader is not None
            return loader
        else:
            raise TypeError(f"Cannot create loader because '{cls}.filename' property is not set.")

    @classmethod
    def template(cls, template_lookup: Optional[TemplateLookup] = None) -> Template:
        # error: Argument 1 to "get_template" of "TemplateLookup" has incompatible type
        # "Callable[[TemplateElement], str]"; expected "str"
        # We can ignore mypy error because filename is an abstractproperty. 
        if not template_lookup:
            template_lookup = TemplateLookup()
        return template_lookup.get_template(cls.filename) # type: ignore[arg-type]

    @abc.abstractproperty
    def filename(self) -> str:
        """
        Associated template filename. 
        """
        pass

class Nav(TemplateElement):
    """
    Common navigation header. 
    """

    filename = 'nav.html'

    @renderer
    def project(self, request: IRequest, tag: Tag) -> Tag:
        if self.system.options.projecturl:
            return Tag('a', attributes=dict(href=self.system.options.projecturl, id="projecthome"), 
                       children=[self.system.projectname])
        else:
            return Tag('span', children=[self.system.projectname])

class BasePage(TemplateElement):
    """
    Base page element. 

    Defines special HTML placeholders that are designed to be overriden by users: 
    "header.html", "subheader.html" and "footer.html".
    """

    def __init__(self, system: model.System, 
                 template_lookup: TemplateLookup, 
                 loader: Optional[ITemplateLoader] = None) -> None:
        self.template_lookup = template_lookup
        if not loader:
            loader = self.lookup_loader(template_lookup)
        super().__init__(system, loader)

    @renderer
    def nav(self, request: IRequest, tag: Tag) -> IRenderable:
        return Nav(self.system, Nav.lookup_loader(self.template_lookup))

    @renderer
    def header(self, request: IRequest, tag: Tag) -> Union[IRenderable, Tag]:
        # Tag is a IRenderable but mypy is not smart enough.

        template = self.template_lookup.get_template('header.html')
        assert template.loader is not None
        return template.loader.load() if not template.is_empty() else Tag('transparent')

    @renderer
    def subheader(self, request: IRequest, tag: Tag) -> Union[IRenderable, Tag]:
        template = self.template_lookup.get_template('subheader.html')
        assert template.loader is not None
        return template.loader.load() if not template.is_empty() else Tag('transparent')

    @renderer
    def footer(self, request: IRequest, tag: Tag) -> Union[IRenderable, Tag]:
        template = self.template_lookup.get_template('footer.html')
        assert template.loader is not None
        return template.loader.load() if not template.is_empty() else Tag('transparent')

class CommonPage(BasePage):

    filename = 'common.html'
    ob: model.Documentable

    def __init__(self, ob:model.Documentable, template_lookup: TemplateLookup, docgetter: Optional[DocGetter]=None):
        super().__init__(ob.system, template_lookup)
        self.ob = ob
        if docgetter is None:
            docgetter = DocGetter()
        self.docgetter = docgetter

    @property
    def page_url(self) -> str:
        return self.ob.page_object.url

    def title(self):
        return self.ob.fullName()

    def heading(self):
        return tags.h1(class_=self.ob.css_class)(
            tags.code(self.namespace(self.ob))
            )

    def category(self) -> str:
        kind = self.ob.kind
        assert kind is not None
        return f"{kind.lower()} documentation"

    def namespace(self, obj: model.Documentable) -> Sequence[Union[Tag, str]]:
        page_url = self.page_url
        parts: List[Union[Tag, str]] = []
        ob: Optional[model.Documentable] = obj
        while ob:
            if ob.documentation_location is model.DocLocation.OWN_PAGE:
                if parts:
                    parts.extend(['.', tags.wbr])
                parts.append(tags.code(epydoc2stan.taglink(ob, page_url, ob.name)))
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
        from pydoctor.templatewriter.pages.table import ChildTable
        children = self.children()
        if children:
            return ChildTable(self.docgetter, self.ob, children, 
                    ChildTable.lookup_loader(self.template_lookup))
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
                r.append(FunctionChild(self.docgetter, c, self.functionExtras(c), 
                            FunctionChild.lookup_loader(self.template_lookup)))
            else:
                r.append(AttributeChild(self.docgetter, c, self.functionExtras(c), 
                            AttributeChild.lookup_loader(self.template_lookup)))
        return r

    def functionExtras(self, data):
        return []

    def functionBody(self, data):
        return self.docgetter.get(data)

    @renderer
    def all(self, request, tag):
        return tag.fillSlots(
            project=self.system.projectname,
            title=self.title(),
            heading=self.heading(),
            category=self.category(),
            part=self.part(),
            extras=self.extras(),
            docstring=self.docstring(),
            mainTable=self.mainTable(),
            packageInitTable=self.packageInitTable(),
            childlist=self.childlist(),
            version=__version__,
            buildtime=self.ob.system.buildtime.strftime("%Y-%m-%d %H:%M:%S"))


class ModulePage(CommonPage):
    def extras(self):
        r = super().extras()

        sourceHref = util.srclink(self.ob)
        if sourceHref:
            r.append(tags.a("(source)", href=sourceHref, class_="sourceLink"))

        return r


class PackagePage(ModulePage):
    def children(self):
        return sorted((o for o in self.ob.contents.values()
                       if o.name != '__init__' and o.isVisible),
                      key=lambda o2:(-o2.privacyClass.value, o2.fullName()))

    def packageInitTable(self):
        from pydoctor.templatewriter.pages.table import ChildTable
        init = self.ob.contents['__init__']
        children = sorted(
            [o for o in init.contents.values() if o.isVisible],
            key=lambda o2:(-o2.privacyClass.value, o2.fullName()))
        if children:
            return [tags.p("From the ", tags.code("__init__.py"), " module:",
                           class_="fromInitPy"),
                    ChildTable(self.docgetter, init, children, 
                        ChildTable.lookup_loader(self.template_lookup))]
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


def assembleList(system, label, lst, idbase, page_url):
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
            return tags.code(epydoc2stan.taglink(system.allobjects[item], page_url))
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

    ob: model.Class

    def __init__(self, ob:model.Documentable, template_lookup:TemplateLookup, 
                 docgetter:Optional[DocGetter] = None):
        super().__init__(ob, template_lookup, docgetter)
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
            source = (" ", tags.a("(source)", href=sourceHref, class_="sourceLink"))
        else:
            source = tags.transparent
        r.append(tags.p(tags.code(
            tags.span("class", class_='py-keyword'), " ",
            tags.span(self.ob.name, class_='py-defname'),
            self.classSignature(), ":", source
            )))

        scs = sorted(self.ob.subclasses, key=lambda o:o.fullName().lower())
        if not scs:
            return r
        p = assembleList(self.ob.system, "Known subclasses: ",
                         [o.fullName() for o in scs], "moreSubclasses", self.page_url)
        if p is not None:
            r.append(tags.p(p))
        return r

    def classSignature(self) -> Sequence[Union[Tag, str]]:
        r = []
        zipped = list(zip(self.ob.rawbases, self.ob.bases, self.ob.baseobjects))
        if zipped:
            r.append('(')
            for idx, (name, full_name, base) in enumerate(zipped):
                if idx != 0:
                    r.append(', ')

                if base is None:
                    # External class.
                    url = self.ob.system.intersphinx.getLink(full_name)
                else:
                    # Internal class.
                    url = base.url

                if url is None:
                    tag = tags.span
                else:
                    tag = tags.a(href=url)
                r.append(tag(name, title=full_name))
            r.append(')')
        return r

    @renderer
    def inhierarchy(self, request, tag):
        return tag(href="classIndex.html#"+self.ob.fullName())

    @renderer
    def baseTables(self, request, item):
        from pydoctor.templatewriter.pages.table import ChildTable
        baselists = self.baselists[:]
        if not baselists:
            return []
        if baselists[0][0][0] == self.ob:
            del baselists[0]
        return [item.clone().fillSlots(
                          baseName=self.baseName(b),
                          baseTable=ChildTable(self.docgetter, self.ob,
                                               sorted(attrs, key=lambda o:-o.privacyClass.value), 
                                                ChildTable.lookup_loader(self.template_lookup)))
                for b, attrs in baselists]

    def baseName(self, data):
        page_url = self.page_url
        r = []
        source_base = data[0]
        r.append(tags.code(epydoc2stan.taglink(source_base, page_url, source_base.name)))
        bases_to_mention = data[1:-1]
        if bases_to_mention:
            tail = []
            for b in reversed(bases_to_mention):
                tail.append(tags.code(epydoc2stan.taglink(b, page_url, b.name)))
                tail.append(', ')
            del tail[-1]
            r.extend([' (via ', tail, ')'])
        return r

    def functionExtras(self, data):
        page_url = self.page_url
        r = []
        for b in self.ob.allbases(include_self=False):
            if data.name not in b.contents:
                continue
            overridden = b.contents[data.name]
            r.append(tags.div(class_="interfaceinfo")(
                'overrides ', tags.code(epydoc2stan.taglink(overridden, page_url))))
            break
        ocs = sorted(overriding_subclasses(self.ob, data.name), key=lambda o:o.fullName().lower())
        if ocs:
            self.overridenInCount += 1
            idbase = 'overridenIn' + str(self.overridenInCount)
            l = assembleList(self.ob.system, 'overridden in ',
                             [o.fullName() for o in ocs], idbase, self.page_url)
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
            l = assembleList(self.ob.system, label, namelist, "moreInterface",
                             self.page_url)
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
            r.append(tags.div(class_="interfaceinfo")('from ', tags.code(
                epydoc2stan.taglink(imeth, self.page_url, imeth.parent.fullName())
                )))
        r.extend(super().functionExtras(data))
        return r
        
# Type alias for HTML page: to use in type checking. 
# It's necessary because L{BasePage} doesn't have the same C{__init__} siganture as concrete pages classes. 

AnyDocPage = Union[ClassPage, 
                ZopeInterfaceClassPage, 
                ModulePage,
                PackagePage, 
                CommonPage]

classpages: Mapping[str, Type[AnyDocPage]] = { 
    'Module': ModulePage,
    'Package': PackagePage, 
    'Class': ClassPage, 
    'ZopeInterfaceClass': ZopeInterfaceClassPage, 
}
"""List all page classes: ties documentable class name with the page class used for rendering"""
