import functools
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple, Type, Union
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import TagLoader, renderer, tags, Tag, Element

from pydoctor import epydoc2stan
from pydoctor.model import Attribute, Class, Function, Documentable, Module, Package
from pydoctor.templatewriter import TemplateLookup, TemplateElement


class TableRow(Element):

    def __init__(self, loader: ITemplateLoader, docgetter: 'DocGetter', 
                 ob: Documentable, child: Documentable):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self.child = child

    @renderer
    def class_(self, request: IRequest, tag: Tag) -> str:
        class_ = self.child.css_class
        if self.child.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @renderer
    def kind(self, request: IRequest, tag: Tag) -> Tag:
        child = self.child
        kind = child.kind
        if isinstance(child, Function) and child.is_async:
            # The official name is "coroutine function", but that is both
            # a bit long and not as widely recognized.
            kind = f'Async {kind}'
        return tag.clear()(kind)

    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        return tag.clear()(tags.code(
            epydoc2stan.taglink(self.child, self.ob.url, self.child.name)
            ))

    @renderer
    def summaryDoc(self, request: IRequest, tag: Tag) -> Tag:
        return tag.clear()(self.docgetter.get(self.child, summary=True))

def _partialclass(cls: Type, *args: Any, **kwargs: Any) -> Type:
    # error: Invalid base class "cls", mypy doesn't like _partialclass()
    class NewCls(cls): #type: ignore[misc]
        # base class "object" defined the type as "Callable[[object], None]") 
        __init__ = functools.partialmethod(cls.__init__, *args, **kwargs) # type: ignore[assignment]
        __class__ = cls
    return NewCls

class _ChildTable(TemplateElement):

    last_id = 0

    def __init__(self, ob: Documentable, 
                 children: Iterable[Documentable], loader: ITemplateLoader):
        super().__init__(loader)
        self.children = children
        _ChildTable.last_id += 1
        self._id = _ChildTable.last_id
        self.ob = ob
        self.TableRow: Callable[[ITemplateLoader, Documentable, Documentable], Element] = NotImplemented

    @renderer
    def id(self, request: IRequest, tag: Tag) -> str:
        return 'id'+str(self._id)

    @renderer
    def rows(self, request: IRequest, tag: Tag) -> Iterable[Element]:
        return [
            # error: Unexpected keyword arguments: loader, ob and child. mypy doesn't like _partialclass()
            self.TableRow( #type: ignore[call-arg]
                loader=TagLoader(tag),
                ob=self.ob,
                child=child)
            for child in self.children]

class ChildTable(_ChildTable):

    filename = 'table.html'

    def __init__(self, docgetter: 'DocGetter', ob: Documentable, 
                 children: Iterable[Documentable], loader: ITemplateLoader):
        super().__init__(ob, children, loader)
        self.docgetter = docgetter
        self.TableRow = _partialclass(TableRow, docgetter=self.docgetter)

class SideBar(TemplateElement):
    """
    Sidebar. 

    Contains:
        - for classes: 
            - information about the contents of the current class and module 
        - for modules/packages:
            - information about the contents of the module and super-module 
    """

    #TODO: add the equivalent of reStructuredText directive .. contents automatically.

    filename = 'sidebar.html'

    def __init__(self, docgetter: 'DocGetter', loader: ITemplateLoader, ob: Documentable, template_lookup: TemplateLookup):
        super().__init__(loader)
        self.ob = ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter

    @renderer
    def docstringToc(self, request: IRequest, tag: Tag) -> Union[Tag, Element]:
        
        toc = self.docgetter.get_toc(self.ob)
        if toc:
            return tag.fillSlots(sectionList=toc)
        else:
            tag.clear()
            return Tag('transparent')

    @renderer
    def moduleToc(self, request: IRequest, tag: Tag) -> Sequence[Element]:
        r = []   
        if isinstance(self.ob, (Package, Module)):
            if isinstance(self.ob, Package):
                r.append(PackageTOC(loader=TagLoader(tag), package=self.ob, 
                                    init_module=self.ob.module, 
                                    template_lookup=self.template_lookup, first=True))
            else:
                r.append(TOC(loader=TagLoader(tag), ob=self.ob.module, 
                             template_lookup=self.template_lookup, first=True))
            if self.ob.parent:
                r.append(PackageTOC(loader=TagLoader(tag), package=self.ob.parent, 
                                    init_module=self.ob.parent.module, template_lookup=self.template_lookup))
        else:
            r.append(TOC(loader=TagLoader(tag), ob=self.ob, template_lookup=self.template_lookup, first=True))
            if self.ob.module.name == "__init__" and self.ob.module.parent:
                r.append(PackageTOC(loader=TagLoader(tag), package=self.ob.module.parent, 
                                    init_module=self.ob.parent.module, 
                                    template_lookup=self.template_lookup))
            else:
                r.append(TOC(loader=TagLoader(tag), ob=self.ob.module, 
                             template_lookup=self.template_lookup))
        return r

class TOC(Element):

    def __init__(self, loader: ITemplateLoader, ob: Documentable, 
                 template_lookup: TemplateLookup, first: bool = False):
        super().__init__(loader)
        self.ob = ob
        self.template_lookup = template_lookup
        self.classesTable = self._childTableByType(Class)
        self.functionsTable = self._childTableByType(Function)
        self.variablesTable = self._childTableByType(Attribute)
        self.subModulesTable = self._childTableByType((Module, Package))
        self._first = first

    @renderer
    def separator(self, request: IRequest, tag: Tag) -> Tag:
        return tag.clear()(tags.hr) if not self._first else tag.clear()

    @renderer
    def kind(self, request: IRequest, tag: Tag) -> Tag:
        return tag.clear()(self.ob.kind)

    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        name = self.ob.name
        if name == "__init__" and self.ob.parent:
            name = self.ob.parent.name
        return tag.clear()(name)

    @renderer
    def classesTitle(self, request: IRequest, tag: Tag) -> str:
        return tag.clear()("Classes") if self.classesTable else ""

    @renderer
    def classes(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.classesTable or Tag('transparent')
    
    @renderer
    def functionsTitle(self, request: IRequest, tag: Tag) -> str:
        return (tag.clear()("Functions") if not isinstance(self.ob, Class) 
                else tag.clear()("Methods")) if self.functionsTable else ""

    @renderer
    def functions(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.functionsTable or Tag('transparent')

    @renderer
    def variablesTitle(self, request: IRequest, tag: Tag) -> str:
        return (tag.clear()("Variables")) if self.variablesTable else ""
    
    @renderer
    def variables(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.variablesTable or Tag('transparent')

    @renderer
    def subModulesTitle(self, request: IRequest, tag: Tag) -> str:
        return tag.clear()("Modules") if self.subModulesTable else ""
    
    @renderer
    def subModules(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.subModulesTable or Tag('transparent')

    def _childTableByType(self, 
                         type_: Union[Type[Documentable], 
                                Tuple[Type[Documentable], ...]]
                         ) -> Optional[Element]:
        things = [ child for child in self.children() if isinstance(child, type_) ]
        if things:
            return TOCTable(self.ob, things, 
                    TOCTable.lookup_loader(self.template_lookup))
        else:
            return None

    def children(self) -> Iterable[Documentable]:
        return sorted(
            [o for o in self.ob.contents.values() if o.isVisible],
            key=lambda o:-o.privacyClass.value)

class PackageTOC(TOC):

    def __init__(self, loader: ITemplateLoader, package: Package, 
                 init_module: Module, template_lookup: TemplateLookup, first: bool = False ):

        self.init_module = init_module
        super().__init__(loader=loader, ob=package, template_lookup=template_lookup, first=first)
        
    
    def init_module_children(self) -> Iterable[Documentable]:
        return sorted(
            [o for o in self.init_module.contents.values() if o.isVisible],
            key=lambda o:-o.privacyClass.value)
    
    def _childTableByType(self, 
                          type_: Union[Type[Documentable], 
                                 Tuple[Type[Documentable], ...]]
                            ) -> Optional[Element]:
        sub_modules = [ child for child in self.children() if isinstance(child, type_) ]
        init_module_contents = [ child for child in self.init_module_children() if isinstance(child, type_) ]
        if sub_modules or init_module_contents:
            return PackageTOCTable(self.ob, sub_modules, init_module_contents, 
                                   loader=PackageTOCTable.lookup_loader(self.template_lookup))
        else:
            return None
        
class TOCTableRow(Element):

    def __init__(self, loader: ITemplateLoader, ob: Documentable, child: Documentable):
        super().__init__(loader)
        self.child = child
        self.ob = ob

    @renderer
    def class_(self, request: IRequest, tag: Tag) -> str:
        class_ = self.child.css_class
        # enforce "base" style not too be too colorful 
        class_ = 'base' + class_
        if self.child.isPrivate:
            class_ += " private"
        return class_
    
    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        return tag.clear()(Tag('code')(
            epydoc2stan.taglink(self.child, self.child.url, self.child.name)
            ))

class TOCTable(_ChildTable):
    """Just like L{ChildTable} but without a L{DocGetter} instance."""
    # one table per module children kind: classes, functions, variables, modules

    filename = 'sidebar-table.html'

    def __init__(self, ob: Documentable, 
                 children: Iterable[Documentable], loader: ITemplateLoader):
        super().__init__(ob, children, loader)
        self.TableRow = TOCTableRow

class PackageTOCTable(TOCTable):

    def __init__(self, ob: Documentable, sub_modules: Iterable[Documentable], 
                init_module_contents: Iterable[Documentable], loader: ITemplateLoader):
        super().__init__(ob=ob, children=list(mod for mod in sub_modules if mod.name != '__init__') + init_module_contents, loader=loader)
