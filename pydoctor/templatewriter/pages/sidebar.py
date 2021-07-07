"""
Classes for the sidebar generation. 
"""
from typing import Any, Iterable, Iterator, List, Optional, Tuple, Type, Union
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import TagLoader, renderer, Tag, Element

from pydoctor import epydoc2stan
from pydoctor.model import Attribute, Class, Function, Documentable, Module
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

    def __init__(self, ob: Documentable, docgetter: util.DocGetter, 
                 template_lookup: TemplateLookup):
        super().__init__(loader=self.lookup_loader(template_lookup))
        self.ob = ob
        self.template_lookup = template_lookup
        self.docgetter = docgetter


    @renderer
    def sections(self, request: IRequest, tag: Tag) -> Iterator['SideBarSection']:
        """
        Sections are L{SideBarSection} elements. 
        """

        # The object itself
        yield SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob, 
                        documented_ob=self.ob, template_lookup=self.template_lookup)

        if isinstance(self.ob, Module):            
            if self.ob.parent:
                # The parent package of the module
                yield SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.parent, 
                              documented_ob=self.ob, template_lookup=self.template_lookup)
        else:
            # The parent of the object
            yield SideBarSection(docgetter=self.docgetter, loader=TagLoader(tag), ob=self.ob.module, 
                            documented_ob=self.ob, template_lookup=self.template_lookup)

class SideBarSection(Element):
    """
    Main sidebar section. 
    
    The sidebar typically contains two C{SideBarSection}: one for the documented object and one for it's parent. 
    Root modules have only one section. 
    """
    
    def __init__(self, ob: Documentable, documented_ob: Documentable, docgetter: util.DocGetter, 
                 loader: ITemplateLoader, template_lookup: TemplateLookup):
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
        return epydoc2stan.format_kind(self.ob.kind) if self.ob.kind else 'Unknown kind'

    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        """Craft a <code><a> block for the title with custom description when hovering. """
        name = self.ob.name
        link = epydoc2stan.taglink(self.ob, self.ob.url, name)
        link.attributes['title'] = self.description()
        tag = Tag('code')(link)
        if self._represents_documented_ob:
            tag.attributes['class'] = 'thisobject'
        return tag

    def description(self) -> str:
        """
        Short description of the sidebar section.
        """
        return (f"This {epydoc2stan.format_kind(self.documented_ob.kind).lower() if self.documented_ob.kind else 'object'}" if self._represents_documented_ob 
                    else f"The parent of this {epydoc2stan.format_kind(self.documented_ob.kind).lower() if self.documented_ob.kind else 'object'}" 
                    if self.ob in [self.documented_ob.parent, self.documented_ob.module.parent] else "")

    @renderer
    def content(self, request: IRequest, tag: Tag) -> 'ObjContent':
        
        return ObjContent(ob=self.ob, docgetter=self.docgetter, 
                    loader=TagLoader(tag), 
                    documented_ob=self.documented_ob,
                    template_lookup=self.template_lookup, 
                    depth=self.ob.system.options.sidebarexpanddepth)

class ObjContent(Element):
    """
    Object content displayed on the sidebar. 

    Each L{SideBarSection} object uses one of these in the L{SideBarSection.content} renderer. 
    This object is also used to represent the contents of nested expandable items.

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
        self.subModuleList = self._getListOf(Module)

        self.inheritedFunctionList = self._getListOf(Function, inherited=True) if isinstance(self.ob, Class) else None
        self.inheritedVariableList = self._getListOf(Attribute, inherited=True) if isinstance(self.ob, Class) else None
    
    def _getListOf(self, type_: Type[Documentable],
                         inherited: bool = False) -> Optional['ContentList']:
        children = self._children(inherited=inherited)
        if children:
            things = [ child for child in children if isinstance(child, type_) ]
            return self._getListFrom(things, expand=self._isExpandable(type_))
        else:
            return None

    #TODO: ensure not to crash if heterogeneous Documentable types are passed

    def _getListFrom(self, things: List[Documentable], expand: bool) -> Optional['ContentList']:
        if things:
            assert self.loader is not None
            return ContentList(ob=self.ob, children=things, 
                    documented_ob=self.documented_ob,
                    docgetter=self.docgetter,
                    expand=expand,
                    nested_content_loader=self.loader, 
                    template_lookup=self.template_lookup,
                    level_depth=(self._level, self._depth))
        else:
            return None
    

    def _children(self, inherited: bool = False) -> Optional[List[Documentable]]:
        """
        Compute the children of this object.
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
                return sorted((o for o in children if o.isVisible),
                              key=util.objects_order)
            else:
                return None
        else:
            return sorted((o for o in self.ob.contents.values() if o.isVisible),
                              key=util.objects_order)

    def _isExpandable(self, list_type: Type[Documentable]) -> bool:
        """
        Should the list items be expandable?
        """
        
        can_be_expanded = False

        # Classes, modules and packages can be expanded in the sidebar. 
        if issubclass(list_type, (Class, Module)):
            can_be_expanded = True
        
        return self._level < self._depth and can_be_expanded

    @renderer
    def docstringToc(self, request: IRequest, tag: Tag) -> Union[Tag, str]:
        
        toc = self.docgetter.get_toc(self.ob)

        # Only show the TOC if visiting the object page itself, in other words, the TOC do dot show up
        # in the object's parent section or any other subsections except the main one.
        if toc and self.documented_ob == self.ob:
            return tag.fillSlots(titles=toc)
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

    @property
    def has_contents(self) -> bool:
        return self.classList or self.functionList or self.variableList or self.subModuleList or self.inheritedFunctionList or self.inheritedVariableList    

class ContentList(TemplateElement):
    """
    List of child objects that share the same type. 

    One L{ObjContent} element can have up to six C{ContentList}: 
        - classes 
        - functions/methods
        - variables/attributes
        - modules
        - inherited attributes
        - inherited methods
    """
    # one table per module children types: classes, functions, variables, modules

    filename = 'sidebar-list.html'

    def __init__(self, ob: Documentable, docgetter: util.DocGetter,
                 children: Iterable[Documentable], documented_ob: Documentable, 
                 expand: bool, nested_content_loader: ITemplateLoader, template_lookup: TemplateLookup,
                 level_depth: Tuple[int, int]):
        super().__init__(loader=self.lookup_loader(template_lookup))
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

        for child in self.children:

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
        

class ContentItem(Element):
    """
    L{ContentList} item. 
    """


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
        # We could keep same style as in the summary table. 
        # But I found it a little bit too colorful.
        if self.child.isPrivate:
            class_ += "private"
        if self.child == self.documented_ob:
            class_ += " thisobject"
        return class_

    def _contents(self) -> ObjContent:

        return ObjContent(ob=self.child, docgetter=self.docgetter,
                    loader=self.nested_content_loader, 
                    documented_ob=self.documented_ob,
                    level=self._level_depth[0], 
                    depth=self._level_depth[1],
                    template_lookup=self.template_lookup)
    
    @renderer
    def expandableItem(self, request: IRequest, tag: Tag) -> Union[str, 'ExpandableItem']:
        if self._expand:
            nested_contents = self._contents()

            # pass do_not_expand=True also when an object do not have any members, 
            # instead of expanding on an empty div. 
            return ExpandableItem(TagLoader(tag), self.child, nested_contents, 
                    do_not_expand=self.child == self.documented_ob or not nested_contents.has_contents)
        else:
            return ""

    @renderer
    def linkOnlyItem(self, request: IRequest, tag: Tag) -> Union[str, 'LinkOnlyItem']:
        if not self._expand:
            return LinkOnlyItem(TagLoader(tag), self.child)
        else:
            return ""

class LinkOnlyItem(Element):
    """
    Sidebar leaf item: just a link to an object.

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
    Sidebar expandable item: link to an object and have a triangle that expand/collapse it's contents

    Used by L{ContentItem.expandableItem}

    @note: ExpandableItem can be created with C{do_not_expand} flag. 
           This will generate a expandable item with a special C{notExpandable} CSS class. 
           It differs from L{LinkOnlyItem}, wich do not show the expand button, 
           here we show it but we make it unusable by assinging an empty CSS ID. 
    """

    last_ExpandableItem_id = 0

    def __init__(self, loader: ITemplateLoader, child: Documentable, contents: ObjContent, do_not_expand: bool = False):
        super().__init__(loader, child)
        self._contents =  contents
        self._do_not_expand = do_not_expand
        ExpandableItem.last_ExpandableItem_id += 1
        self._id = ExpandableItem.last_ExpandableItem_id
    @renderer
    def labelClass(self, request: IRequest, tag: Tag) -> str:
        assert all(isinstance(child, str) for child in tag.children)
        classes: List[Any] = tag.children
        if self._do_not_expand:
            classes.append('notExpandable')
        return ' '.join(classes)
    @renderer
    def contents(self, request: IRequest, tag: Tag) -> ObjContent:
        return self._contents
    @renderer
    def expandableItemId(self, request: IRequest, tag: Tag) -> str:
        return f"expandableItemId{self._id}"
    @renderer
    def labelForExpandableItemId(self, request: IRequest, tag: Tag) -> str:
        return f"expandableItemId{self._id}" if not self._do_not_expand else ""