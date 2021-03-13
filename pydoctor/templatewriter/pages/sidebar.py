"""
Classes for the sidebar generation. 
"""
from typing import Iterable, List, Optional, Sequence, Tuple, Type, Union
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import TagLoader, renderer, Tag, Element

from pydoctor import epydoc2stan
from pydoctor.model import Attribute, Class, Function, Documentable, Module, Package
from pydoctor.templatewriter import util, TemplateLookup, TemplateElement

class SideBar(TemplateElement):
    """
    Sidebar. 

    Contains:
        - the object docstring table of contents if titles are defined
        - for classes: 
            - information about the contents of the current class and parent module/package. 
        - for modules/packages:
            - information about the contents of the module and parent package. 
    """

    filename = 'sidebar.html'

    def __init__(self, docgetter: util.DocGetter, 
                 loader: ITemplateLoader, ob: Documentable, 
                 template_lookup: TemplateLookup):
        super().__init__(loader)
        self.ob = ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter


    @renderer
    def sections(self, request: IRequest, tag: Tag) -> Sequence[Element]:
        """
        Sections are L{SideBarSection} elements. 
        """
        r = []   
        if isinstance(self.ob, (Package, Module)):
            if isinstance(self.ob, Package):
                # The object itself
                r.append(SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob, 
                            documented_ob=self.ob, template_lookup=self.template_lookup))
            else:
                # The object itself
                r.append(SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob, 
                              documented_ob=self.ob, template_lookup=self.template_lookup))
            if self.ob.parent:
                # The parent of the object
                r.append(SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.parent, 
                              documented_ob=self.ob, template_lookup=self.template_lookup))
        else:
            # The object itself
            r.append(SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob, 
                          documented_ob=self.ob, template_lookup=self.template_lookup))

            #TODO: check compatibility once https://github.com/twisted/pydoctor/pull/360/files is merged
            if self.ob.module.name == "__init__" and self.ob.module.parent:
                # The parent of the object
                r.append(SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module.parent, 
                              documented_ob=self.ob, template_lookup=self.template_lookup))
            else:
                # The parent of the object
                r.append(SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module, 
                              documented_ob=self.ob, template_lookup=self.template_lookup))
        return r

class SideBarSection(Element):
    """
    Main sidebar section. 
    
    The sidebar typically contains two C{SideBarSection}: one for the documented object and one for it's parent. 
    Root modules have only one section. 
    """
    
    def __init__(self, docgetter: util.DocGetter, loader: ITemplateLoader, ob: Documentable, 
                 documented_ob: Documentable, template_lookup: TemplateLookup):
        super().__init__(loader)
        self.ob = ob
        self.documented_ob = documented_ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter
        
        # Does this sidebar section represents the object itself ?
        self._represents_documented_ob = self.ob == self.documented_ob
    
    @renderer
    def separator(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return Tag('hr') if not self._represents_documented_ob else ""

    @renderer
    def kind(self, request: IRequest, tag: Tag) -> str:
        return self.ob.kind or 'Unknown kind'

    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        """Craft a <code><a> block for the title. """
        name = self.ob.name
        if name == "__init__" and self.ob.parent:
            name = self.ob.parent.name
        link = epydoc2stan.taglink(self.ob, self.ob.url, name)
        link.attributes['title'] = self.description()
        attributes = {}
        if self._represents_documented_ob:
            attributes['class'] = 'thisObject'
        return Tag('code', children=[link], attributes=attributes)
    
    def description(self) -> str:
        return (f"This {self.documented_ob.kind.lower() if self.documented_ob.kind else 'object'}" if self._represents_documented_ob 
                    else f"The parent{' ' + self.ob.kind.lower() if self.ob.kind else ''} of this {self.documented_ob.kind.lower() if self.documented_ob.kind else 'object'}" 
                    if self.ob in [self.documented_ob.parent, self.documented_ob.module.parent] else "")

    @renderer
    def content(self, request: IRequest, tag: Tag) -> Element:
        if isinstance(self.ob, (Package, Module)):
            if isinstance(self.ob, Package):
                return PackageContent(docgetter=self.docgetter,
                                    loader=TagLoader(tag), 
                                    package=self.ob, 
                                    init_module=self.ob.module, 
                                    documented_ob=self.documented_ob,
                                    template_lookup=self.template_lookup, 
                                    depth=self.ob.system.options.sidebarexpanddepth)
            else:
                return ObjContent(docgetter=self.docgetter, 
                                  loader=TagLoader(tag), 
                                  ob=self.ob.module, 
                                  documented_ob=self.documented_ob,
                                  template_lookup=self.template_lookup, 
                                    depth=self.ob.system.options.sidebarexpanddepth)

        else:
            return ObjContent(docgetter=self.docgetter, 
                              loader=TagLoader(tag), 
                              ob=self.ob, 
                              documented_ob=self.documented_ob,
                              template_lookup=self.template_lookup, 
                              depth=self.ob.system.options.sidebarexpanddepth)

class ObjContent(Element):
    """
    Object content displayed on the sidebar. 

    Each L{SideBarSection} object uses one of these in the L{SideBarSection.content} renderer. 

    Composed by L{ContentList} elements. 
    """

    #TODO: Hide the childrenKindTitle if they are all private and show private is off -> need JS

    def __init__(self, docgetter: util.DocGetter, loader: ITemplateLoader, ob: Documentable, documented_ob: Documentable, 
                 template_lookup: TemplateLookup, depth: int, level: int = 0):

        super().__init__(loader)
        self.ob = ob
        self.documented_ob=documented_ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter

        self._depth = depth
        self._level = level + 1

        self.classList = self._getListOf(Class)
        self.functionList = self._getListOf(Function)
        self.variableList = self._getListOf(Attribute)
        self.subModuleList = self._getListOf((Module, Package))

        self.inheritedFunctionList = self._getListOf(Function, inherited=True) if isinstance(self.ob, Class) else None
        self.inheritedVariableList = self._getListOf(Attribute, inherited=True) if isinstance(self.ob, Class) else None

    def children(self, inherited: bool = False) -> Optional[List[Documentable]]:
        """
        Sorted by name and privacy. 
        """
        if inherited:
            if isinstance(self.ob, Class):
                children : List[Documentable] = []
                for baselist in util.nested_bases(self.ob):
                    #  If the class has super class
                    if len(baselist) >= 2:
                        attrs = util.unmasked_attrs(baselist)
                        if attrs:
                            children.extend(attrs)
                return sorted(
                    [o for o in sorted(children, key=lambda o: o.name) if o.isVisible],
                     key=lambda o:-o.privacyClass.value)
            else:
                return None
        else:
            return sorted(
                # error: Returning Any from function declared to return "SupportsLessThan"
                # because contents type is Dict[str, Any] for now
                [o for o in sorted(self.ob.contents.values(), key=lambda o:o.name) if o.isVisible], # type: ignore[no-any-return]
                 key=lambda o:-o.privacyClass.value)

    def expand_list(self, list_type: Union[Type[Documentable], 
                                            Tuple[Type[Documentable], ...]]) -> bool:
        """
        Should the list items be expandable?
        """
        
        can_be_expanded = False

        # Classes, modules and packages can be expanded in the sidebar. 
        if isinstance(list_type, type) and issubclass(list_type, (Class, Module, Package)):
            can_be_expanded = True
        elif isinstance(list_type, tuple) and any([issubclass(t, (Class, Module, Package)) for t in list_type]):
            can_be_expanded = True
        
        return self._level < self._depth and can_be_expanded

    @renderer
    def docstringToc(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        
        toc = self.docgetter.get_toc(self.ob)
        if toc and self.documented_ob == self.ob:
            # mypy gets error: Returning Any from function declared to return "Union[Tag, str]"
            return tag.fillSlots(titles=toc) # type: ignore[no-any-return]
        else:
            return ""

    @renderer
    def classesTitle(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return tag.clear()("Classes") if self.classList else ""

    @renderer
    def classes(self, request: IRequest, tag: Tag) -> Union[Element, str]:
        return self.classList or ""
    
    @renderer
    def functionsTitle(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return (tag.clear()("Functions") if not isinstance(self.ob, Class) 
                else tag.clear()("Methods")) if self.functionList else ""

    @renderer
    def functions(self, request: IRequest, tag: Tag) -> Union[Element, str]:
        return self.functionList or ""
    
    @renderer
    def inheritedFunctionsTitle(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return tag.clear()("Inherited Methods") if self.inheritedFunctionList else ""

    @renderer
    def inheritedFunctions(self, request: IRequest, tag: Tag) -> Union[Element, str]:
        return self.inheritedFunctionList or ""

    @renderer
    def variablesTitle(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return (tag.clear()("Variables") if not isinstance(self.ob, Class)
                else tag.clear()("Attributes")) if self.variableList else ""
    
    @renderer
    def variables(self, request: IRequest, tag: Tag) -> Union[Element, str]:
        return self.variableList or ""

    @renderer
    def inheritedVariablesTitle(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return tag.clear()("Inherited Attributes") if self.inheritedVariableList else ""

    @renderer
    def inheritedVariables(self, request: IRequest, tag: Tag) -> Union[Element, str]:
        return self.inheritedVariableList or ""

    @renderer
    def subModulesTitle(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        return tag.clear()("Modules") if self.subModuleList else ""
    
    @renderer
    def subModules(self, request: IRequest, tag: Tag) -> Union[Element, str]:
        return self.subModuleList or ""

    def _getListOf(self, type_: Union[Type[Documentable], 
                                Tuple[Type[Documentable], ...]],
                         inherited: bool = False) -> Optional[Element]:
        children = self.children(inherited=inherited)
        if children:
            things = [ child for child in children if isinstance(child, type_) ]
            return self._getListFrom(things, expand=self.expand_list(type_))
        else:
            return None

    #TODO: ensure not to crash if heterogeneous Documentable types are passed

    def _getListFrom(self, things: Iterable[Documentable], expand: bool) -> Optional[Element]:
        if things:
            assert self.loader is not None
            return ContentList(ob=self.ob, children=things, 
                    documented_ob=self.documented_ob,
                    loader=ContentList.lookup_loader(self.template_lookup), 
                    docgetter=self.docgetter,
                    expand=expand,
                    nested_content_loader=self.loader, 
                    template_lookup=self.template_lookup,
                    level_depth=(self._level, self._depth))
        else:
            return None
        

class PackageContent(ObjContent):
    # This class should be deleted once https://github.com/twisted/pydoctor/pull/360/files has been merged

    def __init__(self,  docgetter: util.DocGetter, loader: ITemplateLoader, package: Package, init_module: Module, 
                 documented_ob: Documentable, template_lookup: TemplateLookup, depth: int, level: int = 0):

        self.init_module = init_module
        super().__init__(docgetter=docgetter, loader=loader, ob=package, documented_ob=documented_ob, 
                         template_lookup=template_lookup, depth=depth, level=level)
        
    def init_module_children(self) -> Iterable[Documentable]:
        return sorted(
            [o for o in self.init_module.contents.values() if o.isVisible],
            key=lambda o:-o.privacyClass.value)
    
    def _getListOf(self, type_: Union[Type[Documentable], 
                                Tuple[Type[Documentable], ...]], inherited: bool = False
                  ) -> Optional[Element]:
        children = self.children()
        if children:
            sub_modules = [ child for child in children if isinstance(child, type_) and child.name != '__init__' ]
            contents_filtered = [ child for child in self.init_module_children() 
                                            if isinstance(child, type_) ] + sub_modules
            things = contents_filtered
        else:
            return None

        return self._getListFrom(things, expand=self.expand_list(type_))

class ContentList(TemplateElement):
    """
    List of child objects that share the same kind. 

    One L{ObjContent} element can have up to six C{ContentList}: 
        - classes 
        - functions/methods
        - variables/attributes
        - modules
        - inherited attributes
        - inherited methods
    """
    # one table per module children kind: classes, functions, variables, modules

    filename = 'sidebar-list.html'

    def __init__(self, ob: Documentable, docgetter: util.DocGetter,
                 children: Iterable[Documentable], documented_ob: Documentable, loader: ITemplateLoader, 
                 expand: bool, nested_content_loader: ITemplateLoader, template_lookup: TemplateLookup,
                 level_depth: Tuple[int, int]):
        super().__init__(loader)
        self.ob = ob 
        self.children = children
        self.documented_ob = documented_ob

        self._expand = expand
        self._level_depth = level_depth

        self.nested_content_loader = nested_content_loader
        self.docgetter = docgetter
        self.template_lookup = template_lookup
    
    @renderer
    def items(self, request: IRequest, tag: Tag) -> Iterable[Element]:
        got_documented_ob = False
        for child in self.children:
            if child == self.documented_ob:
                got_documented_ob = True
                continue
            yield ContentItem(
                loader=TagLoader(tag),
                ob=self.ob,
                child=child,
                documented_ob=self.documented_ob,
                docgetter=self.docgetter,
                expand=self._expand, 
                nested_content_loader=self.nested_content_loader,
                template_lookup=self.template_lookup, 
                level_depth=self._level_depth)
        
        if got_documented_ob:
            yield ContentItem(
                loader=TagLoader(tag),
                ob=self.ob,
                child=self.documented_ob,
                documented_ob=self.documented_ob,
                docgetter=self.docgetter,
                expand=False, 
                nested_content_loader=None,
                template_lookup=self.template_lookup, 
                level_depth=self._level_depth)

class ContentItem(Element):
    """
    L{ContentList} item. 
    """

    #TODO: Show a text like "No members" when an object do not have any members, instead of expanding on an empty div. 

    def __init__(self, loader: ITemplateLoader, ob: Documentable, child: Documentable, documented_ob: Documentable,
                 docgetter: util.DocGetter, expand: bool, nested_content_loader: ITemplateLoader, 
                 template_lookup: TemplateLookup, level_depth: Tuple[int, int]):
        
        super().__init__(loader)
        self.child = child
        self.ob = ob
        self.documented_ob = documented_ob

        self._expand = expand
        self._level_depth = level_depth

        self.nested_content_loader = nested_content_loader
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
        if self.child == self.documented_ob:
            class_ += " thisObject"
        return class_

    def nested_contents(self) -> Element:

        if isinstance(self.child, (Package, Module)):
            if isinstance(self.child, Package):
                return PackageContent(docgetter=self.docgetter,
                                    loader=self.nested_content_loader, 
                                    package=self.child, 
                                    init_module=self.child.module, 
                                    documented_ob=self.documented_ob,
                                    template_lookup=self.template_lookup,
                                    level=self._level_depth[0], 
                                    depth=self._level_depth[1])
            else:
                return ObjContent(docgetter=self.docgetter, 
                                 loader=self.nested_content_loader, 
                                 ob=self.child.module, 
                                 documented_ob=self.documented_ob,
                                 template_lookup=self.template_lookup, 
                                 level=self._level_depth[0], 
                                 depth=self._level_depth[1])

        else:
            return ObjContent(docgetter=self.docgetter, 
                              loader=self.nested_content_loader, 
                              ob=self.child, 
                              documented_ob=self.documented_ob,
                              template_lookup=self.template_lookup, 
                              level=self._level_depth[0], 
                              depth=self._level_depth[1])
    
    @renderer
    def expandableItem(self, request: IRequest, tag: Tag) -> Union[str, Element]:
        if self._expand:
            return ExpandableItem(TagLoader(tag), self.child, self.nested_contents())
        else:
            return ""

    @renderer
    def linkOnlyItem(self, request: IRequest, tag: Tag) -> Union[str, Element]:
        if not self._expand:
            return LinkOnlyItem(TagLoader(tag), self.child)
        else:
            return ""

class LinkOnlyItem(Element):
    """
    Sidebar leaf item.

    Used by L{ContentItem.linkOnlyItem}
    """

    def __init__(self, loader: ITemplateLoader, child: Documentable):
        super().__init__(loader)
        self.child = child
    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        return Tag('code', children=[epydoc2stan.taglink(self.child, self.child.url, self.child.name)])

class ExpandableItem(LinkOnlyItem):
    """
    Sidebar expandable item.

    Used by L{ContentItem.expandableItem}
    """

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
        return f"expandableItemId{self._id}"

