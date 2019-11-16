from __future__ import print_function

from pydoctor.templatewriter import util
from twisted.web.template import Element, XMLFile, renderer


class AttributeChild(Element):

    loader = XMLFile(util.templatefilepath('attribute-child.html'))

    def __init__(self, docgetter, ob):
        self.docgetter = docgetter
        self.ob = ob

    @renderer
    def class_(self, request, tag):
        class_ = self.ob.css_class
        if self.ob.parent is not self.ob:
            class_ = 'base' + class_
        return class_

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
