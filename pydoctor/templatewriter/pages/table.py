from typing import Collection

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import (
    Element, Flattenable, Tag, TagLoader, renderer, tags
)

from pydoctor import epydoc2stan
from pydoctor.model import Documentable, Function
from pydoctor.templatewriter import util
from pydoctor.templatewriter.pages import DocGetter, TemplateElement


class TableRow(Element):

    def __init__(self,
            loader: ITemplateLoader,
            docgetter: DocGetter,
            ob: Documentable,
            child: Documentable,
            ):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self.child = child

    @renderer
    def class_(self, request: object, tag: Tag) -> Flattenable:
        class_ = util.css_class(self.child)
        if self.child.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @renderer
    def kind(self, request: object, tag: Tag) -> Tag:
        child = self.child
        kind = child.kind
        assert kind is not None  # 'kind is None' makes the object invisible
        kind_name = epydoc2stan.format_kind(kind)
        if isinstance(child, Function) and child.is_async:
            # The official name is "coroutine function", but that is both
            # a bit long and not as widely recognized.
            kind_name = f'Async {kind_name}'
        return tag.clear()(kind_name)

    @renderer
    def name(self, request: object, tag: Tag) -> Tag:
        return tag.clear()(tags.code(
            epydoc2stan.taglink(self.child, self.ob.url, self.child.name)
            ))

    @renderer
    def summaryDoc(self, request: object, tag: Tag) -> Tag:
        return tag.clear()(self.docgetter.get(self.child, summary=True))


class ChildTable(TemplateElement):
    last_id = 0

    filename = 'table.html'

    def __init__(self,
            docgetter: DocGetter,
            ob: Documentable,
            children: Collection[Documentable],
            loader: ITemplateLoader,
            ):
        super().__init__(loader)
        self.docgetter = docgetter
        self.children = children
        ChildTable.last_id += 1
        self._id = ChildTable.last_id
        self.ob = ob

    @renderer
    def id(self, request: object, tag: Tag) -> str:
        return f'id{self._id}'

    @renderer
    def rows(self, request: object, tag: Tag) -> Flattenable:
        return [
            TableRow(
                TagLoader(tag),
                self.docgetter,
                self.ob,
                child)
            for child in self.children
            if child.isVisible
            ]
