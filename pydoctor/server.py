from nevow import rend, loaders, tags, inevow
from nevow.static import File
from zope.interface import implements
from pydoctor import nevowhtml, model, epydoc2stan

def findPageClassInDict(obj, d, default="CommonPage"):
    for c in obj.__class__.__mro__:
        n = c.__name__ + 'Page'
        if n in d:
            return d[n]
    return d[default]

class PyDoctorResource(rend.ChildLookupMixin):
    implements(inevow.IResource)

    def __init__(self, system):
        self.system = system
        self.putChild('apidocs.css',
                      File(nevowhtml.sibpath(__file__, 'templates/apidocs.css')))
        self.putChild('sorttable.js',
                      File(nevowhtml.sibpath(__file__, 'templates/sorttable.js')))
        index = nevowhtml.IndexPage(self.system)
        self.putChild('', index)
        self.putChild('index.html', index)
        self.putChild('moduleIndex.html', nevowhtml.ModuleIndexPage(self.system))
        self.putChild('classIndex.html', nevowhtml.ClassIndexPage(self.system))
        self.putChild('nameIndex.html', nevowhtml.NameIndexPage(self.system))

    def pageClassForObject(self, ob):
        return findPageClassInDict(ob, nevowhtml.__dict__)

    def childFactory(self, ctx, name):
        if not name.endswith('.html'):
            return None
        name = name[0:-5]
        if name not in self.system.allobjects:
            return None
        obj = self.system.allobjects[name]
        return self.pageClassForObject(obj)(obj)

    def renderHTTP(self, ctx):
        return nevowhtml.IndexPage(self.system).renderHTTP(ctx)

class EditableDocstringsMixin(object):
    def render_docstring(self, context, data):
        return (super(EditableDocstringsMixin, self).render_docstring(context, data),
                tags.a(href="edit?ob="+self.ob.fullName())["Edit"])
    def render_functionBody(self, context, data):
        return (super(EditableDocstringsMixin, self).render_functionBody(context, data),
                tags.a(href="edit?ob="+data.fullName())["Edit"])

def recursiveSubclasses(cls):
    yield cls
    for sc in cls.__subclasses__():
        for ssc in recursiveSubclasses(sc):
            yield ssc

editPageClasses = {}

for cls in list(recursiveSubclasses(nevowhtml.CommonPage)):
    _n = cls.__name__
    editPageClasses[_n] = type(_n, (EditableDocstringsMixin, cls), {})

class EditPage(rend.Page):
    def __init__(self, system):
        self.system = system
    def render_title(self, context, data):
        return context.tag[u"Editing docstring of \N{LEFT DOUBLE QUOTATION MARK}" +
                           context.arg('ob') + u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_textarea(self, context, data):
        docstring = context.arg('docstring', None)
        if docstring is None:
            ob = self.system.allobjects[context.arg('ob')]
            if isinstance(ob, model.Package):
                ob = ob.contents['__init__']
            docstring = ob.docstring
        if docstring is None:
            docstring = ''
        return context.tag[docstring]
    def render_value(self, context, data):
        return context.arg('ob')
    def render_url(self, context, data):
        return 'edit?ob=' + context.arg('ob')
    def render_preview(self, context, data):
        docstring = context.arg('docstring', None)
        ob = self.system.allobjects[context.arg('ob')]
        if docstring is not None:
            return context.tag[epydoc2stan.doc2html(ob, docstring=docstring)]
        else:
            return ()
    def render_if_not_submit(self, context, data):
        req = context.locate(inevow.IRequest)
        fullName = context.arg('ob',)
        if fullName not in self.system.allobjects:
            return tags.html[tags.head[tags.title["Error"]],
                             tags.body[tags.p["An error  occurred."]]]
        ob = self.system.allobjects[fullName]
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        action = context.arg('action', 'Preview')
        if action in ('Submit', 'Cancel'):
            if action == 'Submit':
                # something more should be done here, of course!
                ob.docstring = context.arg('docstring', None)
            if not isinstance(ob, (model.Package, model.Module, model.Class)):
                url = ob.parent.fullName()+'.html#' + ob.name
            else:
                url = fullName+'.html'
            req.redirect(url)
            return ()
        else:
            return context.tag
    docFactory = loaders.stan(tags.html[
        tags.invisible(render=render_if_not_submit)[
        tags.head[tags.title(render=render_title),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=render_title),
                  tags.p["Be warned that this is just a plaything currently, "
                         "changes you make will be lost when the server is restarted, "
                         "which is likely to be frequently."],
                  tags.div(render=render_preview)[tags.h2["Preview"]],
                  tags.form(action=render_url, method="post")
                  [tags.input(name="fullName", type="hidden", value=render_value),
                   tags.textarea(rows=40, cols=90, name="docstring", render=render_textarea),
                   tags.br(),
                   tags.input(name='action', type="submit", value="Submit"),
                   tags.input(name='action', type="submit", value="Preview"),
                   tags.input(name='action', type="submit", value="Cancel")]]]])

class EditingPyDoctorResource(PyDoctorResource):
    def __init__(self, system):
        PyDoctorResource.__init__(self, system)
        self.putChild('edit', EditPage(system))
    def pageClassForObject(self, ob):
        return findPageClassInDict(ob, editPageClasses)

def resourceForPickleFile(pickleFilePath, configFilePath=None):
    import cPickle
    system = cPickle.load(open(pickleFilePath, 'rb'))
    from pydoctor.driver import getparser, readConfigFile
    if configFilePath is not None:
        system.options, _ = getparser().parse_args(['-c', configFilePath])
        readConfigFile(system.options)
    else:
        system.options, _ = getparser().parse_args([])
    return EditingPyDoctorResource(system)
