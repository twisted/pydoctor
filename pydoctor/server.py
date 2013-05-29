"""A web application that dynamically generates pydoctor documentation."""

from nevow import rend, loaders, url
from twisted.web.static import File
from twisted.web import resource
from twisted.web.template import Element, renderElement, renderer, XMLFile, XMLString, tags
from pydoctor import model, epydoc2stan
from pydoctor.templatewriter import DOCTYPE, pages, summary, util
from pydoctor.astbuilder import MyTransformer
import parser

import time

def parse_str(s):
    """Parse the string literal into a L{str_with_orig} that has the literal form as an attribute."""
    t = parser.suite(s.strip()).totuple(1)
    return MyTransformer().get_docstring(t)


def findPageClassInDict(obj, d, default="CommonPage"):
    for c in obj.__class__.__mro__:
        n = c.__name__ + 'Page'
        if n in d:
            return d[n]
    return d[default]

class WrapperPage(resource.Resource):
    def __init__(self, element):
        self.element = element
    def render_GET(self, request):
        request.write(DOCTYPE)
        return renderElement(request, self.element)

class PyDoctorResource(resource.Resource):

    docgetter = None

    def __init__(self, system):
        resource.Resource.__init__(self)
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

    def getChild(self, name, request):
        if not name.endswith('.html'):
            return None
        name = name[0:-5]
        if name not in self.system.allobjects:
            return None
        obj = self.system.allobjects[name]
        return WrapperPage(self.pageClassForObject(obj)(obj, self.docgetter))


class IndexPage(summary.IndexPage):

    @renderer
    def recentChanges(self, request, tag):
        return tag

    @renderer
    def problemObjects(self, request, tag):
        if self.system.epytextproblems:
            return tag
        else:
            return ()

class RecentChangesPage(Element):

    def __init__(self, root, url):
        self.root = root
        self.url = url

    @renderer
    def changes(self, request, tag):
        r = []
        for d in reversed(self.root._edits):
            r.append(
                tag.clone().fillSlots(
                    diff=self.diff(d),
                    hist=self.hist(d),
                    object=util.taglink(d.obj),
                    time=d.time,
                    user=d.user))
        return r

    def diff(self, data):
        return tags.a(href=self.url.sibling(
            'diff').add(
            'ob', data.obj.fullName()).add(
            'revA', data.rev-1).add(
            'revB', data.rev))("(diff)")

    def hist(self, data):
        return tags.a(href=self.url.sibling(
            'history').add(
            'ob', data.obj.fullName()).add(
            'rev', data.rev))("(hist)")

    loader = XMLString('''\
    <html xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
    <head>
    <title>Recent Changes</title>
    <link rel="stylesheet" type="text/css" href="apidocs.css" />
    </head>
    <body>
    <h1>Recent Changes</h1>
    <p>See <a href="bigDiff">a diff containing all changes made online</a></p>
    <ul>
    <li t:render="changes">
    <t:slot name="diff" /> - <t:slot name="hist" /> - <t:slot name="object" />
    - <t:slot name="time" /> - <t:slot name="user" /> 
    </li>
    </ul>
    </body>
    </html>
    ''')

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

class ErrorElement(Element):
    loader = XMLString("<html><head><title>Error</title></head><body><p>An error occurred.</p></body></html>")

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
        from nevow import tags
        docstring = parse_str(self.docstring)
        stan, errors = epydoc2stan.doc2stan(
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
                    tag(tags.pre(class_=cls)("%*s"%(w, i), ' ', line))
                    for err in line2err.get(i, []):
                        tag(tags.p(class_="errormessage")(err.descr()))
                i += 1
                for err in line2err.get(i, []):
                    tag(tags.p(class_="errormessage")(err.descr()))
                items = []
                for err in line2err.get(None, []):
                    items.append(tags.li(str(err)))
                if items:
                    tag(tags.ul(items))
            else:
                tag = context.tag[stan]
            return tag(tags.h2("Edit"))
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

class HistoryElement(Element):
    def __init__(self, root, ob, rev):
        self.root = root
        self.ob = ob
        self.rev = rev

    @renderer
    def title(self, request, tag):
        return tag(u"History of \N{LEFT DOUBLE QUOTATION MARK}" +
                   self.ob.fullName() +
                   u"\N{RIGHT DOUBLE QUOTATION MARK}s docstring")

    @renderer
    def links(self, request, tag):
        ds = self.root.edits(self.ob)
        therange = range(len(ds))
        rev = therange[self.rev]
        ul = tags.ul()
        for i in therange:
            li = tags.li()
            if i:
                li(tags.a(href=url.URL.fromRequest(request).sibling(
                    'diff').add(
                    'ob', self.ob.fullName()).add(
                    'revA', i-1).add(
                    'revB', i))("(diff)"))
            else:
                li("(diff)")
            li(" - ")
            if i == len(ds) - 1:
                label = "Latest"
            else:
                label = str(i)
            if i == rev:
                li(label)
            else:
                li(tags.a(href=url.gethere.replace('rev', str(i)))(label))
            li(' - ' + ds[i].user + '/' + ds[i].time)
            ul(li)
        return tag(ul)

    @renderer
    def docstring(self, request, tag):
        docstring = self.root.edits(self.ob)[self.rev].newDocstring
        if docstring is None:
            docstring = ''
        return epydoc2stan.doc2stan(self.ob, docstring=docstring)[0]

    @renderer
    def linkback(self, context, data):
        return util.taglink(self.ob, label="Back")

    loader = XMLString('''\
    <html xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
    <head>
    <title t:render="title" />
    <link rel="stylesheet" type="text/css" href="apidocs.css" />
    </head>
    <body>
    <h1 t:render="title"/>
    <p t:render="links" />
    <div t:render="docstring" />
    <p t:render="linkback" />
    </body>
    </html>
    ''')


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
            if editA.obj.linenumber:
                lineno = editA.obj.linenumber + 0
            else:
                lineno = 0
            origlines = []
        else:
            origlines = editA.newDocstring.orig.splitlines()
            lineno = editA.newDocstring.linenumber - len(origlines)
        firstdocline = lineno
        lastdocline = firstdocline + len(origlines)
        if editB.newDocstring:
            newlines = editB.newDocstring.orig.splitlines()
            newlines[0] = indentationAmount(editB.obj)*' ' + newlines[0]
            if lineno == 0 and self.lines and self.lines[0].strip() != '':
                newlines.append('')
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


class DiffElement(Element):
    def __init__(self, root, ob, origob, editA, editB):
        self.root = root
        self.ob = ob
        self.origob = origob
        self.editA = editA
        self.editB = editB

    @renderer
    def title(self, context, data):
        return context.tag["Viewing differences between revisions ",
                           self.editA.rev, " and ", self.editB.rev, " of ",
                           u"\N{LEFT DOUBLE QUOTATION MARK}" +
                           self.origob.fullName() +
                           u"\N{RIGHT DOUBLE QUOTATION MARK}"]

    @renderer
    def diff(self, context, data):
        fd = FileDiff(self.ob.parentMod)
        fd.apply_edit(self.root.editsbyob[self.ob][0], self.editA)
        fd.reset()
        fd.apply_edit(self.editA, self.editB)
        return tags.pre(fd.diff())

    loader = XMLFile(util.templatefile('diff.html'))

class BigDiffElement(Element):
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
            r.append(tags.pre(mods[mod].diff()))
        return r

    loader = XMLFile(util.templatefile('bigDiff.html'))

class RawBigDiffPage(resource.Resource):
    def __init__(self, system, root):
        self.system = system
        self.root = root

    def render_GET(self, request):
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
        for mod in sorted(mods, key=lambda x:x.filepath):
            request.write(mods[mod].diff())
        return ''

class ProblemObjectsElement(Element):

    def __init__(self, system):
        self.system = system

    @renderer
    def problemObjects(self, request, tag):
        r = []
        for fn in sorted(self.system.epytextproblems):
            o = self.system.allobjects[fn]
            r.append(tag.clone().fillSlots('link', util.taglink(o)))
        return r

    loader = XMLFile(util.templatefile('problemObjects.html'))

def absoluteURL(request, ob):
    if ob.documentation_location == model.DocLocation.PARENT_PAGE:
        p = ob.parent
        if isinstance(p, model.Module) and p.name == '__init__':
            p = p.parent
        child = p.fullName() + '.html'
        frag = ob.name
    elif ob.documentation_location == model.DocLocation.OWN_PAGE:
        child = ob.fullName() + '.html'
        frag = None
    else:
        raise AssertionError("XXX")
    return str(url.URL.fromContext(request).clear().sibling(child).anchor(frag))

class EditingPyDoctorResource(PyDoctorResource):
    def __init__(self, system):
        PyDoctorResource.__init__(self, system)
        self._edits = []
        self.editsbyob = {}
        self.editsbymod = {}
        self.docgetter = EditableDocGetter(self)

    def indexPage(self):
        return IndexPage(self.system)

    def getChild(self, name, request):
        meth = getattr(self, 'child_' + name, None)
        if meth:
            return meth(request)
        return PyDoctorResource.getChild(self, name, request)
    
    def child_recentChanges(self, ctx):
        return WrapperPage(RecentChangesPage(self, url.URL.fromContext(ctx)))

    def child_edit(self, request):
        ob = self.system.allobjects.get(request.args.get('ob', [None])[0])
        if ob is None:
            return WrapperPage(ErrorElement())
        newDocstring = request.args.get('docstring', [None])[0]
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
            initialWhitespace = request.args['initialWhitespace'][0]
        action = request.args.get('action', ['Preview'])[0]
        if action in ('Submit', 'Cancel'):
            if action == 'Submit':
                if newDocstring:
                    newDocstring = indent(newDocstring, initialWhitespace)
                self.newDocstring(userIP(request), ob, newDocstring)
            request.redirect(absoluteURL(request, ob))
            return ''
        return EditPage(self, ob, newDocstring, isPreview, initialWhitespace)

    def child_history(self, request):
        try:
            rev = int(request.args.get('rev', ['-1'])[0])
        except ValueError:
            return WrapperPage(ErrorElement())
        try:
            ob = request.args['ob'][0]
            ob = self.system.allobjects[ob]
        except KeyError:
            raise
            return WrapperPage(ErrorElement())
        try:
            self.edits(ob)[rev]
        except (IndexError, KeyError):
            raise
            return WrapperPage(ErrorElement())
        return WrapperPage(HistoryElement(self, ob, rev))

    def child_diff(self, ctx):
        origob = ob = self.system.allobjects.get(ctx.arg('ob'))
        if ob is None:
            return WrapperPage(ErrorElement())
        if isinstance(ob, model.Package):
            ob = ob.contents['__init__']
        try:
            revA = int(ctx.arg('revA', ''))
            revB = int(ctx.arg('revB', ''))
        except ValueError:
            return WrapperPage(ErrorElement())
        try:
            edits = self.editsbyob[ob]
        except KeyError:
            return WrapperPage(ErrorElement())
        try:
            editA = edits[revA]
            editB = edits[revB]
        except IndexError:
            return WrapperPage(ErrorElement())
        return WrapperPage(DiffElement(self, ob, origob, editA, editB))

    def child_bigDiff(self, ctx):
        return WrapperPage(BigDiffElement(self.system, self))

    def child_rawBigDiff(self, ctx):
        return RawBigDiffPage(self.system, self)

    def child_problemObjects(self, ctx):
        return WrapperPage(ProblemObjectsElement(self.system))

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
            return epydoc2stan.doc2stan(
                ob.doctarget, summary=True,
                docstring=current_docstring)[0]
        r = [tags.div(epydoc2stan.doc2stan(ob.doctarget,
                                           docstring=current_docstring)[0]),
             tags.a(href="edit?ob="+ob.fullName())("Edit"),
             " "]
        if ob.doctarget in self.editsbyob:
            r.append(tags.a(href="history?ob="+ob.fullName())(
                "View docstring history (",
                str(len(self.editsbyob[ob.doctarget])),
                " versions)"))
        else:
            r.append(tags.span(class_='undocumented')("No edits yet."))
        return r
