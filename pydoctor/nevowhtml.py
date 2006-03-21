from pydoctor import model, html

from nevow import rend, loaders, tags

import os, shutil, inspect

def link(o):
    return o.fullName()+'.html'

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

class NevowWriter:
    def __init__(self, filebase):
        self.base = filebase

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(sibpath(__file__, 'templates/apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))

    def writeIndividualFiles(self, obs):
        for ob in obs:
            self.writeDocsFor(ob)

    def writeModuleIndex(self, system):
        pass

    def writeDocsFor(self, ob):
        self.writeDocsForOne(ob)
        for o in ob.orderedcontents:
            self.writeDocsFor(o)

    def writeDocsForOne(self, ob):
        # brrrrrrrr!
        for c in ob.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in globals():
                pclass = globals()[n]
                break
        else:
            pclass = CommonPage
        page = pclass(self, ob)
        f = open(os.path.join(self.base, link(ob)), 'w')
        print ob
        def _cb(text):
            f.write(text)
            f.close()
        page.renderString().addCallback(_cb)
        assert f.closed

def mediumName(obj):
    fn = obj.fullName()
    if '.' not in fn:
        return fn
    path, name = fn.rsplit('.', 1)
    return '.'.join([p[0] for p in path.split('.')]) + '.' + name

class CommonPage(rend.Page):
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/common.html'))
    def __init__(self, writer, ob):
        self.writer = writer
        self.ob = ob
    def render_title(self, context, data):
        return self.ob.fullName()
    def render_heading(self, context, data):
        tag = context.tag()
        tag.clear()
        kind = self.ob.kind
        return tag(class_=kind.lower())[kind + " " + mediumName(self.ob)]
    def render_part(self, context, data):
        tag = context.tag()
        tag.clear()
        if self.ob.parent:
            return tag['Part of ',
                       tags.a(href=link(self.ob.parent))
                       [self.ob.parent.fullName()]]
        else:
            return tag

    def render_source(self, context, data):
        tag = context.tag()
        if not self.writer.sourcebase:
            return tag.clear()
        m = self.ob
        while not isinstance(m, (model.Module, model.Package)):
            m = m.parent
            if m is None:
                return tag.clear()
        sourceHref = '%s/%s'%(self.writer.sourcebase, m.fullName().replace('.', '/'),)
        if isinstance(m, model.Module):
            sourceHref += '.py'
        if isinstance(self.ob, model.Module):
            sourceHref += '#L1'
        elif hasattr(self.ob, 'linenumber'):
            sourceHref += '#L'+str(self.ob.linenumber)
        return tag(href=sourceHref)

    def render_extras(self, context, data):
        return context.tag().clear()

    def render_docstring(self, context, data):
        return tags.raw(html.doc2html(self.ob, self.ob.docstring))

    def render_maybechildren(self, context, data):
        tag = context.tag()
        if not self.ob.orderedcontents:
            tag.clear()
        return tag

    def data_children(self, context, data):
        return self.ob.orderedcontents

    def render_childclass(self, context, data):
        return data.kind.lower()

    def render_childkind(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[data.kind]

    def render_childname(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[tags.a(href=link(data))[data.name]]

    def render_childsummaryDoc(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[tags.raw(html.summaryDoc(data))]

    def data_methods(self, context, data):
        return []


class PackagePage(CommonPage):
    def render_docstring(self, context, data):
        return tags.raw(html.doc2html(self.ob,
                                      self.ob.contents['__init__'].docstring))

    def data_children(self, context, data):
        return [o for o in self.ob.orderedcontents
                if o.name != '__init__']

def taglink(o):
    return tags.a(href=link(o))[o.fullName()]

class ClassPage(CommonPage):
    def render_extras(self, context, data):
        r = super(ClassPage, self).render_extras(context, data)
        if self.ob.subclasses:
            sc = self.ob.subclasses[0]
            p = tags.p()
            p["Known subclasses: ", taglink(sc)]
            for sc in self.ob.subclasses[1:]:
                p[', ', taglink(sc)]
            r[p]
        return r

    def render_childkind(self, context, data):
        tag = context.tag()
        tag.clear()
        if isinstance(data, model.Function):
            kind = "Method"
        else:
            kind = data.kind
        return tag[kind]

    def render_heading(self, context, data):
        tag = super(ClassPage, self).render_heading(context, data)
        zipped = zip(self.ob.rawbases, self.ob.baseobjects)
        if zipped:
            tag['(']
            for i, (n, o) in enumerate(zipped):
                if o is None:
                    tag[n]
                else:
                    tag[tags.a(href=link(o))[n]]
                if i != len(zipped)-1:
                    tag[', ']
            tag[')']
        tag[':']
        return tag

    def data_children(self, context, data):
        return [o for o in self.ob.orderedcontents
                if isinstance(o, model.Function)]
    data_methods = data_children

    def render_childname(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[tags.a(href='#' + data.fullName())[data.name]]

    def render_functionName(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[data.name, '(', html.signature(data.argspec), '):']

    def render_functionAnchor(self, context, data):
        return data.fullName()

    def render_functionBody(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[tags.raw(html.doc2html(data, data.docstring))]

class TwistedClassPage(ClassPage):
    def render_extras(self, context, data):
        r = super(TwistedClassPage, self).render_extras(context, data)
        system = self.ob.system
        def tl(s):
            if s in system.allobjects:
                return taglink(system.allobjects[s])
            else:
                return s
        if self.ob.isinterface:
            namelist = self.ob.implementedby_directly
            label = 'Known implementations: '
        else:
            namelist = self.ob.implements_directly
            label = 'Implements interfaces: '
        if namelist:
            tag = tags.p()[label, tl(namelist[0])]
            for impl in namelist[1:]:
                tag[', ', tl(impl)]
            r[tag]
        return r

    def render_childsummaryDoc(self, context, data):
        tag = context.tag()
        tag.clear()
        docsource = data
        if not docsource.docstring:
            imeth = self.interfaceMeth(data.name)
            if imeth:
                docsource = imeth
        if not docsource.docstring:
            for b in allbases(self.ob):
                if data.name not in b.contents:
                    continue
                docsource = b.contents[data.name]
                break
        return tag[tags.raw(html.summaryDoc(docsource))]

    def interfaceMeth(self, methname):
        system = self.ob.system
        for interface in self.ob.implements_directly + self.ob.implements_indirectly:
            if interface in system.allobjects:
                io = system.allobjects[interface]
                if methname in io.contents:
                    return io.contents[methname]
        return None

    def render_functionBody(self, context, data):
        imeth = self.interfaceMeth(data.name)
        tag = context.tag()
        tag.clear()
        doc2html_args = data, data.docstring
        if imeth:
            tag[tags.div(class_="interfaceinfo")
                ['from ', tags.a(href=link(imeth.parent) + '#' + imeth.fullName())
                 [imeth.parent.fullName()]]]
            if not doc2html_args[1]:
                doc2html_args = imeth, imeth.docstring
        for b in allbases(self.ob):
            if data.name not in b.contents:
                continue
            overridden = b.contents[data.name]
            tag[tags.div(class_="interfaceinfo")
                ['overrides ',
                 tags.a(href=link(overridden.parent) + '#' + overridden.fullName())
                 [overridden.fullName()]]]
            if not doc2html_args[1]:
                doc2html_args = overridden, overridden.docstring
            break
        tag[tags.raw(html.doc2html(*doc2html_args))]
        return tag

def allbases(c):
    for b in c.baseobjects:
        if b is None:
            continue
        yield b
        for b2 in allbases(b):
            yield b2

class FunctionPage(CommonPage):
    def render_heading(self, context, data):
        tag = super(FunctionPage, self).render_heading(context, data)
        return tag['(', html.signature(self.ob.argspec), '):']
