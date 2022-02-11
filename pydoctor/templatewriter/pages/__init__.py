"""The classes that turn  L{Documentable} instances into objects we can render."""

from typing import (
    TYPE_CHECKING, Dict, Iterator, List, Optional, Mapping, Sequence,
    Tuple, Type, Union
)
import ast
import abc

from twisted.web.iweb import IRenderable, ITemplateLoader, IRequest
from twisted.web.template import Element, Tag, renderer, tags

from pydoctor.stanutils import html2stan
from pydoctor import epydoc2stan, model, zopeinterface, __version__
from pydoctor.astbuilder import node2fullname
from pydoctor.templatewriter import util, TemplateLookup, TemplateElement
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.epydoc.markup._pyval_repr import colorize_inline_pyval

if TYPE_CHECKING:
    from typing_extensions import Final
    from twisted.web.template import Flattenable
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
    return (-o.privacyClass.value, -o.kind.value if o.kind else 0, o.fullName().lower())

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
        stan = doc.to_stan(epydoc2stan._EpydocLinker(obj))
        # Report eventual warnings. It warns when a regex failed to parse or the html2stan() function fails.
        for message in doc.warnings:
            obj.report(message)
        
        yield '@', stan.children, tags.br()

def format_signature(func: Union[model.Function, model.FunctionOverload]) -> "Flattenable":
    """
    Return a stan representation of a nicely-formatted source-like function signature for the given L{Function}.
    Arguments default values are linked to the appropriate objects when possible.
    """
    return html2stan(str(func.signature)) if func.signature else "(...)"

def format_overloads(func: model.Function) -> Iterator["Flattenable"]:
    """
    Format a function overloads definitions as nice HTML signatures.
    """
    for overload in func.overloads:
        yield tags.div(format_function_def(func.name, func.is_async, overload))

def format_function_def(func_name: str, is_async:bool, 
                        func: Union[model.Function, model.FunctionOverload]) -> List["Flattenable"]:
    """
    Format a function definition.
    """
    r:List["Flattenable"] = []
    def_stmt = 'async def' if is_async else 'def'
    if func_name.endswith('.setter') or func_name.endswith('.deleter'):
        func_name = func_name[:func_name.rindex('.')]
    r.extend([
        tags.span(def_stmt, class_='py-keyword'), ' ',
        tags.span(func_name, class_='py-defname'), 
        format_signature(func), ':'
        ])
    return r

class DocGetter:
    """L{epydoc2stan} bridge."""
    def get(self, ob: model.Documentable, summary: bool = False) -> Tag:
        if summary:
            return epydoc2stan.format_summary(ob)
        else:
            return epydoc2stan.format_docstring(ob)
    def get_type(self, ob: model.Documentable) -> Optional[Tag]:
        return epydoc2stan.type2stan(ob)

class Nav(TemplateElement):
    """
    Common navigation header.
    """

    filename = 'nav.html'

    def __init__(self, system: model.System, loader: ITemplateLoader) -> None:
        super().__init__(loader)
        self.system = system


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
        return Nav(self.system, Nav.lookup_loader(self.template_lookup))

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

    def __init__(self, ob: model.Documentable, template_lookup: TemplateLookup, docgetter: Optional[DocGetter]=None):
        super().__init__(ob.system, template_lookup)
        self.ob = ob
        if docgetter is None:
            docgetter = DocGetter()
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
        msg = self.ob._deprecated_info
        if msg is None:
            return ()
        else:
            return tags.div(msg, role="alert", class_="deprecationNotice alert alert-warning")

    @renderer
    def source(self, request: object, tag: Tag) -> "Flattenable":
        sourceHref = util.srclink(self.ob)
        if not sourceHref:
            return ()
        return tag(href=sourceHref)

    @renderer
    def inhierarchy(self, request: object, tag: Tag) -> "Flattenable":
        return ()

    def extras(self) -> List["Flattenable"]:
        return []

    def docstring(self) -> "Flattenable":
        return self.docgetter.get(self.ob)

    def children(self) -> Sequence[model.Documentable]:
        return sorted(
            (o for o in self.ob.contents.values() if o.isVisible),
            key=objects_order)

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
                      key=objects_order)

    def childlist(self) -> List[Union["AttributeChild", "FunctionChild"]]:
        from pydoctor.templatewriter.pages.attributechild import AttributeChild
        from pydoctor.templatewriter.pages.functionchild import FunctionChild

        r: List[Union["AttributeChild", "FunctionChild"]] = []

        func_loader = FunctionChild.lookup_loader(self.template_lookup)
        attr_loader = AttributeChild.lookup_loader(self.template_lookup)

        for c in self.methods():
            if isinstance(c, model.Function):
                r.append(FunctionChild(self.docgetter, c, self.functionExtras(c), func_loader))
            elif isinstance(c, model.Attribute):
                r.append(AttributeChild(self.docgetter, c, self.functionExtras(c), attr_loader))
            else:
                assert False, type(c)
        return r

    def functionExtras(self, ob: model.Documentable) -> List["Flattenable"]:
        return []

    def functionBody(self, ob: model.Documentable) -> "Flattenable":
        return self.docgetter.get(ob)

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
    def extras(self) -> List["Flattenable"]:
        r = super().extras()

        sourceHref = util.srclink(self.ob)
        if sourceHref:
            r.append(tags.a("(source)", href=sourceHref, class_="sourceLink"))

        return r


class PackagePage(ModulePage):
    def children(self) -> Sequence[model.Documentable]:
        return sorted(
            (o for o in self.ob.contents.values()
             if isinstance(o, model.Module) and o.isVisible),
            key=objects_order)

    def packageInitTable(self) -> "Flattenable":
        children = sorted(
            (o for o in self.ob.contents.values()
             if not isinstance(o, model.Module) and o.isVisible),
            key=objects_order)
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


def overriding_subclasses(
        c: model.Class,
        name: str,
        firstcall: bool = True
        ) -> Iterator[model.Class]:
    if not firstcall and name in c.contents:
        yield c
    else:
        for sc in c.subclasses:
            if sc.isVisible:
                yield from overriding_subclasses(sc, name, False)

def nested_bases(b: model.Class) -> Sequence[Tuple[model.Class, ...]]:
    r: List[Tuple[model.Class, ...]] = [(b,)]
    for b2 in b.baseobjects:
        if b2 is None:
            continue
        for n in nested_bases(b2):
            r.append(n + (b,))
    return r

def unmasked_attrs(baselist: Sequence[model.Documentable]) -> Sequence[model.Documentable]:
    maybe_masking = {
        o.name
        for b in baselist[1:]
        for o in b.contents.values()
        }
    return [o for o in baselist[0].contents.values()
            if o.isVisible and o.name not in maybe_masking]

def assembleList(
        system: model.System,
        label: str,
        lst: Sequence[str],
        idbase: str,
        page_url: str
        ) -> Optional["Flattenable"]:
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
            docgetter: Optional[DocGetter] = None
            ):
        super().__init__(ob, template_lookup, docgetter)
        self.baselists = []
        for baselist in nested_bases(self.ob):
            attrs = unmasked_attrs(baselist)
            if attrs:
                self.baselists.append((baselist, attrs))
        self.overridenInCount = 0

    def extras(self) -> List["Flattenable"]:
        r = super().extras()

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

        scs = sorted(self.ob.subclasses, key=objects_order)
        if not scs:
            return r
        p = assembleList(self.ob.system, "Known subclasses: ",
                         [o.fullName() for o in scs], "moreSubclasses", self.page_url)
        if p is not None:
            r.append(tags.p(p))
        return r

    def classSignature(self) -> "Flattenable":
        r: List["Flattenable"] = []
        _linker = epydoc2stan._EpydocLinker(self.ob)
        zipped = list(zip(self.ob.rawbases, self.ob.bases))
        if zipped:
            r.append('(')
            for idx, (name, full_name) in enumerate(zipped):
                if idx != 0:
                    r.append(', ')

                # link to external class or internal class
                tag = _linker.link_to(full_name, name)
                    
                r.append(tag(title=full_name))
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
                                               sorted(attrs, key=objects_order),
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

    def functionExtras(self, ob: model.Documentable) -> List["Flattenable"]:
        page_url = self.page_url
        name = ob.name
        r: List["Flattenable"] = []
        for b in self.ob.allbases(include_self=False):
            if name not in b.contents:
                continue
            overridden = b.contents[name]
            r.append(tags.div(class_="interfaceinfo")(
                'overrides ', tags.code(epydoc2stan.taglink(overridden, page_url))))
            break
        ocs = sorted(overriding_subclasses(self.ob, name), key=objects_order)
        if ocs:
            self.overridenInCount += 1
            idbase = 'overridenIn' + str(self.overridenInCount)
            l = assembleList(self.ob.system, 'overridden in ',
                             [o.fullName() for o in ocs], idbase, self.page_url)
            if l is not None:
                r.append(tags.div(class_="interfaceinfo")(l))
        return r


class ZopeInterfaceClassPage(ClassPage):
    ob: zopeinterface.ZopeInterfaceClass

    def extras(self) -> List["Flattenable"]:
        r = super().extras()
        if self.ob.isinterface:
            namelist = [o.fullName() for o in 
                        sorted(self.ob.implementedby_directly, key=objects_order)]
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

    def interfaceMeth(self, methname: str) -> Optional[model.Documentable]:
        system = self.ob.system
        for interface in self.ob.allImplementedInterfaces:
            if interface in system.allobjects:
                io = system.allobjects[interface]
                assert isinstance(io, zopeinterface.ZopeInterfaceClass)
                for io2 in io.allbases(include_self=True):
                    method: Optional[model.Documentable] = io2.contents.get(methname)
                    if method is not None:
                        return method
        return None

    def functionExtras(self, ob: model.Documentable) -> List["Flattenable"]:
        imeth = self.interfaceMeth(ob.name)
        r: List["Flattenable"] = []
        if imeth:
            iface = imeth.parent
            assert iface is not None
            r.append(tags.div(class_="interfaceinfo")('from ', tags.code(
                epydoc2stan.taglink(imeth, self.page_url, iface.fullName())
                )))
        r.extend(super().functionExtras(ob))
        return r

commonpages: 'Final[Mapping[str, Type[CommonPage]]]' = {
    'Module': ModulePage,
    'Package': PackagePage,
    'Class': ClassPage,
    'ZopeInterfaceClass': ZopeInterfaceClassPage,
}
"""List all page classes: ties documentable class name with the page class used for rendering"""
