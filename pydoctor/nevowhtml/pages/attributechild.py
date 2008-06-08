
from nevow import loaders, page

from pydoctor.nevowhtml import util

class AttributeChild(page.Element):

    docFactory = loaders.xmlfile(util.templatefile('attribute-child.html'))

    def __init__(self, docgetter, ob):
        self.docgetter = docgetter
        self.ob = ob

    @page.renderer
    def functionAnchor(self, request, tag):
        return self.ob.fullName()

    @page.renderer
    def shortFunctionAnchor(self, request, tag):
        return self.ob.name

    @page.renderer
    def attribute(self, request, tag):
        return self.ob.name

    @page.renderer
    def functionBody(self, request, tag):
        return self.docgetter.get(self.ob)
