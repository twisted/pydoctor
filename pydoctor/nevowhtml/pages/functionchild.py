
from nevow import loaders, page, tags

from pydoctor import ast_pp
from pydoctor.nevowhtml import util
from pydoctor.nevowhtml.pages import signature

class FunctionChild(page.Element):

    docFactory = loaders.xmlfile(util.templatefile('function-child.html'))

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

    @page.renderer
    def functionName(self, request, tag):
        return [self.ob.name, '(', signature(self.ob.argspec), '):']

    @page.renderer
    def sourceLink(self, request, tag):
        if self.ob.sourceHref:
            return tag.fillSlots('sourceHref', self.ob.sourceHref)
        else:
            return ()

    @page.renderer
    def functionExtras(self, request, tag):
        return ()

    @page.renderer
    def functionBody(self, request, tag):
        return self.docgetter.get(self.ob)
