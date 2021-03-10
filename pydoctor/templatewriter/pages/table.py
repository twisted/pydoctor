
from typing import Iterable
from twisted.web.iweb import IRequest, ITemplateLoader
from twisted.web.template import TagLoader, renderer, tags, Tag, Element

from pydoctor import epydoc2stan
from pydoctor.model import Function, Documentable
from pydoctor.templatewriter import util, TemplateElement


class TableRow(Element):

    def __init__(self, loader: ITemplateLoader, docgetter: util.DocGetter, 
                 ob: Documentable, child: Documentable):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self.child = child

    @renderer
    def class_(self, request: IRequest, tag: Tag) -> str:
        class_ = self.child.css_class
        if self.child.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @renderer
    def kind(self, request: IRequest, tag: Tag) -> Tag:
        child = self.child
        kind = child.kind
        if isinstance(child, Function) and child.is_async:
            # The official name is "coroutine function", but that is both
            # a bit long and not as widely recognized.
            kind = f'Async {kind}'
        
        # mypy gets error: Returning Any from function declared to return "Tag"
        return tag.clear()(kind) # type: ignore[no-any-return]

    @renderer
    def name(self, request: IRequest, tag: Tag) -> Tag:
        # mypy gets error: Returning Any from function declared to return "Tag"
        return tag.clear()(tags.code( # type: ignore[no-any-return]
            epydoc2stan.taglink(self.child, self.ob.url, self.child.name)
            ))

    @renderer
    def summaryDoc(self, request: IRequest, tag: Tag) -> Tag:
        # mypy gets error: Returning Any from function declared to return "Tag"
        return tag.clear()(self.docgetter.get(self.child, summary=True)) # type: ignore[no-any-return]

class ChildTable(TemplateElement):

    last_id = 0

    filename = 'table.html'

    def __init__(self, docgetter: util.DocGetter, ob: Documentable, 
                 children: Iterable[Documentable], loader: ITemplateLoader):
        super().__init__(loader)
        self.children = children
        ChildTable.last_id += 1
        self._id = ChildTable.last_id
        self.ob = ob
        self.docgetter = docgetter

    @renderer
    def id(self, request: IRequest, tag: Tag) -> str:
        return 'id'+str(self._id)

    @renderer
    def rows(self, request: IRequest, tag: Tag) -> Iterable[Element]:
        return [
            TableRow(
                loader=TagLoader(tag),
                ob=self.ob,
                child=child, 
                docgetter=self.docgetter)
            for child in self.children]
