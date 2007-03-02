from nevow import rend, loaders, tags, inevow, url, page
from nevow.static import File
from zope.interface import implements
from pydoctor import nevowhtml, model, epydoc2stan
from pydoctor.nevowhtml import pages, summary, util

import time

def findPageClassInDict(obj, d, default="CommonPage"):
    for c in obj.__class__.__mro__:
        n = c.__name__ + 'Page'
        if n in d:
            return d[n]
    return d[default]

class WrapperPage(rend.Page):
    def __init__(self, element):
        self.element = element
    def render_content(self, context, data):
        return self.element
    docFactory = loaders.stan(tags.directive('content'))

class PyDoctorResource(rend.ChildLookupMixin):
    implements(inevow.IResource)

    def __init__(self, system):
        self.system = system
        self.putChild('apidocs.css', File(util.templatefile('apidocs.css')))
        self.putChild('sorttable.js', File(util.templatefile('sorttable.js')))
        self.putChild('pydoctor.js', File(util.templatefile('pydoctor.js')))
        self.index = WrapperPage(self.indexPage())
        self.putChild('', self.index)
        self.putChild('index.html', self.index)
        self.putChild('moduleIndex.html',
                      WrapperPage(summary.ModuleIndexPage(self.system)))
        self.putChild('classIndex.html',
                      WrapperPage(summary.ClassIndexPage(self.system)))
        self.putChild('nameIndex.html',
                      WrapperPage(summary.NameIndexPage(self.system)))

    def indexPage(self):
        return summary.IndexPage(self.system)

    def pageClassForObject(self, ob):
        return findPageClassInDict(ob, pages.__dict__)

    def childFactory(self, ctx, name):
        if not name.endswith('.html'):
            return None
        name = name[0:-5]
        if name not in self.system.allobjects:
            return None
        obj = self.system.allobjects[name]
        return WrapperPage(self.pageClassForObject(obj)(obj))

    def renderHTTP(self, ctx):
        return self.index.renderHTTP(ctx)

class IndexPage(summary.IndexPage):
    @page.renderer
    def recentChanges(self, request, tag):
        return tag

class RecentChangesPage(page.Element):
    def __init__(self, root, url):
        self.root = root
        self.url = url

    @page.renderer
    def changes(self, request, tag):
        item = tag.patternGenerator('item')
        for d in reversed(self.root.edits):
            tag[util.fillSlots(item,
                               diff=self.diff(d),
                               hist=self.hist(d),
                               object=util.taglink(d.obj),
                               time=d.time,
                               user=d.user)]
        return tag

    def diff(self, data):
        return tags.a(href=self.url.sibling(
            'diff').add(
            'ob', data.obj.fullName()).add(
            'revA', data.rev-1).add(
            'revB', data.rev))["(diff)"]

    def hist(self, data):
        return tags.a(href=self.url.sibling(
            'history').add(
            'ob', data.obj.fullName()).add(
            'rev', data.rev))["(hist)"]

    docFactory = loaders.stan(tags.html[
        tags.head[tags.title["Recent Changes"],
                  tags.link(rel="stylesheet", type="text/css", href='apidocs.css')],
        tags.body[tags.h1["Recent Changes"],
                  tags.p["See ", tags.a(href="bigDiff")["a diff containing all changes made online"]],
                  tags.ul(render=tags.directive("changes"))
                  [tags.li(pattern="item")
                   [tags.slot("diff"),
                    " - ",
                    tags.slot("hist"),
                    " - ",
                    tags.slot("object"),
                    " - ",
                    tags.slot("time"),
                    " - ",
                    tags.slot("user"),
                    ]]]])

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
    def docstring(self):
        return stanForOb(self.ob)

    def functionBody(self, data):
        return stanForOb(data)

def recursiveSubclasses(cls):
    yield cls
    for sc in cls.__subclasses__():
        for ssc in recursiveSubclasses(sc):
            yield ssc

editPageClasses = {}

for cls in list(recursiveSubclasses(pages.CommonPage)):
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
        tags.body[tags.p["An error occurred."]]])


def origstring(ob):
    if hasattr(ob, 'docsource'):
        return None
    else:
        return ob.docstring.orig

class EditPage(rend.Page):
    def __init__(self, system, root):
        self.system = system
        self.root = root

    def render_title(self, context, data):
        return context.tag[u"Editing docstring of \N{LEFT DOUBLE QUOTATION MARK}" +
                           self.fullName + u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_textarea(self, context, data):
        docstring = context.arg('docstring', origstring(self.ob))
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
            from pydoctor.astbuilder import mystr, MyTransformer
            import parser
            docstring = MyTransformer().get_docstring(parser.suite(docstring).totuple(1))
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
                    if hasattr(ob, 'docsource'):
                        ds = None
                    else:
                        ds = ob.docstring
                    ob.edits = [Edit(self.origob, 0, ds, 'no-one', 'Dawn of time')]
                newDocstring = ctx.arg('docstring', None)
                if not newDocstring:
                    newDocstring = None
                else:
                    from pydoctor.astbuilder import mystr, MyTransformer
                    import parser
                    newDocstring = MyTransformer().get_docstring(parser.suite(newDocstring).totuple(1))
                    orig = origstring(ob)
                    if orig:
                        l = len(orig.splitlines())
                        newDocstring.linenumber = ob.docstring.linenumber - l + len(newDocstring.orig.splitlines())
                    else:
                        newDocstring.linenumber = ob.linenumber + 1
                edit = Edit(self.origob, len(ob.edits), newDocstring, userIP(req),
                            time.strftime("%Y-%m-%d %H:%M:%S"))
                ob.docstring = newDocstring
                if hasattr(ob, 'docsource') and hasattr(ob, 'computeDocsource'):
                    del ob.docsource
                    ob.computeDocsource()
                ob.edits.append(edit)
                self.root.edits.append(edit)
            if not isinstance(ob, (model.Package, model.Module, model.Class)):
                p = self.origob.parent
                if isinstance(p, model.Module) and p.name == '__init__':
                    p = p.parent
                child = p.fullName() + '.html'
                frag = ob.name
            else:
                child = self.fullName + '.html'
                frag = None
            req.redirect(str(url.URL.fromContext(ctx).clear().sibling(child).anchor(frag)))
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
            if i:
                li[tags.a(href=url.URL.fromContext(context).sibling(
                    'diff').add(
                    'ob', self.origob.fullName()).add(
                    'revA', i-1).add(
                    'revB', i))["(diff)"]]
            else:
                li["(diff)"]
            li[" - "]
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
        if ob.document_in_parent_page:
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
            self.origob = self.ob = self.system.allobjects[self.fullName]
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
    def __init__(self, obj, rev, newDocstring, user, time):
        self.obj = obj
        self.rev = rev
        self.newDocstring = newDocstring
        self.user = user
        self.time = time

def filepath(ob):
    mod = ob.parentMod
    filepath = mod.filepath
    while mod:
        top = mod
        mod = mod.parent
    toppath = top.contents['__init__'].filepath[:-(len('__init__.py') + 1 + len(top.name))]
    return filepath[len(toppath):]

class FileDiff(object):
    def __init__(self, ob):
        self.ob = ob
        self.lines = [l[:-1] for l in open(ob.filepath, 'rU').readlines()]
        self.orig_lines = self.lines[:]
        self.delta = 0

    def reset(self):
        self.orig_lines = self.lines[:]
        self.delta = 0

    def apply_edit(self, editA, editB):
        print 'apply_edit'
        if not editA.newDocstring:
            lineno = editA.obj.linenumber + 1
            origlines = []
        else:
            origlines = editA.newDocstring.orig.splitlines()
            lineno = editA.newDocstring.linenumber - len(origlines)
        firstdocline = lineno + self.delta
        lastdocline = firstdocline + len(origlines)
        if editB.newDocstring:
            newlines = editB.newDocstring.orig.splitlines()
        else:
            newlines = []
        self.lines[firstdocline:lastdocline] = newlines
        self.delta += len(origlines) - len(newlines)

    def diff(self):
        orig = [line + '\n' for line in self.orig_lines]
        new = [line + '\n' for line in self.lines]
        import difflib
        fpath = filepath(self.ob)
        return ''.join(difflib.unified_diff(orig, new,
                                            fromfile=fpath,
                                            tofile=fpath))


class DiffPage(rend.Page):
    def __init__(self, system):
        self.system = system

    def render_title(self, context, data):
        return context.tag["Viewing differences between revisions ",
                           self.editA.rev, " and ", self.editB.rev, " of ",
                           u"\N{LEFT DOUBLE QUOTATION MARK}" +
                           self.origob.fullName() + u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_diff(self, context, data):
        fd = FileDiff(self.ob.parentMod)
        fd.apply_edit(edits(self.ob)[0], self.editA)
        fd.reset()
        fd.apply_edit(self.editA, self.editB)
        return tags.pre[fd.diff()]

    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=tags.directive("title")),
                  tags.link(rel="stylesheet", type="text/css", href="apidocs.css")],
        tags.body[tags.h1(render=tags.directive("title")),
                  tags.table(render=tags.directive("diff"))]])

    def renderHTTP(self, context):
        try:
            self.origob = self.ob = self.system.allobjects[context.arg('ob')]
        except KeyError:
            return ErrorPage()
        if isinstance(self.ob, model.Package):
            self.ob = self.ob.contents['__init__']
        try:
            revA = int(context.arg('revA', ''))
            revB = int(context.arg('revB', ''))
        except ValueError:
            return ErrorPage()
        try:
            self.editA = edits(self.ob)[revA]
            self.editB = edits(self.ob)[revB]
        except IndexError:
            return ErrorPage()
        return super(DiffPage, self).renderHTTP(context)

class BigDiffPage(rend.Page):
    def __init__(self, system, root):
        self.system = system
        self.root = root

    def render_bigDiff(self, context, data):
        mods = {}
        for e in self.root.edits:
            m = e.obj.parentMod
            if m not in mods:
                mods[m] = FileDiff(m)
            i = e.obj.edits.index(e)
            mods[m].apply_edit(e.obj.edits[i-1], e.obj.edits[i])
        r = []
        for mod in sorted(mods, key=lambda x:x.filepath):
            r.append(tags.pre[mods[mod].diff()])
        return r

    docFactory = loaders.stan(tags.html[
        tags.head[tags.title["Big Diff"],
                  tags.link(rel="stylesheet", type="text/css", href="apidocs.css")],
        tags.body[tags.h1["Big Diff"],
                  tags.div(render=tags.directive("bigDiff"))]])

    def renderHTTP(self, context):
        return super(BigDiffPage, self).renderHTTP(context)


class EditingPyDoctorResource(PyDoctorResource):
    def __init__(self, system):
        PyDoctorResource.__init__(self, system)
        self.edits = []
    def pageClassForObject(self, ob):
        return findPageClassInDict(ob, editPageClasses)
    def indexPage(self):
        return IndexPage(self.system)
    def child_recentChanges(self, ctx):
        return WrapperPage(RecentChangesPage(self, url.URL.fromContext(ctx)))
    def child_edit(self, ctx):
        return EditPage(self.system, self)
    def child_history(self, ctx):
        return HistoryPage(self.system)
    def child_diff(self, ctx):
        return DiffPage(self.system)
    def child_bigDiff(self, ctx):
        return BigDiffPage(self.system, self)

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
