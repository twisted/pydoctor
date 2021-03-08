from typing import Iterable, Optional, Sequence, Tuple, Type, Union
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import TagLoader, renderer, tags, Tag, Element

from pydoctor import epydoc2stan
from pydoctor.model import Attribute, Class, Function, Documentable, Module, Package
from pydoctor.templatewriter import TemplateLookup, TemplateElement

class SideBar(TemplateElement):
    """
    Sidebar. 

    Contains:
        - the object docstring TOC if titles are defined
        - for classes: 
            - information about the contents of the current class and parent module/package. 
        - for modules/packages:
            - information about the contents of the module and parent package. 
    """

    #TODO: add the equivalent of reStructuredText directive .. contents automatically.

    filename = 'sidebar.html'

    def __init__(self, docgetter: 'DocGetter', 
                 loader: ITemplateLoader, ob: Documentable, 
                 template_lookup: TemplateLookup):
        super().__init__(loader)
        self.ob = ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter


    @renderer
    def sections(self, request: IRequest, tag: Tag) -> Sequence[Element]:
        """
        Sections are a TOC elements, separated by <hr />
        """
        r = []   
        if isinstance(self.ob, (Package, Module)):
            if isinstance(self.ob, Package):
                r.append(TOC(docgetter=self.docgetter, ob=self.ob,
                                    loader=TagLoader(tag), 
                                    template_lookup=self.template_lookup, first=True))
            else:
                r.append(TOC(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module, 
                             template_lookup=self.template_lookup, first=True))
            if self.ob.parent:
                r.append(TOC(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.parent, 
                             template_lookup=self.template_lookup))
        else:
            r.append(TOC(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob, 
                         template_lookup=self.template_lookup, first=True))
            
            if self.ob.module.name == "__init__" and self.ob.module.parent:
                r.append(TOC(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module.parent, 
                             template_lookup=self.template_lookup))
            else:
                r.append(TOC(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module, 
                             template_lookup=self.template_lookup))
        return r

class TOC(Element):

    def __init__(self, docgetter: 'DocGetter', loader: ITemplateLoader, ob: Documentable, 
                 template_lookup: TemplateLookup, first: bool = False):
        super().__init__(loader)
        self.ob = ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter
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
    def content(self, request: IRequest, tag: Tag) -> Element:
        if isinstance(self.ob, (Package, Module)):
            if isinstance(self.ob, Package):
                return PackageContent(docgetter=self.docgetter,
                                    loader=TagLoader(tag), 
                                    package=self.ob, 
                                    init_module=self.ob.module, 
                                    template_lookup=self.template_lookup)
            else:
                return ObjContent(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module, 
                             template_lookup=self.template_lookup)

        else:
            return ObjContent(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob, 
                         template_lookup=self.template_lookup)

class ObjContent(Element):

    def __init__(self, docgetter: 'DocGetter', loader: ITemplateLoader, ob: Documentable, 
                 template_lookup: TemplateLookup, depth: int = 3, level: int = 0):

        super().__init__(loader)
        self.ob = ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter

        self._depth = depth
        self._level = level + 1

        self.classList = self._getListOf(Class)
        self.functionList = self._getListOf(Function)
        self.variableList = self._getListOf(Attribute)
        self.subModuleList = self._getListOf((Module, Package))

    @renderer
    def docstringToc(self, request: IRequest, tag: Tag) -> Tag:
        
        toc = self.docgetter.get_toc(self.ob)
        if toc:
            return tag.fillSlots(titles=toc)
        else:
            tag.clear()
            return Tag('transparent')

    @renderer
    def classesTitle(self, request: IRequest, tag: Tag) -> str:
        return tag.clear()("Classes") if self.classList else ""

    @renderer
    def classes(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.classList or Tag('transparent')
    
    @renderer
    def functionsTitle(self, request: IRequest, tag: Tag) -> str:
        return (tag.clear()("Functions") if not isinstance(self.ob, Class) 
                else tag.clear()("Methods")) if self.functionList else ""

    @renderer
    def functions(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.functionList or Tag('transparent')

    @renderer
    def variablesTitle(self, request: IRequest, tag: Tag) -> str:
        return (tag.clear()("Variables")) if self.variableList else ""
    
    @renderer
    def variables(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.variableList or Tag('transparent')

    @renderer
    def subModulesTitle(self, request: IRequest, tag: Tag) -> str:
        return tag.clear()("Modules") if self.subModuleList else ""
    
    @renderer
    def subModules(self, request: IRequest, tag: Tag) -> Union[Element, Tag]:
        return self.subModuleList or Tag('transparent')

    def _getListOf(self, 
                         type_: Union[Type[Documentable], 
                                Tuple[Type[Documentable], ...]]
                         ) -> Optional[Element]:
        things = [ child for child in self.children() if isinstance(child, type_) ]
        
        can_be_expanded = False

        # Classes, modules and packages can be expanded in the sidebar. 
        if isinstance(type_, type) and issubclass(type_, (Class, Module, Package)):
            can_be_expanded = True
        elif isinstance(type_, tuple) and any([issubclass(t, (Class, Module, Package)) for t in type_]):
            can_be_expanded = True
        
        if things:
            assert self.loader is not None
            return TOCList(ob=self.ob, children=things,
                    loader=TOCList.lookup_loader(self.template_lookup), docgetter=self.docgetter,
                    expand=self._level < self._depth and can_be_expanded,
                    nestedContentLoader=self.loader, template_lookup=self.template_lookup,
                    level=self._level, depth=self._depth)
        else:
            return None

    def children(self) -> Iterable[Documentable]:
        return sorted(
            [o for o in self.ob.contents.values() if o.isVisible],
            key=lambda o:-o.privacyClass.value)

class PackageContent(ObjContent):
    # This class should be deleted once https://github.com/twisted/pydoctor/pull/360/files has been merged

    def __init__(self,  docgetter: 'DocGetter', loader: ITemplateLoader, package: Package, 
                 init_module: Module, template_lookup: TemplateLookup, depth: int = 3, level: int = 0 ):

        self.init_module = init_module
        super().__init__(docgetter=docgetter, loader=loader, 
                         ob=package, template_lookup=template_lookup, depth=depth, level=level)
        
    def init_module_children(self) -> Iterable[Documentable]:
        return sorted(
            [o for o in self.init_module.contents.values() if o.isVisible],
            key=lambda o:-o.privacyClass.value)
    
    def _getListOf(self, type_: Union[Type[Documentable], 
                                Tuple[Type[Documentable], ...]]
                  ) -> Optional[Element]:
        sub_modules = [ child for child in self.children() if isinstance(child, type_) and child.name != '__init__' ]
        contents_filtered = [ child for child in self.init_module_children() 
                                          if isinstance(child, type_) ] + sub_modules
        things = contents_filtered

        can_be_expanded = False

        # Classes, modules and packages can be expanded in the sidebar. 
        if isinstance(type_, type) and issubclass(type_, (Class, Module, Package)):
            can_be_expanded = True
        elif isinstance(type_, tuple) and any([issubclass(t, (Class, Module, Package)) for t in type_]):
            can_be_expanded = True
        
        if things:
            assert self.loader is not None
            return TOCList(ob=self.ob, children=things,
                    loader=TOCList.lookup_loader(self.template_lookup), docgetter=self.docgetter,
                    expand=self._level < self._depth and can_be_expanded,
                    nestedContentLoader=self.loader, template_lookup=self.template_lookup,
                    level=self._level, depth=self._depth)
        else:
            return None

class LinkOnlyItem(Element):
    def __init__(self, loader: ITemplateLoader, child: Documentable):
        super().__init__(loader)
        self.child = child
    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        return Tag('code')(
            epydoc2stan.taglink(self.child, self.child.url, self.child.name)
            )

class ExpandableItem(LinkOnlyItem):

    last_ExpandableItem_id = 0

    def __init__(self, loader: ITemplateLoader, child: Documentable, contents: Element):
        super().__init__(loader, child)
        self._contents =  contents
        ExpandableItem.last_ExpandableItem_id += 1
        self._id = ExpandableItem.last_ExpandableItem_id
    @renderer
    def contents(self, request: IRequest, tag: Tag) -> Element:
        return self._contents
    @renderer
    def expandableItemId(self, request: IRequest, tag: Tag) -> str:
        return f"tocExpandableItemId{self._id}"

class TOCListItem(Element):

    def __init__(self, loader: ITemplateLoader, ob: Documentable, child: Documentable, docgetter: 'DocGetter',
                 expand: bool, nestedContentLoader: Optional[ITemplateLoader], template_lookup: TemplateLookup,
                 depth: int, level: int):
        super().__init__(loader)
        self.child = child
        self.ob = ob

        self._expand = expand
        self._depth = depth
        self._level = level

        self.nestedContentLoader = nestedContentLoader
        self.docgetter = docgetter
        self.template_lookup = template_lookup

    @renderer
    def class_(self, request: IRequest, tag: Tag) -> str:
        class_ = ''
        # Uncomment if we want to keep same style as in the summary table. 
        # I found it a little bit too colorful. 
        # class_ += 'base' + self.child.css_class + ' '
        if self.child.isPrivate:
            class_ += "private"
        return class_

    def nested_contents(self) -> Element:
        assert self.nestedContentLoader is not None

        if isinstance(self.child, (Package, Module)):
            if isinstance(self.child, Package):
                return PackageContent(docgetter=self.docgetter,
                                    loader=self.nestedContentLoader, 
                                    package=self.child, 
                                    init_module=self.child.module, 
                                    template_lookup=self.template_lookup,
                                    level=self._level, depth=self._depth)
            else:
                return ObjContent(docgetter=self.docgetter, loader=self.nestedContentLoader, ob=self.child.module, 
                             template_lookup=self.template_lookup, level=self._level, depth=self._depth)

        else:
            return ObjContent(docgetter=self.docgetter, loader=self.nestedContentLoader, ob=self.child, 
                         template_lookup=self.template_lookup, level=self._level, depth=self._depth)
    
    @renderer
    def expandableItem(self, request: IRequest, tag: Tag) -> Tag:
        if self._expand:
            return ExpandableItem(TagLoader(tag), self.child, self.nested_contents())
        else:
            return tag.clear()

    @renderer
    def linkOnlyItem(self, request: IRequest, tag: Tag) -> Tag:
        if not self._expand:
            return LinkOnlyItem(TagLoader(tag), self.child)
        else:
            return tag.clear()

class TOCList(TemplateElement):
    # one table per module children kind: classes, functions, variables, modules

    filename = 'sidebar-list.html'

    def __init__(self, ob: Documentable, docgetter: 'DocGetter',
                 children: Iterable[Documentable], loader: ITemplateLoader, 
                 expand: bool, nestedContentLoader: ITemplateLoader, template_lookup: TemplateLookup,
                 depth: int, level: int):
        super().__init__(loader)
        self.ob = ob 
        self.children = children

        self._expand = expand
        self._depth = depth
        self._level = level

        self.nestedContentLoader = nestedContentLoader
        self.docgetter = docgetter
        self.template_lookup = template_lookup
    
    @renderer
    def items(self, request: IRequest, tag: Tag) -> Iterable[Element]:
        return [
            TOCListItem(
                loader=TagLoader(tag),
                ob=self.ob,
                child=child, 
                docgetter=self.docgetter,
                expand=self._expand, 
                nestedContentLoader=self.nestedContentLoader if self._expand else None,
                template_lookup=self.template_lookup, level=self._level, depth=self._depth)
            for child in self.children]
