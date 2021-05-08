from typing import TYPE_CHECKING, List, Optional

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import Tag, renderer, tags

from pydoctor.model import Attribute
from pydoctor.templatewriter import TemplateElement, util
from pydoctor.templatewriter.pages import DocGetter, format_decorators

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


class AttributeChild(TemplateElement):

    filename = 'attribute-child.html'

    def __init__(self,
            docgetter: DocGetter,
            ob: Attribute,
            extras: "Flattenable",
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
    def shortFunctionAnchor(self, request: object, tag: Tag) -> "Flattenable":
        return self.ob.name

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
    def functionExtras(self, request: object, tag: Tag) -> "Flattenable":
        return self._functionExtras

    @renderer
    def functionBody(self, request: object, tag: Tag) -> "Flattenable":
        return self.docgetter.get(self.ob)

    @renderer
    def functionDeprecated(self, request: object, tag: Tag) -> "Flattenable":
        msg = self.ob._deprecated_info
        if msg is None:
            return ()
        else:
            return tags.div(msg, role="alert", class_="deprecationNotice alert alert-warning")
