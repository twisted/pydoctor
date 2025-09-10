from __future__ import annotations

from typing import TYPE_CHECKING, List

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import Tag, renderer, tags

from pydoctor.model import Attribute, AttributeValueDisplay, DocumentableKind
from pydoctor import epydoc2stan
from pydoctor.templatewriter import TemplateElement, util
from pydoctor.templatewriter.pages import format_decorators, format_type_params

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


class AttributeChild(TemplateElement):

    filename = 'attribute-child.html'

    def __init__(self,
            docgetter: util.DocGetter,
            ob: Attribute,
            extras: List["Flattenable"],
            loader: ITemplateLoader
            ):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self._functionExtras = extras

    @renderer
    def class_(self, request: object, tag: Tag) -> "Flattenable":
        class_ = util.css_class(self.ob)
        if self.ob.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @renderer
    def functionAnchor(self, request: object, tag: Tag) -> "Flattenable":
        return self.ob.fullName()

    @renderer
    def shortFunctionAnchor(self, request: object, tag: Tag) -> str:
        return self.ob.name
    
    @renderer
    def anchorHref(self, request: object, tag: Tag) -> str:
        name = self.shortFunctionAnchor(request, tag)
        return f'#{name}'
    
    @renderer
    def decorator(self, request: object, tag: Tag) -> "Flattenable":
        return format_decorators(self.ob)

    @renderer
    def attribute(self, request: object, tag: Tag) -> "Flattenable":
        is_type_alias = self.ob.kind is DocumentableKind.TYPE_ALIAS
        attr: List["Flattenable"] = []
        if is_type_alias:
            attr += [tags.span('type', class_='py-keyword'), ' ',]
        attr += [tags.span(self.ob.name, class_='py-defname'), 
                 *format_type_params(self.ob)]
        _type = self.docgetter.get_type(self.ob)
        if _type and not is_type_alias:
            attr.extend([': ', _type])
        return attr

    @renderer
    def sourceLink(self, request: object, tag: Tag) -> "Flattenable":
        if self.ob.source_href:
            return tag.fillSlots(sourceHref=self.ob.source_href)
        else:
            return ()

    @renderer
    def objectExtras(self, request: object, tag: Tag) -> List["Flattenable"]:
        return self._functionExtras

    @renderer
    def functionBody(self, request: object, tag: Tag) -> "Flattenable":
        return self.docgetter.get(self.ob)

    @renderer
    def constantValue(self, request: object, tag: Tag) -> "Flattenable":
        showval = self.ob.system.showAttrValue(self.ob)
        if showval is AttributeValueDisplay.HIDDEN:
            return tag.clear()
        elif showval is AttributeValueDisplay.AS_CODE_BLOCK:
            return epydoc2stan.format_constant_value(self.ob)
        else:
            assert False
