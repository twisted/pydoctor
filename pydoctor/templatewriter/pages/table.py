from typing import TYPE_CHECKING, Collection, Optional, Tuple, Union

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import Element, Tag, TagLoader, renderer, tags

from pydoctor import epydoc2stan
from pydoctor.model import Documentable, Function, Class
from pydoctor.templatewriter import TemplateElement, util

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


class TableRow(Element):

    def __init__(self,
            loader: ITemplateLoader,
            docgetter: util.DocGetter,
            ob: Documentable,
            child: Documentable,
            as_name:Optional[str]
            ):
        super().__init__(loader)
        self.docgetter = docgetter
        self.ob = ob
        self.child = child
        self.as_name = as_name

    @renderer
    def class_(self, request: object, tag: Tag) -> "Flattenable":
        class_ = util.css_class(self.child)
        if isinstance(self.ob, Class) and self.child.parent is not self.ob:
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
            epydoc2stan.taglink(self.child, self.ob.url, 
                                epydoc2stan.insert_break_points(
                                    self.as_name or self.child.name))))

    @renderer
    def summaryDoc(self, request: object, tag: Tag) -> Tag:
        return tag.clear()(self.docgetter.get(self.child, summary=True))


class ChildTable(TemplateElement):

    last_id = 0

    filename = 'table.html'

    def __init__(self,
            docgetter: util.DocGetter,
            ob: Documentable,
            children: Collection[Union[Documentable, Tuple[str, Documentable]]],
            loader: ITemplateLoader,
            ):
        super().__init__(loader)
        self.children = children
        ChildTable.last_id += 1
        self._id = ChildTable.last_id
        self.ob = ob
        self.docgetter = docgetter

    @renderer
    def id(self, request: object, tag: Tag) -> str:
        return f'id{self._id}'

    @renderer
    def rows(self, request: object, tag: Tag) -> "Flattenable":
        return [
            TableRow(
                TagLoader(tag),
                self.docgetter,
                self.ob,
                child=child if isinstance(child, Documentable) else child[1],
                as_name=None if isinstance(child, Documentable) else child[0])
            for child in self.children
                if (child if isinstance(child, Documentable) else child[1]).isVisible
                ]
