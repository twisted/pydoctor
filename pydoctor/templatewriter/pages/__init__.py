"""The classes that turn  L{Documentable} instances into objects we can render."""


from typing import Any, Dict, Mapping, Iterable, Iterator, List, Optional, Sequence, Union, Type
import ast
import abc

from twisted.web.template import tags, renderer, Tag, Element
import astor

from twisted.web.iweb import IRenderable, ITemplateLoader, IRequest
from pydoctor import epydoc2stan, model, __version__
from pydoctor.astbuilder import node2fullname
from pydoctor.templatewriter import util, TemplateLookup, TemplateElement
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.templatewriter.pages.sidebar import SideBar

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

class Nav(TemplateElement):
    """
    Common navigation header.
    """

    filename = 'nav.html'

    def __init__(self, system: model.System, loader: ITemplateLoader, template_lookup: TemplateLookup) -> None:
        super().__init__(loader)
        self.system = system
        self.template_lookup = template_lookup


class Head(TemplateElement):
    """
    Common metadata.
    """

    filename = 'head.html'

    def __init__(self, title: str, loader: ITemplateLoader) -> None:
        super().__init__(loader)
        self._title = title

    @renderer
    def title(self, request: IRequest, tag: Tag) -> str:
        return self._title


class Page(TemplateElement):
    """
    Abstract base class for output pages.

    Defines special HTML placeholders that are designed to be overriden by users:
    "header.html", "subheader.html" and "footer.html".
    """

    def __init__(self, system: model.System,
                 template_lookup: TemplateLookup,
                 loader: Optional[ITemplateLoader] = None):
        self.system = system
        self.template_lookup = template_lookup
        if not loader:
            loader = self.lookup_loader(template_lookup)
        super().__init__(loader)

    def render(self, request: None) -> Tag:
        tag: Tag
        tag, = super().render(request)
        tag.fillSlots(**self.slot_map)
        return tag

    @property
    def slot_map(self) -> Dict[str, str]:
        system = self.system

        if system.options.projecturl:
            project_tag = tags.a(href=system.options.projecturl, class_="projecthome")
        else:
            project_tag = tags.transparent
        project_tag(system.projectname)

        return dict(
            project=project_tag,
            pydoctor_version=__version__,
            buildtime=system.buildtime.strftime("%Y-%m-%d %H:%M:%S"),
        )

    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @renderer
    def head(self, request: IRequest, tag: Tag) -> IRenderable:
        return Head(self.title(), Head.lookup_loader(self.template_lookup))

    @renderer
    def nav(self, request: IRequest, tag: Tag) -> IRenderable:
        return Nav(self.system, Nav.lookup_loader(self.template_lookup), 
                   template_lookup=self.template_lookup)

    @renderer
    def header(self, request: IRequest, tag: Tag) -> IRenderable:
        return Element(self.template_lookup.get_loader('header.html'))

    @renderer
    def subheader(self, request: IRequest, tag: Tag) -> IRenderable:
        return Element(self.template_lookup.get_loader('subheader.html'))

    @renderer
    def footer(self, request: IRequest, tag: Tag) -> IRenderable:
        return Element(self.template_lookup.get_loader('footer.html'))


class CommonPage(Page):

    filename = 'common.html'
    ob: model.Documentable

    def __init__(self, ob: model.Documentable, template_lookup: TemplateLookup, docgetter: Optional[util.DocGetter]=None):
        super().__init__(ob.system, template_lookup)
        self.ob = ob
        if docgetter is None:
            docgetter = util.DocGetter()
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

        func_loader = FunctionChild.lookup_loader(self.template_lookup)
        attr_loader = AttributeChild.lookup_loader(self.template_lookup)

        for c in self.methods():
            if isinstance(c, model.Function):
                r.append(FunctionChild(self.docgetter, c, self.functionExtras(c), func_loader))
            else:
                r.append(AttributeChild(self.docgetter, c, self.functionExtras(c), attr_loader))
        return r

    def functionExtras(self, data):
        return []

    def functionBody(self, data):
        return self.docgetter.get(data)

    @renderer
    def maindivclass(self, request: IRequest, tag: Tag) -> str:
        return ('nosidebar sidebarloading' 
            if self.ob.system.options.nosidebar else 'sidebarloading')

    @renderer
    def sidebarcontainer(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        if self.ob.system.options.nosidebar:
            return ""
        else:
            # error: Returning Any from function declared to return "Tag"
            return tag.fillSlots(sidebar=SideBar(docgetter=self.docgetter, # type: ignore[no-any-return]
                                 ob=self.ob, template_lookup=self.template_lookup))

    @property
    def slot_map(self) -> Dict[str, str]:
        slot_map = super().slot_map
        slot_map.update(
            heading=self.heading(),
            category=self.category(),
            extras=self.extras(),
            docstring=self.docstring(),
            mainTable=self.mainTable(),
            packageInitTable=self.packageInitTable(),
            childlist=self.childlist(),
        )
        return slot_map


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
        init = self.ob.contents['__init__']
        children = sorted(
            [o for o in init.contents.values() if o.isVisible],
            key=lambda o2:(-o2.privacyClass.value, o2.fullName()))
        if children:
            loader = ChildTable.lookup_loader(self.template_lookup)
            return [tags.p("From the ", tags.code("__init__.py"), " module:",
                           class_="fromInitPy"),
                    ChildTable(self.docgetter, init, children, loader)]
        else:
            return ()

    def methods(self):
        return [o for o in self.ob.contents['__init__'].contents.values()
                if o.documentation_location is model.DocLocation.PARENT_PAGE
                and o.isVisible]


def assembleList(system: model.System, label: str, lst: Iterable[str], idbase: str, page_url: str) -> Optional[Sequence[Union[str, Tag]]]:
    """
    Convert list of object names into a stan tree with clickable links. 
    """
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

    def __init__(self, ob: model.Documentable, template_lookup: TemplateLookup, 
                 docgetter: Optional[util.DocGetter] = None):
        super().__init__(ob, template_lookup, docgetter)
        self.baselists = []
        for baselist in util.nested_bases(self.ob):
            attrs = util.unmasked_attrs(baselist)
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
        baselists = self.baselists[:]
        if not baselists:
            return []
        if baselists[0][0][0] == self.ob:
            del baselists[0]
        loader = ChildTable.lookup_loader(self.template_lookup)
        return [item.clone().fillSlots(
                          baseName=self.baseName(b),
                          baseTable=ChildTable(self.docgetter, self.ob,
                                               sorted(attrs, key=lambda o:-o.privacyClass.value),
                                               loader))
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
        ocs = sorted(util.overriding_subclasses(self.ob, data.name), key=lambda o:o.fullName().lower())
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

commonpages: Mapping[str, Type[CommonPage]] = {
    'Module': ModulePage,
    'Package': PackagePage,
    'Class': ClassPage,
    'ZopeInterfaceClass': ZopeInterfaceClassPage,
}
"""List all page classes: ties documentable class name with the page class used for rendering"""
