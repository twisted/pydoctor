from typing import TYPE_CHECKING, List

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import Tag, renderer, tags

from pydoctor.model import Function
from pydoctor.templatewriter import TemplateElement, util
from pydoctor.templatewriter.pages import format_decorators, format_signature

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


class FunctionChild(TemplateElement):

    filename = 'function-child.html'

    def __init__(self,
            docgetter: util.DocGetter,
            ob: Function,
            extras: List[Tag],
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
        return list(format_decorators(self.ob))

    @renderer
    def functionDef(self, request: object, tag: Tag) -> "Flattenable":
        def_stmt = 'async def' if self.ob.is_async else 'def'
        name = self.ob.name
        if name.endswith('.setter') or name.endswith('.deleter'):
            name = name[:name.rindex('.')]
        return [
            tags.span(def_stmt, class_='py-keyword'), ' ',
            tags.span(name, class_='py-defname'), 
            format_signature(self.ob), ':'
            ]

    @renderer
    def sourceLink(self, request: object, tag: Tag) -> "Flattenable":
        if self.ob.sourceHref:
            return tag.fillSlots(sourceHref=self.ob.sourceHref)
        else:
            return ()

    @renderer
    def objectExtras(self, request: object, tag: Tag) -> List[Tag]:
        return self._functionExtras

    @renderer
    def functionBody(self, request: object, tag: Tag) -> "Flattenable":
        return self.docgetter.get(self.ob)

