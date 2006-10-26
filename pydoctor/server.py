from nevow import rend, loaders, tags, inevow, url
from nevow.static import File
from zope.interface import implements
from pydoctor import nevowhtml, model, epydoc2stan

import time

def findPageClassInDict(obj, d, default="CommonPage"):
    for c in obj.__class__.__mro__:
        n = c.__name__ + 'Page'
        if n in d:
            return d[n]
    return d[default]

class HateTheWorld(rend.Page):
    def render_foo(self, context, data):
        import pprint
        req = inevow.IRequest(context)
        #print repr(pprint.pformat(req.received_headers)), req.received_headers
        return context.tag[pprint.pformat(req.received_headers)]
    docFactory = loaders.stan(tags.html[tags.body[tags.pre(render=render_foo)]])

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
        self.putChild('debug', HateTheWorld())

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

def stanForOb(ob):
    origob = ob
    if isinstance(ob, model.Package):
        ob = ob.contents['__init__']
    r = [epydoc2stan.doc2html(ob),
         tags.a(href="edit?ob="+origob.fullName())["Edit"],
         " "]
    if hasattr(ob, 'olddocstrings'):
        r.append(tags.a(href="history?ob="+origob.fullName())["View docstring history (",
                                                              len(docstrings(ob)),
                                                              " versions)"])
    else:
        r.append(tags.span(class_='undocumented')["No edits yet."])
    return r

class EditableDocstringsMixin(object):
    def render_docstring(self, context, data):
        return stanForOb(self.ob)
    def render_functionBody(self, context, data):
        return stanForOb(data)

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
            return [tags.head[tags.title["Error"]],
                    tags.body[tags.p["An error  occurred."]]]
        ob = self.system.allobjects[fullName]
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        action = context.arg('action', 'Preview')
        if action in ('Submit', 'Cancel'):
            if action == 'Submit':
                if not hasattr(ob, 'olddocstrings'):
                    ob.olddocstrings = []
                ob.olddocstrings.append((ob.docstring,
                                         getattr(ob, 'edittime', 'Dawn of time')))
                ob.docstring = context.arg('docstring', None)
                ob.edittime = time.strftime("%Y-%m-%d %H:%M:%S")
            if not isinstance(ob, (model.Package, model.Module, model.Class)):
                target = ob.parent.fullName()+'.html#' + ob.name
            else:
                target = fullName+'.html'
            req.redirect(str(url.URL.fromContext(context).sibling(target)))
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

def docstrings(ob):
    return getattr(ob, 'olddocstrings', []) + \
           [(ob.docstring, getattr(ob, 'edittime', 'Dawn of Time'))]

class HistoryPage(rend.Page):
    def __init__(self, system):
        self.system = system
    def render_title(self, context, data):
        return context.tag[u"History of \N{LEFT DOUBLE QUOTATION MARK}" +
                           context.arg('ob') +
                           u"\N{RIGHT DOUBLE QUOTATION MARK}s docstring"]
    def render_links(self, context, data):
        rev = int(context.arg('rev', '-1'))
        ob = self.system.allobjects[context.arg('ob')]
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        ds = docstrings(ob)
        therange = range(len(ds))
        rev = therange[rev]
        r = []
        for i in therange:
            if i == len(ds) - 1:
                label = "Latest"
            else:
                label = str(i)
            if i == rev:
                r.append(label)
            else:
                r.append(tags.a(href=url.gethere.replace('rev', str(i)))[label])
            r.append(' - ' + ds[i][1])
            r.append(' / ')
        del r[-1]
        return context.tag[r]
    def render_docstring(self, context, data):
        rev = int(context.arg('rev', '-1'))
        ob = self.system.allobjects[context.arg('ob')]
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        docstring = docstrings(ob)[rev][0]
        if docstring is None:
            docstring = ''
        return epydoc2stan.doc2html(ob, docstring=docstring)
    def render_check(self, context, data):
        try:
            rev = int(context.arg('rev', '-1'))
        except ValueError:
            return self.errorDocument
        try:
            ob = self.system.allobjects[context.arg('ob')]
        except KeyError:
            return self.errorDocument
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        try:
            docstrings(ob)[rev]
        except IndexError:
            return self.errorDocument
        return context.tag
    def render_linkback(self, context, data):
        ob = self.system.allobjects[context.arg('ob')]
        if not isinstance(ob, (model.Package, model.Module, model.Class)):
            url = ob.parent.fullName()+'.html#' + ob.name
        else:
            url = ob.fullName()+'.html'
        return context.tag[tags.a(href=url)["Back"]]
    docFactory = loaders.stan(tags.html[
        tags.invisible(render=render_check)[
        tags.head[tags.title(render=render_title),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=render_title),
                  tags.p(render=render_links),
                  tags.div(render=render_docstring),
                  tags.p(render=render_linkback)]]])
    errorDocument = [tags.head[tags.title["Error"]],
                     tags.body[tags.p["An error  occurred."]]]


class EditingPyDoctorResource(PyDoctorResource):
    def __init__(self, system):
        PyDoctorResource.__init__(self, system)
        self.putChild('edit', EditPage(system))
        self.putChild('history', HistoryPage(system))
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
