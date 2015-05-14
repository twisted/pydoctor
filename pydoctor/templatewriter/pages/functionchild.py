
from twisted.web.template import Element, renderer, tags, XMLFile

from pydoctor import ast_pp
from pydoctor.templatewriter import util
from pydoctor.templatewriter.pages import signature

class FunctionChild(Element):

    loader = XMLFile(util.templatefile('function-child.html'))

    def __init__(self, docgetter, ob, functionExtras):
        self.docgetter = docgetter
        self.ob = ob
        self._functionExtras = functionExtras

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
    def decorator(self, request, tag):
        if self.ob.decorators:
            decorators = [ast_pp.pp(dec) for dec in self.ob.decorators]
        else:
            decorators = []

        if self.ob.kind == "Class Method" \
               and 'classmethod' not in decorators:
            decorators.append('classmethod')
        elif self.ob.kind == "Static Method" \
                 and 'staticmethod' not in decorators:
            decorators.append('staticmethod')

        if decorators:
            decorator = [('@' + dec, tags.br()) for dec in decorators]
        else:
            decorator = ()

        return decorator

    @renderer
    def functionName(self, request, tag):
        return [self.ob.name, '(', signature(self.ob.argspec), '):']

    @renderer
    def sourceLink(self, request, tag):
        if self.ob.sourceHref:
            return tag.fillSlots(sourceHref=self.ob.sourceHref)
        else:
            return ()

    @renderer
    def functionExtras(self, request, tag):
        return self._functionExtras

    @renderer
    def functionBody(self, request, tag):
        return self.docgetter.get(self.ob)
