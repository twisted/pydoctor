"""
Classes for the sidebar generation. 
"""
from __future__ import annotations

from typing import Any, Iterator, List, Optional, Sequence, Tuple, Type, Union
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import TagLoader, renderer, Tag, Element, tags

from pydoctor import epydoc2stan
from pydoctor.model import Attribute, Class, Function, Documentable, Module
from pydoctor.templatewriter import util, TemplateLookup, TemplateElement

from pydoctor.napoleon.iterators import peek_iter

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

    def __init__(self, ob: Documentable, template_lookup: TemplateLookup):
        super().__init__(loader=self.lookup_loader(template_lookup))
        self.ob = ob
        self.template_lookup = template_lookup


    @renderer
    def sections(self, request: IRequest, tag: Tag) -> Iterator['SideBarSection']:
        """
        Sections are L{SideBarSection} elements. 
        """

        # The object itself
        yield SideBarSection(loader=TagLoader(tag), ob=self.ob, 
                        documented_ob=self.ob, template_lookup=self.template_lookup)

        parent: Optional[Documentable] = None
        if isinstance(self.ob, Module):
            # The object is a module, we document the parent package in the second section (if it's not a root module).
            if self.ob.parent:
                parent = self.ob.parent
        else:
            # The object is a class/function or attribute, we docuement the module that contains the object, not it's direct parent. 
            # 
            parent = self.ob.module
            
        if parent:
            yield SideBarSection(loader=TagLoader(tag), ob=parent, 
                            documented_ob=self.ob, template_lookup=self.template_lookup)
class SideBarSection(Element):
    """
    Main sidebar section. 
    
    The sidebar typically contains two C{SideBarSection}: one for the documented object and one for it's parent. 
    Root modules have only one section. 
    """
    
    def __init__(self, ob: Documentable, documented_ob: Documentable, 
                 loader: ITemplateLoader, template_lookup: TemplateLookup):
        super().__init__(loader)
        self.ob = ob
        self.documented_ob = documented_ob
        self.template_lookup = template_lookup
        
        # Does this sidebar section represents the object itself ?
        self._represents_documented_ob = self.ob is self.documented_ob

    @renderer
    def kind(self, request: IRequest, tag: Tag) -> str:
        return epydoc2stan.format_kind(self.ob.kind) if self.ob.kind else 'Unknown kind'

    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        """Craft a <code><a> block for the title with custom description when hovering. """
        name = self.ob.name
        link = epydoc2stan.taglink(self.ob, self.ob.page_object.url, 
            epydoc2stan.insert_break_points(name))
        tag = tags.code(link(title=self.description()))
        if self._represents_documented_ob:
            tag(class_='thisobject')
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
        
        return ObjContent(ob=self.ob,
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

    #FIXME: https://github.com/twisted/pydoctor/issues/600

    def __init__(self, loader: ITemplateLoader, ob: Documentable, documented_ob: Documentable, 
                 template_lookup: TemplateLookup, depth: int, level: int = 0):

        super().__init__(loader)
        self.ob = ob
        self.documented_ob = documented_ob
        self.template_lookup = template_lookup

        self._depth = depth
        self._level = level + 1

        _direct_children = self._children(inherited=False)

        self.classList = self._getContentList(_direct_children, Class)
        self.functionList = self._getContentList(_direct_children, Function)
        self.variableList = self._getContentList(_direct_children, Attribute)
        self.subModuleList = self._getContentList(_direct_children, Module)
        
        self.inheritedFunctionList: Optional[ContentList] = None
        self.inheritedVariableList: Optional[ContentList] = None

        if isinstance(self.ob, Class):
            _inherited_children = self._children(inherited=True)

            self.inheritedFunctionList = self._getContentList(_inherited_children, Function)
            self.inheritedVariableList = self._getContentList(_inherited_children, Attribute)
    
    #TODO: ensure not to crash if heterogeneous Documentable types are passed

    def _getContentList(self, children: Sequence[Documentable], type_: Type[Documentable]) -> Optional['ContentList']:
        # We use the filter and iterators (instead of lists) for performance reasons.
        
        things = peek_iter(filter(lambda o: isinstance(o, type_,), children))

        if things.has_next():
            
            assert self.loader is not None
            return ContentList(ob=self.ob, children=things, 
                    documented_ob=self.documented_ob,
                    expand=self._isExpandable(type_),
                    nested_content_loader=self.loader, 
                    template_lookup=self.template_lookup,
                    level_depth=(self._level, self._depth))
        else:
            return None
    

    def _children(self, inherited: bool = False) -> List[Documentable]:
        """
        Compute the children of this object.
        """
        if inherited:
            assert isinstance(self.ob, Class), "Use inherited=True only with Class instances"
            return sorted((o for o in util.inherited_members(self.ob) if o.isVisible),
                              key=util.objects_order)
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
        
        toc = util.DocGetter().get_toc(self.ob)

        # Only show the TOC if visiting the object page itself, in other words, the TOC do dot show up
        # in the object's parent section or any other subsections except the main one.
        if toc and self.documented_ob is self.ob:
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
        return bool(self.classList or self.functionList or self.variableList or self.subModuleList or self.inheritedFunctionList or self.inheritedVariableList)

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

    def __init__(self, ob: Documentable, 
                 children: Iterator[Documentable], documented_ob: Documentable, 
                 expand: bool, nested_content_loader: ITemplateLoader, template_lookup: TemplateLookup,
                 level_depth: Tuple[int, int]):
        super().__init__(loader=self.lookup_loader(template_lookup))
        self.ob = ob 
        self.children = children
        self.documented_ob = documented_ob

        self._expand = expand
        self._level_depth = level_depth

        self.nested_content_loader = nested_content_loader
        self.template_lookup = template_lookup
    
    @renderer
    def items(self, request: IRequest, tag: Tag) -> Iterator['ContentItem']:

        return (
            ContentItem(
                loader=TagLoader(tag),
                ob=self.ob,
                child=child,
                documented_ob=self.documented_ob,
                expand=self._expand, 
                nested_content_loader=self.nested_content_loader,
                template_lookup=self.template_lookup, 
                level_depth=self._level_depth)
            for child in self.children )
        

class ContentItem(Element):
    """
    L{ContentList} item. 
    """


    def __init__(self, loader: ITemplateLoader, ob: Documentable, child: Documentable, documented_ob: Documentable,
                 expand: bool, nested_content_loader: ITemplateLoader, 
                 template_lookup: TemplateLookup, level_depth: Tuple[int, int]):
        
        super().__init__(loader)
        self.child = child
        self.ob = ob
        self.documented_ob = documented_ob

        self._expand = expand
        self._level_depth = level_depth

        self.nested_content_loader = nested_content_loader
        self.template_lookup = template_lookup

    @renderer
    def class_(self, request: IRequest, tag: Tag) -> str:
        class_ = ''
        # We could keep same style as in the summary table. 
        # But I found it a little bit too colorful.
        if self.child.isPrivate:
            class_ += "private"
        if self.child is self.documented_ob:
            class_ += " thisobject"
        return class_

    def _contents(self) -> ObjContent:

        return ObjContent(ob=self.child, 
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
            return ExpandableItem(TagLoader(tag), self.child, self.documented_ob, nested_contents, 
                    do_not_expand=self.child is self.documented_ob or not nested_contents.has_contents)
        else:
            return ""

    @renderer
    def linkOnlyItem(self, request: IRequest, tag: Tag) -> Union[str, 'LinkOnlyItem']:
        if not self._expand:
            return LinkOnlyItem(TagLoader(tag), self.child, self.documented_ob)
        else:
            return ""

class LinkOnlyItem(Element):
    """
    Sidebar leaf item: just a link to an object.

    Used by L{ContentItem.linkOnlyItem}
    """

    def __init__(self, loader: ITemplateLoader, child: Documentable, documented_ob: Documentable):
        super().__init__(loader)
        self.child = child
        self.documented_ob = documented_ob
    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        return tags.code(epydoc2stan.taglink(self.child, self.documented_ob.page_object.url, 
                                        epydoc2stan.insert_break_points(self.child.name)))

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

    def __init__(self, loader: ITemplateLoader, child: Documentable, documented_ob: Documentable, 
                contents: ObjContent, do_not_expand: bool = False):
        super().__init__(loader, child, documented_ob)
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
