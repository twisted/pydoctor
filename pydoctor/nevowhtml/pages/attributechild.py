
from nevow import loaders, page

from pydoctor.nevowhtml import util

class AttributeChild(page.Element):

    docFactory = loaders.xmlfile(util.templatefile('attribute-child.html'))

    def __init__(self, docgetter, ob):
        self.docgetter = docgetter
        self.ob = ob

    @page.renderer
    def functionAnchor(self, tag, request):
        return self.ob.fullName()

    @page.renderer
    def shortFunctionAnchor(self, tag, request):
        return self.ob.name

    @page.renderer
    def attribute(self, tag, request):
        return self.ob.name

    @page.renderer
    def functionBody(self, tag, request):
        return self.docgetter.get(self.ob)
