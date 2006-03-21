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
        pclass = None
        if isinstance(ob, model.Package):
            pclass = PackagePage
        else:
            pclass = CommonPage
        page = pclass(self, ob)
        f = open(os.path.join(self.base, link(ob)), 'w')
        print f, ob
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
        tag = context.tag()
        tag.clear()
        s = (u"API docs for \N{LEFT DOUBLE QUOTATION MARK}%s"
             u"\N{RIGHT DOUBLE QUOTATION MARK}")
        return tag[s%(self.ob.fullName(),)]
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
    
        

class PackagePage(CommonPage):
    def render_docstring(self, context, data):
        return tags.raw(html.doc2html(self.ob,
                                      self.ob.contents['__init__'].docstring))
        
        
