"""A web application that dynamically generates pydoctor documentation."""

from nevow import rend, loaders, tags, inevow, url, page
from nevow.static import File
from zope.interface import implements
from pydoctor import model, epydoc2stan
from pydoctor.nevowhtml import pages, summary, util
from pydoctor.astbuilder import MyTransformer
import parser

import time

def parse_str(s):
    """Parse the string literal into a `mystr` that has the literal form as an attribute."""
    t = parser.suite(s.strip()).totuple(1)
    return MyTransformer().get_docstring(t)


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

    docgetter = None

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
        return WrapperPage(self.pageClassForObject(obj)(obj, self.docgetter))

    def renderHTTP(self, ctx):
        return self.index.renderHTTP(ctx)

class IndexPage(summary.IndexPage):
    @page.renderer
    def recentChanges(self, request, tag):
        return tag
    @page.renderer
    def problemObjects(self, request, tag):
        if self.system.epytextproblems:
            return tag
        else:
            return ()

class RecentChangesPage(page.Element):
    def __init__(self, root, url):
        self.root = root
        self.url = url

    @page.renderer
    def changes(self, request, tag):
        item = tag.patternGenerator('item')
        for d in reversed(self.root._edits):
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
                  tags.link(rel="stylesheet", type="text/css",
                            href='apidocs.css')],
        tags.body[tags.h1["Recent Changes"],
                  tags.p["See ", tags.a(href="bigDiff")
                         ["a diff containing all changes made online"]],
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

class EditableDocGetter(object):
    def __init__(self, root):
        self.root = root

    def get(self, ob, summary=False):
        return self.root.stanForOb(ob, summary=summary)

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

def indentationAmount(ob):
    ob = ob.doctarget
    if isinstance(ob, model.Module):
        return 0
    lines = open(ob.doctarget.parentMod.filepath, 'rU').readlines()
    if ob.docstring is None:
        line = lines[ob.linenumber-1]
        return len(line) - len(line.lstrip()) + 4
    else:
        docstring_line_count = len(ob.docstring.orig.splitlines())
        firstline = lines[ob.docstring.linenumber - docstring_line_count]
        return len(firstline) - len(firstline.lstrip())

def indent(ds, data):
    lines = ds.splitlines()
    r = [lines[0]]
    for line in lines[1:]:
        if line.strip():
            line = data + line
        r.append(line)
    return '\n'.join(r)

def dedent(ds):
    lines = ds.splitlines()
    for line in lines[1:]:
        if line.strip():
            break
    else:
        return ds, None
    initialWhitespace = line[:len(line) - len(line.lstrip())]
    r = [lines[0]]
    for line in lines[1:]:
        if line.startswith(initialWhitespace):
            line = line[len(initialWhitespace):]
        r.append(line)
    return '\n'.join(r), initialWhitespace

class EditPage(rend.Page):
    def __init__(self, root, ob, docstring, isPreview, initialWhitespace):
        self.root = root
        self.ob = ob
        self.lines = open(
            self.ob.doctarget.parentMod.filepath, 'rU').readlines()
        self.docstring = docstring
        self.isPreview = isPreview
        self.initialWhitespace = initialWhitespace

    def render_title(self, context, data):
        return context.tag.clear()[
            u"Editing docstring of \N{LEFT DOUBLE QUOTATION MARK}",
            self.ob.fullName(),
            u"\N{RIGHT DOUBLE QUOTATION MARK}"]
    def render_preview(self, context, data):
        docstring = parse_str(self.docstring)
        stan, errors = epydoc2stan.doc2html(
            self.ob, docstring=docstring)
        if self.isPreview or errors:
            if errors:
                tag = context.tag
                #print stan, errors
                #assert isinstance(stan, tags.pre)
                [text] = stan.children
                lines = text.replace('\r\n', '\n').split('\n')
                line2err = {}
                for err in errors:
                    if isinstance(err, str):
                        ln = None
                    else:
                        ln = err.linenum()
                    line2err.setdefault(ln, []).append(err)
                w = len(str(len(lines)))
                for i, line in enumerate(lines):
                    i += 1
                    cls = "preview"
                    if i in line2err:
                        cls += " error"
                    tag[tags.pre(class_=cls)["%*s"%(w, i), ' ', line]]
                    for err in line2err.get(i, []):
                        tag[tags.p(class_="errormessage")[err.descr()]]
                i += 1
                for err in line2err.get(i, []):
                    tag[tags.p(class_="errormessage")[err.descr()]]
                items = []
                for err in line2err.get(None, []):
                    items.append(tags.li[str(err)])
                if items:
                    tag[tags.ul[items]]
            else:
                tag = context.tag[stan]
            return tag[tags.h2["Edit"]]
        else:
            return ()
    def render_fullName(self, context, data):
        return self.ob.fullName()
    def render_initialWhitespace(self, context, data):
        return self.initialWhitespace
    def render_before(self, context, data):
        tob = self.ob.doctarget
        if tob.docstring:
            docstring_line_count = len(tob.docstring.orig.splitlines())
            lineno = tob.docstring.linenumber - docstring_line_count
        else:
            lineno = tob.linenumber
        firstlineno = max(0, lineno-6)
        lines = self.lines[firstlineno:lineno]
        if not lines:
            return ()
        if firstlineno > 0:
            lines.insert(0, '...\n')
        return context.tag[lines]
    def render_divIndent(self, context, data):
        return 'margin-left: %dex;'%(indentationAmount(self.ob),)
    def render_rows(self, context, data):
        return len(self.docstring.splitlines()) + 1
    def render_textarea(self, context, data):
        return context.tag.clear()[self.docstring]
    def render_after(self, context, data):
        tob = self.ob.doctarget
        if tob.docstring:
            lineno = tob.docstring.linenumber
        else:
            lineno = tob.linenumber
        lastlineno = lineno + 6
        lines = self.lines[lineno:lastlineno]
        if not lines:
            return ()
        if lastlineno < len(self.lines):
            lines.append('...\n')
        return context.tag[lines]
    def render_url(self, context, data):
        return 'edit?ob=' + self.ob.fullName()

    docFactory = loaders.xmlfile(util.templatefile("edit.html"))

class HistoryPage(rend.Page):
    def __init__(self, root, ob, rev):
        self.root = root
        self.ob = ob
        self.rev = rev

    def render_title(self, context, data):
        return context.tag[u"History of \N{LEFT DOUBLE QUOTATION MARK}" +
                           self.ob.fullName() +
                           u"\N{RIGHT DOUBLE QUOTATION MARK}s docstring"]
    def render_links(self, context, data):
        ds = self.root.edits(self.ob)
        therange = range(len(ds))
        rev = therange[self.rev]
        ul = tags.ul()
        for i in therange:
            li = tags.li()
            if i:
                li[tags.a(href=url.URL.fromContext(context).sibling(
                    'diff').add(
                    'ob', self.ob.fullName()).add(
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
        docstring = self.root.editsbyob[self.ob][self.rev].newDocstring
        if docstring is None:
            docstring = ''
        return epydoc2stan.doc2html(self.ob, docstring=docstring)[0]
    def render_linkback(self, context, data):
        return util.taglink(self.ob, label="Back")

    docFactory = loaders.stan(tags.html[
        tags.head[tags.title(render=tags.directive('title')),
                  tags.link(rel="stylesheet", type="text/css",
                            href='apidocs.css')],
        tags.body[tags.h1(render=tags.directive('title')),
                  tags.p(render=tags.directive('links')),
                  tags.div(render=tags.directive('docstring')),
                  tags.p(render=tags.directive('linkback'))]])


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

    def reset(self):
        self.orig_lines = self.lines[:]

    def apply_edit(self, editA, editB):
        if not editA.newDocstring:
            lineno = editA.obj.linenumber + 1
            origlines = []
        else:
            origlines = editA.newDocstring.orig.splitlines()
            lineno = editA.newDocstring.linenumber - len(origlines)
        firstdocline = lineno
        lastdocline = firstdocline + len(origlines)
        if editB.newDocstring:
            newlines = editB.newDocstring.orig.splitlines()
            newlines[0] = indentationAmount(editB.obj)*' ' + newlines[0]
        else:
            newlines = []
        self.lines[firstdocline:lastdocline] = newlines

    def diff(self):
        orig = [line + '\n' for line in self.orig_lines]
        new = [line + '\n' for line in self.lines]
        import difflib
        fpath = filepath(self.ob)
        return ''.join(difflib.unified_diff(orig, new,
                                            fromfile=fpath,
                                            tofile=fpath))


class DiffPage(rend.Page):
    def __init__(self, root, ob, origob, editA, editB):
        self.root = root
        self.ob = ob
        self.origob = origob
        self.editA = editA
        self.editB = editB

    def render_title(self, context, data):
        return context.tag["Viewing differences between revisions ",
                           self.editA.rev, " and ", self.editB.rev, " of ",
                           u"\N{LEFT DOUBLE QUOTATION MARK}" +
                           self.origob.fullName() +
                           u"\N{RIGHT DOUBLE QUOTATION MARK}"]

    def render_diff(self, context, data):
        fd = FileDiff(self.ob.parentMod)
        fd.apply_edit(self.root.editsbyob[self.ob][0], self.editA)
        fd.reset()
        fd.apply_edit(self.editA, self.editB)
        return tags.pre[fd.diff()]

    docFactory = loaders.xmlfile(util.templatefile('diff.html'))

class BigDiffPage(rend.Page):
    def __init__(self, system, root):
        self.system = system
        self.root = root

    def render_bigDiff(self, context, data):
        mods = {}
        for m in self.root.editsbymod:
            l = [e for e in self.root.editsbymod[m]
                 if e is self.root.editsbyob[e.obj.doctarget][-1]]
            l.sort(key=lambda x:x.obj.linenumber, reverse=True)
            mods[m] = FileDiff(m)
            for e in l:
                edit0 = self.root.editsbyob[e.obj][0]
                mods[m].apply_edit(edit0, e)
        r = []
        for mod in sorted(mods, key=lambda x:x.filepath):
            r.append(tags.pre[mods[mod].diff()])
        return r

    docFactory = loaders.xmlfile(util.templatefile('bigDiff.html'))

class RawBigDiffPage(rend.Page):
    def __init__(self, system, root):
        self.system = system
        self.root = root

    def renderHTTP(self, context):
        request = context.locate(inevow.IRequest)
        request.setHeader('content-type', 'text/plain')
        mods = {}
        if not self.root.editsbymod:
            return 'No edits yet!'
        for m in self.root.editsbymod:
            l = [e for e in self.root.editsbymod[m]
                 if e is self.root.editsbyob[e.obj.doctarget][-1]]
            l.sort(key=lambda x:x.obj.linenumber, reverse=True)
            mods[m] = FileDiff(m)
            for e in l:
                edit0 = self.root.editsbyob[e.obj][0]
                mods[m].apply_edit(edit0, e)
        r = []
        for mod in sorted(mods, key=lambda x:x.filepath):
            request.write(mods[mod].diff())
        return ''

class ProblemObjectsPage(rend.Page):
    def __init__(self, system):
        self.system = system
    def render_problemObjects(self, context, data):
        t = context.tag
        pat = t.patternGenerator('object')
        for fn in sorted(self.system.epytextproblems):
            o = self.system.allobjects[fn]
            t[pat.fillSlots('link', util.taglink(o))]
        return t
    docFactory = loaders.xmlfile(util.templatefile('problemObjects.html'))

def absoluteURL(ctx, ob):
    if ob.document_in_parent_page:
        p = ob.parent
        if isinstance(p, model.Module) and p.name == '__init__':
            p = p.parent
        child = p.fullName() + '.html'
        frag = ob.name
    else:
        child = ob.fullName() + '.html'
        frag = None
    return str(url.URL.fromContext(ctx).clear().sibling(child).anchor(frag))

class EditingPyDoctorResource(PyDoctorResource):
    def __init__(self, system):
        PyDoctorResource.__init__(self, system)
        self._edits = []
        self.editsbyob = {}
        self.editsbymod = {}
        self.docgetter = EditableDocGetter(self)

    def indexPage(self):
        return IndexPage(self.system)

    def child_recentChanges(self, ctx):
        return WrapperPage(RecentChangesPage(self, url.URL.fromContext(ctx)))

    def child_edit(self, ctx):
        ob = self.system.allobjects.get(ctx.arg('ob'))
        if ob is None:
            return ErrorPage()
        newDocstring = ctx.arg('docstring', None)
        if newDocstring is None:
            isPreview = False
            newDocstring = self.mostRecentEdit(ob).newDocstring
            if newDocstring is None:
                newDocstring = ''
            else:
                newDocstring = newDocstring.orig
            newDocstring, initialWhitespace = dedent(newDocstring)
            if initialWhitespace is None:
                initialWhitespace = ' '*indentationAmount(ob)
        else:
            isPreview = True
            initialWhitespace = ctx.arg('initialWhitespace')
        action = ctx.arg('action', 'Preview')
        if action in ('Submit', 'Cancel'):
            req = ctx.locate(inevow.IRequest)
            if action == 'Submit':
                if newDocstring:
                    newDocstring = indent(newDocstring, initialWhitespace)
                self.newDocstring(userIP(req), ob, newDocstring)
            req.redirect(absoluteURL(ctx, ob))
            return ''
        return EditPage(self, ob, newDocstring, isPreview, initialWhitespace)

    def child_history(self, ctx):
        try:
            rev = int(ctx.arg('rev', '-1'))
        except ValueError:
            return ErrorPage()
        try:
            ob = self.system.allobjects[ctx.arg('ob')]
        except KeyError:
            return ErrorPage()
        try:
            self.editsbyob[ob][rev]
        except (IndexError, KeyError):
            return ErrorPage()
        return HistoryPage(self, ob, rev)

    def child_diff(self, ctx):
        origob = ob = self.system.allobjects.get(ctx.arg('ob'))
        if ob is None:
            return ErrorPage()
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        try:
            revA = int(ctx.arg('revA', ''))
            revB = int(ctx.arg('revB', ''))
        except ValueError:
            return ErrorPage()
        try:
            edits = self.editsbyob[ob]
        except KeyError:
            return ErrorPage()
        try:
            editA = edits[revA]
            editB = edits[revB]
        except IndexError:
            return ErrorPage()
        return DiffPage(self, ob, origob, editA, editB)

    def child_bigDiff(self, ctx):
        return BigDiffPage(self.system, self)

    def child_rawBigDiff(self, ctx):
        return RawBigDiffPage(self.system, self)

    def child_problemObjects(self, ctx):
        return ProblemObjectsPage(self.system)

    def mostRecentEdit(self, ob):
        return self.edits(ob)[-1]

    def edits(self, ob):
        ob = ob.doctarget
        if ob not in self.editsbyob:
            self.editsbyob[ob] = [
                Edit(ob, 0, ob.docstring, 'no-one', 'Dawn of time')]
        return self.editsbyob[ob]

    def currentDocstringForObject(self, ob):
        for source in ob.docsources():
            d = self.mostRecentEdit(source).newDocstring
            if d is not None:
                return d
        return ''

    def addEdit(self, edit):
        self.editsbyob.setdefault(edit.obj.doctarget, []).append(edit)
        self.editsbymod.setdefault(
            edit.obj.doctarget.parentMod, []).append(edit)
        self._edits.append(edit)

    def newDocstring(self, user, ob, newDocstring):
        tob = ob.doctarget
        if tob.parentMod not in self.editsbymod:
            self.editsbymod[tob.parentMod] = []

        prevEdit = self.mostRecentEdit(ob)

        if not newDocstring.strip():
            newDocstring = None
        else:
            newDocstring = parse_str(newDocstring)
            newLength = len(newDocstring.orig.splitlines())
            if prevEdit.newDocstring:
                oldLength = len(prevEdit.newDocstring.orig.splitlines())
                oldNumber = prevEdit.newDocstring.linenumber
                newDocstring.linenumber = oldNumber - oldLength + newLength
            else:
                # XXX check for comments?
                newDocstring.linenumber = tob.linenumber + 1 + newLength

        edit = Edit(tob, prevEdit.rev + 1, newDocstring, user,
                    time.strftime("%Y-%m-%d %H:%M:%S"))
        self.addEdit(edit)
        if tob.fullName() in self.system.epytextproblems:
            self.system.epytextproblems.remove(tob.fullName())

    def stanForOb(self, ob, summary=False):
        current_docstring = self.currentDocstringForObject(ob)
        if summary:
            return epydoc2stan.doc2html(
                ob.doctarget, summary=True,
                docstring=current_docstring)[0]
        r = [tags.div[epydoc2stan.doc2html(ob.doctarget,
                                           docstring=current_docstring)[0]],
             tags.a(href="edit?ob="+ob.fullName())["Edit"],
             " "]
        if ob.doctarget in self.editsbyob:
            r.append(tags.a(href="history?ob="+ob.fullName())[
                "View docstring history (",
                len(self.editsbyob[ob.doctarget]),
                " versions)"])
        else:
            r.append(tags.span(class_='undocumented')["No edits yet."])
        return r


def resourceForPickleFile(pickleFilePath, configFilePath=None):
    import cPickle
    system = cPickle.load(open(pickleFilePath, 'rb'))
    from pydoctor.driver import getparser, readConfigFile
    if configFilePath is not None:
        system.options, _ = getparser().parse_args(['-c', configFilePath])
        readConfigFile(system.options)
    else:
        system.options, _ = getparser().parse_args([])
        system.options.verbosity = 3
    return EditingPyDoctorResource(system)
