from pydoctor import model

from nevow import rend, loaders, tags

import os, shutil, inspect

try:
    from epydoc.markup import epytext
    EPYTEXT = True
except:
    print "no epytext found"
    EPYTEXT = False

def link(o):
    return o.fullName()+'.html'

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

def boringDocstring(doc):
    """Generate an HTML representation of a docstring in a really boring
    way."""
    # inspect.getdoc requires an object with a __doc__ attribute, not
    # just a string :-(
    if doc is None or not doc.strip():
        return '<pre class="undocumented">Undocumented</pre>'
    def crappit(): pass
    crappit.__doc__ = doc
    return tags.pre[inspect.getdoc(crappit)]

class _EpydocLinker(object):
    def __init__(self, obj):
        self.obj = obj
    def translate_indexterm(self, something):
        # X{foobar} is meant to put foobar in an index page (like, a
        # proper end-of-the-book index). Should we support that? There
        # are like 2 uses in Twisted.
        return something.to_html(self)
    def translate_identifier_xref(self, fullID, prettyID):
        obj = self.obj.resolveDottedName(fullID)
        if obj is None:
            return prettyID
        else:
            return '<a href="%s">%s</a>'%(link(obj), prettyID)

def doc2html(obj, doc=None):
    """Generate an HTML representation of a docstring"""
    if doc is None:
        doc = obj.docstring
    if doc is None or not doc.strip():
        return tags.div(class_="undocumented")["Undocumented"]
    if not EPYTEXT:
        return boringDocstring(doc)
    errs = []
    pdoc = epytext.parse_docstring(doc, errs)
    if errs:
        errs = []
        def crappit(): pass
        crappit.__doc__ = doc
        doc = inspect.getdoc(crappit)
        pdoc = epytext.parse_docstring(doc, errs)
        if errs:
##             if obj.system.verbosity > 0:
##                 print obj
##             if obj.system.verbosity > 1:
##                 for i, l in enumerate(doc.splitlines()):
##                     print "%4s"%(i+1), l
##                 for err in errs:
##                     print err
##             global errcount
##             errcount += len(errs)
            return boringDocstring(doc)
    pdoc, fields = pdoc.split_fields()
    crap = pdoc.to_html(_EpydocLinker(obj))
    s = tags.div()[tags.raw(crap)]
    parameter_descs = []
    returns = None
    rtype = None
    authors = []
    raises = []
    ivars = []
    cvars = []
    vars = []
    unattached_types = {}
    see = []
    note = []
    for field in fields:
        body = tags.raw(field.body().to_html(_EpydocLinker(obj)))
        if field.tag() in ('param', 'arg'):
            parameter_descs.append([field.arg(), body, None])
        elif field.tag() in ('ivar',):
            ivars.append([field.arg(), body, None])
            if field.arg() in unattached_types:
                ivars[-1][2] = unattached_types[field.arg()]
                del unattached_types[field.arg()]
        elif field.tag() in ('cvar',):
            cvars.append([field.arg(), body, None])
            if field.arg() in unattached_types:
                cvars[-1][2] = unattached_types[field.arg()]
                del unattached_types[field.arg()]
        elif field.tag() in ('var',):
            vars.append([field.arg(), body, None])
        elif field.tag() in ('type',):
            if isinstance(obj, model.Function):
                if parameter_descs and parameter_descs[-1][0] == field.arg():
                    assert parameter_descs[-1][2] is None
                    parameter_descs[-1][2] = body
                else:
                    parameter_descs.append([field.arg(), None, body])
            elif isinstance(obj, model.Class):
                if ivars and ivars[-1][0] == field.arg():
                    assert ivars[-1][2] is None
                    ivars[-1][2] = body
                elif cvars and cvars[-1][0] == field.arg():
                    assert cvars[-1][2] is None
                    cvars[-1][2] = body
                else:
                    unattached_types[field.arg()] = body
            else:
                if vars and vars[-1][0] == field.arg():
                    assert vars[-1][2] is None
                    vars[-1][2] = body
                else:
                    vars.append([field.arg(), None, body])
        elif field.tag() in ('return', 'returns'):
            returns = body
        elif field.tag() in ('returntype', 'rtype'):
            rtype = body
        elif field.tag() in ('raises', 'raise'):
            raises.append((field.arg(), body))
        elif field.tag() in ('see', 'seealso'):
            see.append(body)
        elif field.tag() in ('note',):
            note.append(body)
        elif field.tag() in ('author'):
            authors.append(body)
        else:
            s[tags.div(class_="metadata")
              [tags.span(class_="tag")[field.tag()],
               ' ',
               tags.span(class_="arg")[str(field.arg())],
               tags.span(class_="body")[body]]]
    for label, descs in [('Parameters:', parameter_descs),
                         ('Instance Variables', ivars),
                         ('Class Variables', cvars),
                         ('Variables', vars)]:
        if descs:
            b = tags.dl()
            for param, desc, t in descs:
                if desc is None:
                    desc = ''
                if t is not None:
                    b[tags.dt[param], tags.dd[desc, '(type: ',  t, ')']]
                else:
                    b[tags.dt[param], tags.dd[desc]]
            s[tags.p[label], tags.blockquote[b]]
    if returns or rtype:
        if not returns:
            returns = ''
        if rtype:
            rtype = '(type: ',  rtype, ')'
        else:
            rtype = ''
        s[tags.p['Returns:'], tags.blockquote[returns, rtype]]
    if raises:
        dl = tags.dl()
        for e, b in raises:
            dl[tags.dt[e], tags.dd[b]]
        s[tags.p['Raises:'], tags.blockquote[dl]]
    if note:
        s[tags.p['Note'], tags.blockquote[note]]        
    for fname, fname_plural, descs in [('Author', 'Authors', authors),
                                       ('See also:', 'See also:', see)]:
        if descs:
            if len(descs) > 1:
                t = tags.ul()
                for thing in descs:
                    t[tags.li[thing]]
                fname = fname_plural
            else:
                t = descs[0]
            s[tags.p[fname], tags.blockquote[t]]        
    return s

def summaryDoc(obj):
    """Generate a one-line summary of a docstring."""
    if isinstance(obj, model.Package):
        obj = obj.contents['__init__']
    doc = obj.docstring
    if not doc or not doc.strip():
        return tags.span(class_="undocumented")["Undocumented"]
    # Return the first line of the docstring (that actually has stuff)
    for doc in doc.splitlines():
        if doc.strip():
            return doc2html(obj, doc)

def getBetterThanArgspec(argspec):
    """Ok, maybe argspec's format isn't the best after all: This takes an
    argspec and returns (regularArguments, [(kwarg, kwval), (kwarg, kwval)])."""
    args = argspec[0]
    defaults = argspec[-1]
    if not defaults:
        return (args, [])
    backargs = args[:]
    backargs.reverse()
    defaults = list(defaults)
    defaults.reverse()
    kws = zip(backargs, defaults)
    kws.reverse()
    allargs = args[:-len(kws)] + kws
    return (args[:-len(kws)], kws)

def _strtup(tup):
    # Ugh
    if not isinstance(tup, (tuple, list)):
        return str(tup)
    return '(' + ', '.join(map(_strtup, tup)) + ')'

def signature(argspec):
    """Return a nicely-formatted source-like signature, formatted from an
    argspec.
    """
    regargs, kwargs = getBetterThanArgspec(argspec)
    varargname, varkwname = argspec[1:3]
    things = []
    for regarg in regargs:
        if isinstance(regarg, list):
            things.append(_strtup(regarg))
        else:
            things.append(regarg)
    if varargname:
        things.append('*%s' % varargname)
    things += ['%s=%s' % (t[0], t[1]) for t in kwargs]
    if varkwname:
        things.append('**%s' % varkwname)
    return ', '.join(things)

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
        return doc2html(self.ob)

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
        return tag[summaryDoc(data)]

    def data_methods(self, context, data):
        return []


class PackagePage(CommonPage):
    def render_docstring(self, context, data):
        return doc2html(self.ob,
                        self.ob.contents['__init__'].docstring)

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
        return tag[data.name, '(', signature(data.argspec), '):']

    def render_functionAnchor(self, context, data):
        return data.fullName()

    def render_functionBody(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[doc2html(data)]

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
        return tag[summaryDoc(docsource)]

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
        docsource = data
        if imeth:
            tag[tags.div(class_="interfaceinfo")
                ['from ', tags.a(href=link(imeth.parent) + '#' + imeth.fullName())
                 [imeth.parent.fullName()]]]
            if docsource.docstring is None:
                docsource = imeth
        for b in allbases(self.ob):
            if data.name not in b.contents:
                continue
            overridden = b.contents[data.name]
            tag[tags.div(class_="interfaceinfo")
                ['overrides ',
                 tags.a(href=link(overridden.parent) + '#' + overridden.fullName())
                 [overridden.fullName()]]]
            if docsource.docstring is None:
                docsource = overridden
            break
        ocs = list(overriding_subclasses(self.ob, data.name))
        if ocs:
            def one(sc):
                return tags.a(
                    href=link(sc) + '#' + sc.contents[data.name].fullName()
                    )[sc.fullName()]
            t = tags.div(class_="interfaceinfo")['overridden in ']
            t[one(ocs[0])]
            for sc in ocs[1:]:
                t[', ', one(sc)]
            tag[t]
        tag[doc2html(docsource)]
        return tag

def allbases(c):
    for b in c.baseobjects:
        if b is None:
            continue
        yield b
        for b2 in allbases(b):
            yield b2

def overriding_subclasses(c, name, firstcall=True):
    if not firstcall and name in c.contents:
        yield c
    else:
        for sc in c.subclasses:
            for sc2 in overriding_subclasses(sc, name, False):
                yield sc2

class FunctionPage(CommonPage):
    def render_heading(self, context, data):
        tag = super(FunctionPage, self).render_heading(context, data)
        return tag['(', signature(self.ob.argspec), '):']
