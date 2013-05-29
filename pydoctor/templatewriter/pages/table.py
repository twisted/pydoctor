
from twisted.web.template import Element, renderer, TagLoader, tags, XMLFile

from pydoctor.templatewriter import util

class TableRow(Element):

    def __init__(self, loader, docgetter, has_lineno_col, ob, child):
        Element.__init__(self, loader)
        self.docgetter = docgetter
        self.has_lineno_col = has_lineno_col
        self.ob = ob
        self.child = child

    @renderer
    def class_(self, request, tag):
        class_ = self.child.css_class
        if self.child.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @renderer
    def lineno(self, request, tag):
        if not self.has_lineno_col:
            return ()
        if hasattr(self.child, 'linenumber'):
            line = self.child.linenumber
            if self.child.sourceHref:
                line = tags.a(href=self.child.sourceHref)(line)
            return tag.clear()(line)
        else:
            return ()

    @renderer
    def kind(self, request, tag):
        return tag.clear()(self.child.kind)

    @renderer
    def name(self, request, tag):
        return tag.clear()(util.taglink(self.child, self.child.name))

    @renderer
    def summaryDoc(self, request, tag):
        return tag.clear()(self.docgetter.get(self.child, summary=True))


class ChildTable(Element):

    loader = XMLFile(util.templatefile('table.html'))

    last_id = 0
    def __init__(self, docgetter, ob, has_lineno_col, children):
        self.docgetter = docgetter
        self.system = ob.system
        self.has_lineno_col = has_lineno_col
        self.children = children
        ChildTable.last_id += 1
        self._id = ChildTable.last_id
        self.ob = ob

    @renderer
    def id(self, request, tag):
        return 'id'+str(self._id)

    @renderer
    def header(self, request, tag):
        if self.system.options.htmlusesorttable:
            return tag
        else:
            return ()

    @renderer
    def linenohead(self, request, tag):
        if self.has_lineno_col:
            return tag
        else:
            return ()

    @renderer
    def rows(self, request, tag):
        return [
            TableRow(
                TagLoader(tag),
                self.docgetter,
                self.has_lineno_col,
                self.ob,
                child)
            for child in self.children]
