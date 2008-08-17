
from nevow import loaders, page, tags

from pydoctor.nevowhtml import util

class TableRow(page.Element):
    docFactory = loaders.xmlfile(util.templatefile('table.html'), 'row')

    def __init__(self, docgetter, has_lineno_col, ob, child):
        self.docgetter = docgetter
        self.has_lineno_col = has_lineno_col
        self.ob = ob
        self.child = child

    @page.renderer
    def class_(self, request, tag):
        class_ = self.child.css_class
        if self.child.parent is not self.ob:
            class_ = 'base' + class_
        return class_

    @page.renderer
    def lineno(self, request, tag):
        if not self.has_lineno_col:
            return ()
        if hasattr(self.child, 'linenumber'):
            line = self.child.linenumber
            if self.child.sourceHref:
                line = tags.a(href=self.child.sourceHref)[line]
            return tag.clear()[line]
        else:
            return ()

    @page.renderer
    def kind(self, request, tag):
        return tag.clear()[self.child.kind]

    @page.renderer
    def name(self, request, tag):
        return tag.clear()[util.taglink(self.child, self.child.name)]

    @page.renderer
    def summaryDoc(self, request, tag):
        return tag.clear()[self.docgetter.get(self.child, summary=True)]


class ChildTable(page.Element):
    docFactory = loaders.xmlfile(util.templatefile('table.html'))
    last_id = 0
    def __init__(self, docgetter, ob, has_lineno_col, children):
        self.docgetter = docgetter
        self.system = ob.system
        self.has_lineno_col = has_lineno_col
        self.children = children
        ChildTable.last_id += 1
        self._id = ChildTable.last_id
        self.ob = ob

    @page.renderer
    def id(self, request, tag):
        return 'id'+str(self._id)

    @page.renderer
    def header(self, request, tag):
        if self.system.options.htmlusesorttable:
            return tag
        else:
            return ()

    @page.renderer
    def linenohead(self, request, tag):
        if self.has_lineno_col:
            return tag
        else:
            return ()

    @page.renderer
    def rows(self, request, tag):
        return [TableRow(self.docgetter, self.has_lineno_col, self.ob, child)
                for child in self.children]
