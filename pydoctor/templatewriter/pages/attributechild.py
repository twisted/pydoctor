
from twisted.web.template import Element, renderer, XMLFile

from pydoctor.templatewriter import util

class AttributeChild(Element):

    loader = XMLFile(util.templatefile('attribute-child.html'))

    def __init__(self, docgetter, ob):
        self.docgetter = docgetter
        self.ob = ob

    @renderer
    def functionAnchor(self, request, tag):
        return self.ob.fullName()

    @renderer
    def shortFunctionAnchor(self, request, tag):
        return self.ob.name

    @renderer
    def attribute(self, request, tag):
        return self.ob.name

    @renderer
    def functionBody(self, request, tag):
        return self.docgetter.get(self.ob)
