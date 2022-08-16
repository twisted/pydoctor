"""The classes that turn  L{Documentable} instances into objects we can render."""

from typing import (
    TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Mapping, Sequence,
    Tuple, Type, Union
)
import ast
import abc

from twisted.web.iweb import IRenderable, ITemplateLoader, IRequest
from twisted.web.template import Element, Tag, renderer, tags
from pydoctor.extensions import zopeinterface

from pydoctor.stanutils import html2stan
from pydoctor import epydoc2stan, node2stan, model, __version__
from pydoctor.astbuilder import node2fullname
from pydoctor.templatewriter import util, TemplateLookup, TemplateElement
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.templatewriter.pages.sidebar import SideBar
from pydoctor.epydoc.markup._pyval_repr import colorize_inline_pyval

if TYPE_CHECKING:
    from typing_extensions import Final
    from twisted.web.template import Flattenable
    from pydoctor.epydoc.markup import ParsedDocstring
    from pydoctor.templatewriter.pages.attributechild import AttributeChild
    from pydoctor.templatewriter.pages.functionchild import FunctionChild


def objects_order(o: model.Documentable) -> Tuple[int, int, str]: 
    """
    Function to use as the value of standard library's L{sorted} function C{key} argument
    such that the objects are sorted by: Privacy, Kind and Name.

    Example::

        children = sorted((o for o in ob.contents.values() if o.isVisible),
                      key=objects_order)
    """

    def map_kind(kind: model.DocumentableKind) -> model.DocumentableKind:
        if kind == model.DocumentableKind.PACKAGE:
            # packages and modules should be listed together
            return model.DocumentableKind.MODULE
        return kind

    return (-o.privacyClass.value, -map_kind(o.kind).value if o.kind else 0, o.fullName().lower())

def _format_decorators_fallback(_:Any, doc:'ParsedDocstring', __:model.Documentable) -> Tag:
    return Tag('code')(node2stan.gettext(doc.to_node()))
def format_decorators(obj: Union[model.Function, model.Attribute]) -> Iterator["Flattenable"]:
    for dec in obj.decorators or ():
        if isinstance(dec, ast.Call):
            fn = node2fullname(dec.func, obj)
            # We don't want to show the deprecated decorator;
            # it shows up as an infobox.
            if fn in ("twisted.python.deprecate.deprecated",
                      "twisted.python.deprecate.deprecatedProperty"):
                break

        # Colorize decorators!
        doc = colorize_inline_pyval(dec)

        stan = epydoc2stan.safe_to_stan(doc, obj, compact=True, 
            fallback=_format_decorators_fallback, section='rendering of decorators')
        
        # Report eventual warnings. It warns when a regex failed to parse or the html2stan() function fails.
        epydoc2stan.reportWarnings(obj, doc.warnings)
        yield '@', stan.children, tags.br()

def format_signature(function: model.Function) -> "Flattenable":
    """
    Return a stan representation of a nicely-formatted source-like function signature for the given L{Function}.
    Arguments default values are linked to the appropriate objects when possible.
    """
    broken = "(...)"
    try:
        return html2stan(str(function.signature)) if function.signature else broken
    except Exception as e:
        epydoc2stan.reportErrors(function, 
            [epydoc2stan.get_to_stan_error(e)], section='signature')
        return broken

class Nav(TemplateElement):
    """
    Common navigation header.
    """

    filename = 'nav.html'

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

    def render(self, request: Optional[IRequest]) -> Tag:
        return tags.transparent(super().render(request)).fillSlots(**self.slot_map)

    @property
    def slot_map(self) -> Dict[str, "Flattenable"]:
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
        return Nav(Nav.lookup_loader(self.template_lookup))

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

    def title(self) -> str:
        return self.ob.fullName()

    def heading(self) -> Tag:
        return tags.h1(class_=util.css_class(self.ob))(
            tags.code(self.namespace(self.ob))
            )

    def category(self) -> str:
        kind = self.ob.kind
        assert kind is not None
        return f"{epydoc2stan.format_kind(kind).lower()} documentation"

    def namespace(self, obj: model.Documentable) -> List[Union[Tag, str]]:
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
    def deprecated(self, request: object, tag: Tag) -> "Flattenable":
        import warnings
        warnings.warn("Renderer 'CommonPage.deprecated' is deprecated, the twisted's deprecation system is now supported by default.")
        return ''
    @renderer
    def source(self, request: object, tag: Tag) -> "Flattenable":
        sourceHref = util.srclink(self.ob)
        if not sourceHref:
            return ()
        return tag(href=sourceHref)

    @renderer
    def inhierarchy(self, request: object, tag: Tag) -> "Flattenable":
        return ()

    def extras(self) -> List[Tag]:
        return self.objectExtras(self.ob)

    def docstring(self) -> "Flattenable":
        return self.docgetter.get(self.ob)

    def children(self) -> Sequence[model.Documentable]:
        return sorted(
            (o for o in self.ob.contents.values() if o.isVisible),
            key=util.objects_order)

    def packageInitTable(self) -> "Flattenable":
        return ()

    @renderer
    def baseTables(self, request: object, tag: Tag) -> "Flattenable":
        return ()

    def mainTable(self) -> "Flattenable":
        children = self.children()
        if children:
            return ChildTable(self.docgetter, self.ob, children,
                    ChildTable.lookup_loader(self.template_lookup))
        else:
            return ()

    def methods(self) -> Sequence[model.Documentable]:
        return sorted((o for o in self.ob.contents.values()
                       if o.documentation_location is model.DocLocation.PARENT_PAGE and o.isVisible), 
                      key=util.objects_order)

    def childlist(self) -> List[Union["AttributeChild", "FunctionChild"]]:
        from pydoctor.templatewriter.pages.attributechild import AttributeChild
        from pydoctor.templatewriter.pages.functionchild import FunctionChild

        r: List[Union["AttributeChild", "FunctionChild"]] = []

        func_loader = FunctionChild.lookup_loader(self.template_lookup)
        attr_loader = AttributeChild.lookup_loader(self.template_lookup)

        for c in self.methods():
            if isinstance(c, model.Function):
                r.append(FunctionChild(self.docgetter, c, self.objectExtras(c), func_loader))
            elif isinstance(c, model.Attribute):
                r.append(AttributeChild(self.docgetter, c, self.objectExtras(c), attr_loader))
            else:
                assert False, type(c)
        return r

    def objectExtras(self, ob: model.Documentable) -> List[Tag]:
        """
        Flatten each L{model.Documentable.extra_info} list item.
        """
        r: List[Tag] = []
        for extra in ob.extra_info:
            r.append(epydoc2stan.safe_to_stan(extra, ob, compact=False, 
                fallback = lambda _,__,___:epydoc2stan.BROKEN, section='extra'))
        return r


    def functionBody(self, ob: model.Documentable) -> "Flattenable":
        return self.docgetter.get(ob)

    @renderer
    def maindivclass(self, request: IRequest, tag: Tag) -> str:
        return 'nosidebar' if self.ob.system.options.nosidebar else ''

    @renderer
    def sidebarcontainer(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        if self.ob.system.options.nosidebar:
            return ""
        else:
            return tag.fillSlots(sidebar=SideBar(ob=self.ob, template_lookup=self.template_lookup))

    @property
    def slot_map(self) -> Dict[str, "Flattenable"]:
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
    ob: model.Module

    def extras(self) -> List[Tag]:
        r: List[Tag] = []

        sourceHref = util.srclink(self.ob)
        if sourceHref:
            r.append(tags.a("(source)", href=sourceHref, class_="sourceLink"))

        r.extend(super().extras())
        return r


class PackagePage(ModulePage):
    def children(self) -> Sequence[model.Documentable]:
        return sorted(self.ob.submodules(), key=objects_order)

    def packageInitTable(self) -> "Flattenable":
        children = sorted(
            (o for o in self.ob.contents.values()
             if not isinstance(o, model.Module) and o.isVisible),
            key=util.objects_order)
        if children:
            loader = ChildTable.lookup_loader(self.template_lookup)
            return [
                tags.p("From ", tags.code("__init__.py"), ":", class_="fromInitPy"),
                ChildTable(self.docgetter, self.ob, children, loader)
                ]
        else:
            return ()

    def methods(self) -> Sequence[model.Documentable]:
        return [o for o in self.ob.contents.values()
                if o.documentation_location is model.DocLocation.PARENT_PAGE
                and o.isVisible]

def assembleList(
        system: model.System,
        label: str,
        lst: Sequence[str],
        page_url: str
        ) -> Optional["Flattenable"]:
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
    def one(item: str) -> "Flattenable":
        if item in system.allobjects:
            return tags.code(epydoc2stan.taglink(system.allobjects[item], page_url))
        else:
            return item
    def commasep(items: Sequence[str]) -> List["Flattenable"]:
        r = []
        for item in items:
            r.append(one(item))
            r.append(', ')
        del r[-1]
        return r
    p: List["Flattenable"] = [label]
    p.extend(commasep(lst))
    return p


class ClassPage(CommonPage):

    ob: model.Class

    def __init__(self,
            ob: model.Documentable,
            template_lookup: TemplateLookup,
            docgetter: Optional[util.DocGetter] = None
            ):
        super().__init__(ob, template_lookup, docgetter)
        self.baselists = util.class_members(self.ob)

    def extras(self) -> List[Tag]:
        r: List[Tag] = []

        sourceHref = util.srclink(self.ob)
        source: "Flattenable"
        if sourceHref:
            source = (" ", tags.a("(source)", href=sourceHref, class_="sourceLink"))
        else:
            source = tags.transparent
        r.append(tags.p(tags.code(
            tags.span("class", class_='py-keyword'), " ",
            tags.span(self.ob.name, class_='py-defname'),
            self.classSignature(), ":", source
            )))

        subclasses = sorted(self.ob.subclasses, key=util.objects_order)
        if subclasses:
            p = assembleList(self.ob.system, "Known subclasses: ",
                            [o.fullName() for o in subclasses], self.page_url)
            if p is not None:
                r.append(tags.p(p))

        r.extend(super().extras())
        return r

    def classSignature(self) -> "Flattenable":
        r: List["Flattenable"] = []
        # Here, we should use the parent's linker because a base name
        # can't be define in the class itself.
        ctx =  self.ob.parent
        _linker = ctx.docstring_linker
        if self.ob.rawbases:
            r.append('(')
            with _linker.disable_same_page_optimazation():
            
                for idx, (_, base_node) in enumerate(self.ob.rawbases):
                    if idx != 0:
                        r.append(', ')

                    # link to external class or internal class, using the colorizer here
                    # to link to classes with generics (subscripts and other AST expr).
                    stan = epydoc2stan.safe_to_stan(colorize_inline_pyval(base_node), ctx, compact=False, 
                        fallback = epydoc2stan._class_signature_fallback, section='rendering of class signature')
                    r.extend(stan.children)
                    
            r.append(')')
        return r

    @renderer
    def inhierarchy(self, request: object, tag: Tag) -> Tag:
        return tag(href="classIndex.html#"+self.ob.fullName())

    @renderer
    def baseTables(self, request: object, item: Tag) -> "Flattenable":
        baselists = self.baselists[:]
        if not baselists:
            return []
        if baselists[0][0][0] == self.ob:
            del baselists[0]
        loader = ChildTable.lookup_loader(self.template_lookup)
        return [item.clone().fillSlots(
                          baseName=self.baseName(b),
                          baseTable=ChildTable(self.docgetter, self.ob,
                                               sorted(attrs, key=util.objects_order),
                                               loader))
                for b, attrs in baselists]

    def baseName(self, bases: Sequence[model.Class]) -> "Flattenable":
        page_url = self.page_url
        r: List["Flattenable"] = []
        source_base = bases[0]
        r.append(tags.code(epydoc2stan.taglink(source_base, page_url, source_base.name)))
        bases_to_mention = bases[1:-1]
        if bases_to_mention:
            tail: List["Flattenable"] = []
            for b in reversed(bases_to_mention):
                tail.append(tags.code(epydoc2stan.taglink(b, page_url, b.name)))
                tail.append(', ')
            del tail[-1]
            r.extend([' (via ', tail, ')'])
        return r

    def objectExtras(self, ob: model.Documentable) -> List[Tag]:
        r = list(get_override_info(self.ob, ob.name, self.page_url))
        r.extend(super().objectExtras(ob))
        return r

def get_override_info(cls:model.Class, member_name:str, page_url:Optional[str]=None) -> Iterator[Tag]:
    page_url = page_url or cls.page_object.url
    for b in cls.mro(include_self=False):
        if member_name not in b.contents:
            continue
        overridden = b.contents[member_name]
        yield tags.div(class_="interfaceinfo")(
            'overrides ', tags.code(epydoc2stan.taglink(overridden, page_url)))
        break
    
    ocs = sorted(util.overriding_subclasses(cls, member_name), key=util.objects_order)
    if ocs:
        l = assembleList(cls.system, 'overridden in ',
                            [o.fullName() for o in ocs], page_url)
        if l is not None:
            yield tags.div(class_="interfaceinfo")(l)
    

class ZopeInterfaceClassPage(ClassPage):
    ob: zopeinterface.ZopeInterfaceClass

    def extras(self) -> List[Tag]:
        r = super().extras()
        if self.ob.isinterface:
            namelist = [o.fullName() for o in 
                        sorted(self.ob.implementedby_directly, key=util.objects_order)]
            label = 'Known implementations: '
        else:
            namelist = sorted(self.ob.implements_directly, key=lambda x:x.lower())
            label = 'Implements interfaces: '
        if namelist:
            l = assembleList(self.ob.system, label, namelist, self.page_url)
            if l is not None:
                r.append(tags.p(l))
        return r

    def interfaceMeth(self, methname: str) -> Optional[model.Documentable]:
        system = self.ob.system
        for interface in self.ob.allImplementedInterfaces:
            if interface in system.allobjects:
                io = system.allobjects[interface]
                assert isinstance(io, zopeinterface.ZopeInterfaceClass)
                for io2 in io.mro():
                    method: Optional[model.Documentable] = io2.contents.get(methname)
                    if method is not None:
                        return method
        return None

    def objectExtras(self, ob: model.Documentable) -> List[Tag]:
        imeth = self.interfaceMeth(ob.name)
        r: List[Tag] = []
        if imeth:
            iface = imeth.parent
            assert iface is not None
            r.append(tags.div(class_="interfaceinfo")('from ', tags.code(
                epydoc2stan.taglink(imeth, self.page_url, iface.fullName())
                )))
        r.extend(super().objectExtras(ob))
        return r

commonpages: 'Final[Mapping[str, Type[CommonPage]]]' = {
    'Module': ModulePage,
    'Package': PackagePage,
    'Class': ClassPage,
    'ZopeInterfaceClass': ZopeInterfaceClassPage,
}
"""List all page classes: ties documentable class name with the page class used for rendering"""
