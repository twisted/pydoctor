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

class PyDoctorResource(rend.ChildLookupMixin):
    implements(inevow.IResource)

    def __init__(self, system):
        self.system = system
        self.putChild('apidocs.css',
                      File(nevowhtml.sibpath(__file__, 'templates/apidocs.css')))
        self.putChild('sorttable.js',
                      File(nevowhtml.sibpath(__file__, 'templates/sorttable.js')))
        index = self.indexPage()
        self.putChild('', index)
        self.putChild('index.html', index)
        self.putChild('moduleIndex.html', nevowhtml.ModuleIndexPage(self.system))
        self.putChild('classIndex.html', nevowhtml.ClassIndexPage(self.system))
        self.putChild('nameIndex.html', nevowhtml.NameIndexPage(self.system))

    def indexPage(self):
        return nevowhtml.IndexPage(self.system)

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

class IndexPage(nevowhtml.IndexPage):
    def render_recentChanges(self, context, data):
        return context.tag

class RecentChangesPage(nevowhtml.CommonPage):
    docFactory = loaders.stan(tags.html[
        tags.head[tags.title["Recent Changes"],
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1["Recent Changes"]]])

def stanForOb(ob):
    origob = ob
    if isinstance(ob, model.Package):
        ob = ob.contents['__init__']
    r = [epydoc2stan.doc2html(ob),
         tags.a(href="edit?ob="+origob.fullName())["Edit"],
         " "]
    if hasattr(ob, 'edits'):
        r.append(tags.a(href="history?ob="+origob.fullName())["View docstring history (",
                                                              len(ob.edits),
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

def userIP(req):
    # obviously this is at least slightly a guess.
    xff = req.received_headers.get('x-forwarded-for')
    if xff:
        return xff
    else:
        return req.getClientIP()

class ErrorPage(rend.Page):
    docFactory = loaders.stan(tags.html[
        tags.head[tags.title["Error"]],
        tags.body[tags.p["An error  occurred."]]])


class EditPage(rend.Page):
    def __init__(self, system, root):
        self.system = system
        self.root = root

    def render_title(self, context, data):
        return context.tag[u"Editing docstring of \N{LEFT DOUBLE QUOTATION MARK}" +
                           self.fullName + u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_textarea(self, context, data):
        docstring = context.arg('docstring', self.ob.docstring)
        if docstring is None:
            docstring = ''
        return context.tag[docstring]
    def render_value(self, context, data):
        return self.fullName
    def render_url(self, context, data):
        return 'edit?ob=' + self.fullName
    def render_preview(self, context, data):
        docstring = context.arg('docstring', None)
        if docstring is not None:
            return context.tag[epydoc2stan.doc2html(
                self.system.allobjects[self.fullName], docstring=docstring)]
        else:
            return ()

    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=tags.directive('title')),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=tags.directive('title')),
                  tags.p["Be warned that this is just a plaything currently, "
                         "changes you make will be lost when the server is restarted, "
                         "which is likely to be frequently."],
                  tags.div(render=tags.directive('preview'))[tags.h2["Preview"]],
                  tags.form(action=tags.directive('url'), method="post")
                  [tags.input(name="fullName", type="hidden", value=tags.directive('value')),
                   tags.textarea(rows=40, cols=90, name="docstring",
                                 render=tags.directive('textarea')),
                   tags.br(),
                   tags.input(name='action', type="submit", value="Submit"),
                   tags.input(name='action', type="submit", value="Preview"),
                   tags.input(name='action', type="submit", value="Cancel")]]])

    def renderHTTP(self, ctx):
        self.fullName = ctx.arg('ob')
        if self.fullName not in self.system.allobjects:
            return ErrorPage()
        self.origob = self.ob = self.system.allobjects[self.fullName]
        if isinstance(self.ob, model.Package):
            self.ob = self.ob.contents['__init__']
        req = ctx.locate(inevow.IRequest)
        action = ctx.arg('action', 'Preview')
        if action in ('Submit', 'Cancel'):
            ob = self.ob
            if action == 'Submit':
                if not hasattr(ob, 'edits'):
                    ob.edits = [Edit(ob, ob.docstring, 'no-one', 'Dawn of time')]
                newDocstring = ctx.arg('docstring', None)
                edit = Edit(ob, newDocstring, userIP(req), time.strftime("%Y-%m-%d %H:%M:%S"))
                ob.docstring = newDocstring
                ob.edits.append(edit)
                self.root.changes.append(edit)
            if not isinstance(ob, (model.Package, model.Module, model.Class)):
                child = self.origob.parent.fullName() + '.html'
                frag = ob.name
            else:
                child = self.fullName + '.html'
                frag = None
            req.redirect(str(url.URL.fromContext(ctx).sibling(child).anchor(frag)))
            return ''
        return super(EditPage, self).renderHTTP(ctx)

def edits(ob):
    return getattr(ob, 'edits', [])

class HistoryPage(rend.Page):
    def __init__(self, system):
        self.system = system

    def render_title(self, context, data):
        return context.tag[u"History of \N{LEFT DOUBLE QUOTATION MARK}" +
                           self.fullName +
                           u"\N{RIGHT DOUBLE QUOTATION MARK}s docstring"]
    def render_links(self, context, data):
        ds = edits(self.ob)
        therange = range(len(ds))
        rev = therange[self.rev]
        ul = tags.ul()
        for i in therange:
            li = tags.li()
            if i == len(ds) - 1:
                label = "Latest"
            else:
                label = str(i)
            if i == rev:
                li[label]
            else:
                li[tags.a(href=url.gethere.replace('rev', str(i)))[label]]
            li[' - ' + ds[i].user + '/' + ds[i].time]
            ul[li]
        return context.tag[ul]
    def render_docstring(self, context, data):
        docstring = edits(self.ob)[self.rev].newDocstring
        if docstring is None:
            docstring = ''
        return epydoc2stan.doc2html(
            self.system.allobjects[self.fullName], docstring=docstring)
    def render_linkback(self, context, data):
        ob = self.system.allobjects[self.fullName]
        if not isinstance(ob, (model.Package, model.Module, model.Class)):
            url = ob.parent.fullName()+'.html#' + ob.name
        else:
            url = ob.fullName()+'.html'
        return context.tag[tags.a(href=url)["Back"]]

    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=tags.directive('title')),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=tags.directive('title')),
                  tags.p(render=tags.directive('links')),
                  tags.div(render=tags.directive('docstring')),
                  tags.p(render=tags.directive('linkback'))]])

    def renderHTTP(self, context):
        try:
            self.rev = int(context.arg('rev', '-1'))
        except ValueError:
            return ErrorPage()
        self.fullName = context.arg('ob')
        try:
            self.ob = self.system.allobjects[self.fullName]
        except KeyError:
            return ErrorPage()
        if isinstance(self.ob, model.Package):
            self.ob = self.ob.contents['__init__']
        try:
            edits(self.ob)[self.rev]
        except IndexError:
            return ErrorPage()
        return super(HistoryPage, self).renderHTTP(context)


class Edit(object):
    def __init__(self, obj, newDocstring, user, time):
        self.obj = obj
        self.newDocstring = newDocstring
        self.user = user
        self.time = time

class DiffPage(rend.Page):
    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=tags.directive("title")),
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1(render=tags.directive("title"))]])


class EditingPyDoctorResource(PyDoctorResource):
    def __init__(self, system):
        PyDoctorResource.__init__(self, system)
        self.putChild('edit', EditPage(system, self))
        self.putChild('history', HistoryPage(system))
        self.putChild('recentChanges', RecentChangesPage(self))
        self.putChild('diff', DiffPage())
        self.changes = []
    def pageClassForObject(self, ob):
        return findPageClassInDict(ob, editPageClasses)
    def indexPage(self):
        return IndexPage(self.system)

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
