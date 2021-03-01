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
        - for classes: 
            - information about the contents of the current class and parent module/package. 
        - for modules/packages:
            - information about the contents of the module and parent package. 
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
        self.classList = self._getListOf(Class)
        self.functionList = self._getListOf(Function)
        self.variableList = self._getListOf(Attribute)
        self.subModuleList = self._getListOf((Module, Package))
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
        if things:
            return TOCList(self.ob, things, 
                    TOCList.lookup_loader(self.template_lookup))
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
    
    def _getListOf(self, 
                          type_: Union[Type[Documentable], 
                                 Tuple[Type[Documentable], ...]]
                            ) -> Optional[Element]:
        sub_modules = [ child for child in self.children() if isinstance(child, type_) and child.name != '__init__' ]
        contents_filtered = [ child for child in self.init_module_children() 
                                          if isinstance(child, type_) ] + sub_modules
        if contents_filtered:
            return TOCList(self.ob, contents_filtered, 
                                   loader=TOCList.lookup_loader(self.template_lookup))
        else:
            return None
        
class TOCListItem(Element):

    def __init__(self, loader: ITemplateLoader, ob: Documentable, child: Documentable):
        super().__init__(loader)
        self.child = child
        self.ob = ob

    @renderer
    def class_(self, request: IRequest, tag: Tag) -> str:
        class_ = ''
        # Uncomment if we want to keep same style as in the summary table. 
        # I found it a little bit too colorful. 
        # class_ += 'base' + self.child.css_class + ' '
        if self.child.isPrivate:
            class_ += "private"
        return class_
    
    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        return tag.clear()(Tag('code')(
            epydoc2stan.taglink(self.child, self.child.url, self.child.name)
            ))

class TOCList(TemplateElement):
    # one table per module children kind: classes, functions, variables, modules

    filename = 'sidebar-list.html'

    def __init__(self, ob: Documentable, 
                 children: Iterable[Documentable], loader: ITemplateLoader):
        super().__init__(loader)
        self.ob = ob 
        self.children = children
    
    @renderer
    def items(self, request: IRequest, tag: Tag) -> Iterable[Element]:
        return [
            TOCListItem(
                loader=TagLoader(tag),
                ob=self.ob,
                child=child)
            for child in self.children]
