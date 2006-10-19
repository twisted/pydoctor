from nevow import rend, loaders, tags, inevow
from nevow.static import File
from zope.interface import implements
from pydoctor import nevowhtml, model

class PyDoctorResource(rend.ChildLookupMixin):
    implements(inevow.IResource)

    def __init__(self, system):
        self.system = system
        self.putChild('apidocs.css', File(nevowhtml.sibpath(__file__, 'templates/apidocs.css')))
        self.putChild('sorttable.js', File(nevowhtml.sibpath(__file__, 'templates/sorttable.js')))
        index = nevowhtml.IndexPage(None, self.system)
        self.putChild('', index)
        self.putChild('index.html', index)
        self.putChild('moduleIndex.html', nevowhtml.ModuleIndexPage(None, self.system))
        self.putChild('classIndex.html', nevowhtml.ClassIndexPage(None, self.system))
        self.putChild('nameIndex.html', nevowhtml.NameIndexPage(None, self.system))
        self.putChild('edit', EditPage(system))
        self.putChild('write', WritePage(system))

    def childFactory(self, ctx, name):
        if not name.endswith('.html'):
            return None
        name = name[0:-5]
        if name not in self.system.allobjects:
            return None
        obj = self.system.allobjects[name]
        d = nevowhtml.__dict__
        for c in obj.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in d:
                pclass = d[n]
                break
        else:
            pclass = nevowhtml.CommonPage
        return pclass(None, obj)

    def renderHTTP(self, ctx):
        return nevowhtml.IndexPage(None, self.system).renderHTTP(ctx)

class EditPage(rend.Page):
    def __init__(self, system):
        self.system = system
    def render_title(self, context, data):
        obname = context.arg('ob', '')
        return context.tag[u"Editing docstring of \N{LEFT DOUBLE QUOTATION MARK}" + obname + u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_textarea(self, context, data):
        obname = context.arg('ob', '')
        if obname not in self.system.allobjects:
            return context.tag
        else:
            docstring = self.system.allobjects[obname].docstring
            if docstring is None:
                docstring = ''
            return context.tag[docstring]
    def render_value(self, context, data):
        return context.arg('ob', '')
    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=render_title),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=render_title),
                  tags.form(action="write", method="post")
                  [tags.input(name="fullName", type="hidden", value=render_value),
                   tags.textarea(rows=40, cols=90, name="docstring", render=render_textarea),
                   tags.br(),
                   tags.input(type="submit", value="Submit")]]])

class WritePage(rend.Page):
    def __init__(self, system):
        self.system = system
    def render_title(self, context, data):
        obname = context.arg('ob', '')
        return context.tag[u"Writing docstring of \N{LEFT DOUBLE QUOTATION MARK}" + obname +
                           u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_link(self, context, data):
        req = context.locate(inevow.IRequest)
        fullName = req.fields.getvalue('fullName', '')
        ob = self.system.allobjects.get(fullName)
        docstring = req.fields.getvalue('docstring', '')
        if ob:
            if isinstance(ob, model.Package):
                ob.contents['__init__'].docstring = docstring
            else:
                ob.docstring = docstring
            if not isinstance(ob, (model.Package, model.Module, model.Class)):
                url = ob.parent.fullName()+'.html#' + ob.name
            else:
                url = fullName+'.html'
            req.redirect(url)
            return tags.a(href=url)
        else:
            return ()
    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=render_title),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=render_title),
                  tags.p["Thank you for your attention.  Now go ",
                         tags.invisible(render=render_link), "."]]])

def resourceForPickleFile(pickleFilePath, configFilePath=None):
    import cPickle
    system = cPickle.load(open(pickleFilePath, 'rb'))
    from pydoctor.driver import getparser, readConfigFile
    if configFilePath is not None:
        system.options, _ = getparser().parse_args(['-c', configFilePath])
        readConfigFile(system.options)
    else:
        system.options, _ = getparser().parse_args([])
    system.options.addeditlinks = True
    return PyDoctorResource(system)
