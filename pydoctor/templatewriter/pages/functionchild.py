from typing import TYPE_CHECKING, List

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import Tag, renderer

from pydoctor.model import Function
from pydoctor.epydoc2stan import get_docstring
from pydoctor.templatewriter import TemplateElement, util
from pydoctor.templatewriter.pages import format_decorators, format_function_def, format_overloads

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


class FunctionChild(TemplateElement):

    filename = 'function-child.html'

    def __init__(self,
            docgetter: util.DocGetter,
            ob: Function,
            extras: List[Tag],
            loader: ITemplateLoader,
            silent_undoc:bool=False,
            ):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self._functionExtras = extras
        self._silent_undoc = silent_undoc

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
    def overloads(self, request: object, tag: Tag) -> "Flattenable":
        return list(format_overloads(self.ob))

    @renderer
    def decorator(self, request: object, tag: Tag) -> "Flattenable":
        return list(format_decorators(self.ob))

    @renderer
    def functionDef(self, request: object, tag: Tag) -> "Flattenable":
        return format_function_def(self.ob.name, self.ob.is_async, self.ob)

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
        # Default behaviour
        if not self._silent_undoc:
            return self.docgetter.get(self.ob)
        
        # If the function is not documented, do not even show 'Undocumented'
        doc, _ = get_docstring(self.ob)
        if doc:
            return self.docgetter.get(self.ob)
        else:
            return ()
