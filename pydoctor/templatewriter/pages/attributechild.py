from typing import TYPE_CHECKING, List

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import Tag, renderer, tags

from pydoctor.model import Attribute, DocumentableKind
from pydoctor import epydoc2stan
from pydoctor.templatewriter import TemplateElement, util
from pydoctor.templatewriter.pages import format_decorators

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


class AttributeChild(TemplateElement):

    filename = 'attribute-child.html'

    def __init__(self,
            docgetter: util.DocGetter,
            ob: Attribute,
            extras: List["Flattenable"],
            loader: ITemplateLoader,
            funcLoader: ITemplateLoader,
            ):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self._functionExtras = extras
        self._funcLoader = funcLoader

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
        return list(format_decorators(self.ob))

    @renderer
    def attribute(self, request: object, tag: Tag) -> "Flattenable":
        attr: List["Flattenable"] = [tags.span(self.ob.name, class_='py-defname')]
        _type = self.docgetter.get_type(self.ob)
        if _type:
            attr.extend([': ', _type])
        return attr

    @renderer
    def sourceLink(self, request: object, tag: Tag) -> "Flattenable":
        if self.ob.sourceHref:
            return tag.fillSlots(sourceHref=self.ob.sourceHref)
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
        if self.ob.kind not in self.ob.system.show_attr_value or self.ob.value is None:
            return tag.clear()
        # Attribute is a constant/type alias (with a value), then display it's value
        return epydoc2stan.format_constant_value(self.ob)

    @renderer
    def propertyInfo(self, request: object, tag: Tag) -> "Flattenable":
        # Property info consist in nested function child elements that 
        # formats the setter and deleter docs of the property.
        r = []
        if self.ob.kind is DocumentableKind.PROPERTY:
            from pydoctor.templatewriter.pages.functionchild import FunctionChild

            assert isinstance(self.ob, Attribute)
            
            for func in [f for f in (self.ob.property_def.setter, self.ob.property_def.deleter) if f]:
                r.append(FunctionChild(self.docgetter, func, extras=[], 
                            loader=self._funcLoader, silent_undoc=True))
        return r
