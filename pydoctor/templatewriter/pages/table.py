from twisted.web.template import Element, TagLoader, XMLFile, renderer, tags

from pydoctor import epydoc2stan
from pydoctor.model import Function
from pydoctor.templatewriter import util


class TableRow(Element):

    def __init__(self, loader, docgetter, ob, child):
        Element.__init__(self, loader)
        self.docgetter = docgetter
        self.ob = ob
        self.child = child

    @renderer
    def class_(self, request, tag):
        class_ = self.child.css_class
        if self.child.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @renderer
    def kind(self, request, tag):
        child = self.child
        kind = child.kind
        if isinstance(child, Function) and child.is_async:
            # The official name is "coroutine function", but that is both
            # a bit long and not as widely recognized.
            kind = f'Async {kind}'
        return tag.clear()(kind)

    @renderer
    def name(self, request, tag):
        return tag.clear()(tags.code(
            epydoc2stan.taglink(self.child, self.ob.url, self.child.name)
            ))

    @renderer
    def summaryDoc(self, request, tag):
        return tag.clear()(self.docgetter.get(self.child, summary=True))


class ChildTable(Element):
    loader = XMLFile(util.templatefilepath('table.html'))
    last_id = 0

    def __init__(self, docgetter, ob, children):
        self.docgetter = docgetter
        self.system = ob.system
        self.children = children
        ChildTable.last_id += 1
        self._id = ChildTable.last_id
        self.ob = ob

    @renderer
    def id(self, request, tag):
        return 'id'+str(self._id)

    @renderer
    def rows(self, request, tag):
        return [
            TableRow(
                TagLoader(tag),
                self.docgetter,
                self.ob,
                child)
            for child in self.children]
