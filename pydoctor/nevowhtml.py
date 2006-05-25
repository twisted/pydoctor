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
            if isinstance(obj, model.Function):
                linktext = link(obj.parent) + '#' + obj.fullName()
            else:
                linktext = link(obj)
            return '<a href="%s">%s</a>'%(linktext, prettyID)

class FieldDesc(object):
    def __init__(self):
        self.kind = None
        self.name = None
        self.type = None
        self.body = None
    def format(self):
        if self.body is None:
            body = ''
        else:
            body = self.body
        if self.type is not None:
            body = body, '(type: ', self.type, ')'
        return body

def format_desc_list(singular, descs, plural=None):
    if plural is None:
        plural = singular + 's'
    if not descs:
        return ''
    if len(descs) > 1:
        label = plural
    else:
        label = singular
    r = []
    first = True
    for d in descs:
        if first:
            row = tags.tr(class_="fieldStart")
            row[tags.td(class_="fieldName")[label]]
            first = False
        else:
            row = tags.tr()
            row[tags.td()]
        row[tags.td(class_="fieldArg")[d.name], tags.td[d.format()]]
        r.append(row)
    return r

def format_field_list(obj, singular, fields, plural=None):
    if plural is None:
        plural = singular + 's'
    if not fields:
        return ''
    if len(fields) > 1:
        label = plural
    else:
        label = singular
    rows = []
    first = True
    for field in fields:
        if first:
            row = tags.tr(class_="fieldStart")
            row[tags.td(class_="fieldName")[label]]
            first=False
        else:
            row = tags.tr()
            row[tags.td()]
        row[tags.td(colspan=2)[field.body]]
        rows.append(row)
    return rows

class Field(object):
    """Like epydoc.markup.Field, but without the gross accessor
    methods and with a formatted body."""
    def __init__(self, field, obj):
        self.tag = field.tag()
        self.arg = field.arg()
        self.body = tags.raw(field.body().to_html(_EpydocLinker(obj)))

class FieldHandler(object):
    def __init__(self, obj):
        self.obj = obj
        
        self.parameter_descs = []
        self.ivar_descs = []
        self.cvar_descs = []
        self.var_descs = []
        self.return_desc = None
        self.raise_descs = []
        self.seealsos = []
        self.notes = []
        self.authors = []
        self.unknowns = []
        self.unattached_types = {}

    def handle_return(self, field):
        if not self.return_desc:
            self.return_desc = FieldDesc()
        if self.return_desc.body:
            print 'XXX'
        self.return_desc.body = field.body
    handle_returns = handle_return
    
    def handle_returntype(self, field):
        if not self.return_desc:
            self.return_desc = FieldDesc()
        if self.return_desc.type:
            print 'XXX'
        self.return_desc.type = field.body
    handle_rtype = handle_returntype

    def add_type_info(self, desc_list, field):
        if desc_list and desc_list[-1].name == field.arg:
            assert desc_list[-1].type is None
            desc_list[-1].type = field.body
        else:
            d = FieldDesc()
            d.kind = field.tag
            d.name = field.arg
            d.type = field.body
            desc_list.append(d)

    def add_info(self, desc_list, field):
        if desc_list and desc_list[-1].name == field.arg:
            assert desc_list[-1].body is None
            desc_list[-1].body = field.body
        else:
            d = FieldDesc()
            d.kind = field.tag
            d.name = field.arg
            d.body = field.body
            desc_list.append(d)
    
    def handle_type(self, field):
        obj = self.obj
        if isinstance(obj, model.Function):
            self.add_type_info(self.parameter_descs, field)
        elif isinstance(obj, model.Class):
            ivars = self.ivar_descs
            cvars = self.cvar_descs
            if ivars and ivars[-1].name == field.arg:
                assert ivars[-1].type is None
                ivars[-1].type = field.body
            elif cvars and cvars[-1].name == field.arg:
                assert cvars[-1].type is None
                cvars[-1].type = field.body
            else:
                self.unattached_types[field.arg] = field.body
        else:
            self.add_type_info(self.var_descs, field)

    def handle_param(self, field):
        self.add_info(self.parameter_descs, field)
    handle_arg = handle_param

    def handle_ivar(self, field):
        self.add_info(self.ivar_descs, field)
        if field.arg in self.unattached_types:
            self.ivar_descs[-1].type = self.unattached_types[field.arg]
            del self.unattached_types[field.arg]

    def handle_cvar(self, field):
        self.add_info(self.cvar_descs, field)
        if field.arg in self.unattached_types:
            self.cvar_descs[-1].type = self.unattached_types[field.arg]
            del self.unattached_types[field.arg]

    def handle_var(self, field):
        self.add_info(self.var_descs, field)

    def handle_raises(self, field):
        self.add_info(self.raise_descs, field)
    handle_raise = handle_raises
    
    def handle_seealso(self, field):
        self.seealsos.append(field)
    handle_see = handle_seealso

    def handle_note(self, field):
        self.notes.append(field)

    def handle_author(self, field):
        self.authors.append(field)

    def handleUnknownField(self, field):
        print 'XXX', 'unknown field', field
        self.unknowns.append(field)

    def handle(self, field):
        m = getattr(self, 'handle_' + field.tag, self.handleUnknownField)
        m(field)

    def format(self):
        r = []
        for d, l in (('Parameters', self.parameter_descs),
                     ('Instance Variables', self.ivar_descs),
                     ('Class Variables', self.cvar_descs),
                     ('Variables', self.var_descs)):
            r.append(format_desc_list(d, l, d))
        if self.return_desc:
            r.append(tags.tr(class_="fieldStart")[tags.td(class_="fieldName")['Returns'],
                               tags.td(colspan="2")[self.return_desc.format()]])
        r.append(format_desc_list("Raises", self.raise_descs, "Raises"))
        for s, p, l in (('Author', 'Authors', self.authors),
                        ('See Also', 'See Also', self.seealsos),
                        ('Note', 'Notes', self.notes),
                        ('Unknown Field', 'Unknown Fields', self.unknowns)):
            r.append(format_field_list(self.obj, s, l, p))
        return tags.table(class_='fieldTable')[r]

def doc2html(obj, summary=False):
    """Generate an HTML representation of a docstring"""
    if isinstance(obj, model.Package):
        obj = obj.contents['__init__']
    doc = obj.docstring
    if doc is None or not doc.strip():
        if summary:
            return tags.span(class_="undocumented")["Undocumented"]
        else:
            return tags.div(class_="undocumented")["Undocumented"]            
    if summary:
        for line in doc.split('\n'):
            if line.strip():
                doc = line
                break
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
    if summary:
        s = tags.span()[tags.raw(crap)]
    else:
        s = tags.div()[tags.raw(crap)]        
        fh = FieldHandler(obj)
        for field in fields:
            fh.handle(Field(field, obj))
        s[fh.format()]
    return s

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
    sourcebase = None
    
    def __init__(self, filebase):
        self.base = filebase

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(sibpath(__file__, 'templates/apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))

    def writeIndividualFiles(self, obs, functionpages=False):
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)

    def writeModuleIndex(self, system):
        for pclass in summarypages:
            page = pclass(self, system)
            f = open(os.path.join(self.base, pclass.filename), 'w')
            f.write(page.renderSynchronously())
            f.close()

    def writeDocsFor(self, ob, functionpages):
        isfunc = isinstance(ob, model.Function)
        if (isfunc and functionpages) or not isfunc:
            f = open(os.path.join(self.base, link(ob)), 'w')
            self.writeDocsForOne(ob, f)
            f.close()
        for o in ob.orderedcontents:
            self.writeDocsFor(o, functionpages)

    def writeDocsForOne(self, ob, fobj):
        # brrrrrrrr!
        for c in ob.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in globals():
                pclass = globals()[n]
                break
        else:
            pclass = CommonPage
        page = pclass(self, ob)
        print ob
        fobj.write(page.renderSynchronously())

def mediumName(obj):
    fn = obj.fullName()
    if '.' not in fn:
        return fn
    path, name = fn.rsplit('.', 1)
    return '.'.join([p[0] for p in path.split('.')]) + '.' + name

def moduleSummary(modorpack):
    r = [tags.li[taglink(modorpack), ' - ', doc2html(modorpack, summary=True)]]
    if isinstance(modorpack, model.Package) and len(modorpack.orderedcontents) > 1:
        ul = tags.ul()
        for m in sorted(modorpack.orderedcontents,
                        key=lambda m:m.fullName()):
            if m.name != '__init__':
                ul[moduleSummary(m)]
        r.append(ul)
    return r

class ModuleIndexPage(rend.Page):
    filename = 'moduleIndex.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/summary.html'))
    def __init__(self, writer, system):
        self.writer = writer
        self.system = system
    def render_title(self, context, data):
        return context.tag.clear()["Module Index"]
    def render_stuff(self, context, data):
        r = []
        for o in self.system.rootobjects:
            r.extend(moduleSummary(o))
        return context.tag.clear()[r]
    def render_heading(self, context, data):
        return context.tag().clear()["Module Index"]

def findRootClasses(system):
    roots = {}
    for cls in system.objectsOfType(model.Class):
        if cls.bases:
            for n, b in zip(cls.bases, cls.baseobjects):
                if b is None:
                    roots.setdefault(n, []).append(cls)
        else:
            roots[cls.fullName()] = cls
    return sorted(roots.items())

def subclassesFrom(cls):
    r = [tags.li[tags.a(name=cls.fullName()), taglink(cls), ' - ', doc2html(cls, summary=True)]]
    if len(cls.subclasses) > 0:
        ul = tags.ul()
        for sc in sorted(cls.subclasses, key=lambda sc2:sc2.fullName()):
            ul[subclassesFrom(sc)]
        r.append(ul)
    return r

class ClassIndexPage(rend.Page):
    filename = 'classIndex.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/summary.html'))
    def __init__(self, writer, system):
        self.writer = writer
        self.system = system
    def render_title(self, context, data):
        return context.tag.clear()["Class Hierarchy"]
    def render_stuff(self, context, data):
        t = context.tag
        for b, o in findRootClasses(self.system):
            if isinstance(o, model.Class):
                t[subclassesFrom(o)]
            else:
                t[tags.li[b]]
                if o:
                    ul = tags.ul()
                    for sc in sorted(o, key=lambda sc2:sc2.fullName()):
                        ul[subclassesFrom(sc)]
                    t[ul]
        return t
    def render_heading(self, context, data):
        return context.tag.clear()["Class Hierarchy"]


class NameIndexPage(rend.Page):
    filename = 'nameIndex.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/nameIndex.html'))
    def __init__(self, writer, system):
        self.writer = writer
        self.system = system
        used_initials = {}
        for ob in self.system.orderedallobjects:
            used_initials[ob.name[0].upper()] = True
        self.used_initials = sorted(used_initials)
        
    def render_title(self, context, data):
        return context.tag.clear()["Index Of Names"]
    def render_heading(self, context, data):
        return context.tag.clear()["Index Of Names"]
    def data_letters(self, context, data):
        # this is confusing
        # we return a list of lists of lists
        # if r is the return value, r[i][j] is a list of things with the same .name
        # all the things in the lists contained in r[i] share the same initial.
        initials = {}
        for ob in self.system.orderedallobjects:
            initials.setdefault(ob.name[0].upper(), {}).setdefault(ob.name, []).append(ob)
        r = []
        for k in sorted(initials):
            r.append(sorted(
                sorted(initials[k].values(), key=lambda v:v[0].name),
                key=lambda v:v[0].name.upper()))
        return r
    def render_letter(self, context, data):
        return context.tag.clear()[data[0][0].name[0].upper()]
    def render_letters(self, context, data):
        cur = data[0][0].name[0].upper()
        r = []
        for i in self.used_initials:
            if i != cur:
                r.append(tags.a(href='#' + i)[i])
            else:
                r.append(i)
            r.append(' - ')
        if r:
            del r[-1]
        return context.tag.clear()[r]
    def render_linkToThing(self, context, data):
        tag = context.tag.clear()
        if len(data) == 1:
            ob, = data
            return tag[ob.name, ' - ', taglink(ob)]
        else:
            ul = tags.ul()
            for d in sorted(data, key=lambda o:o.fullName()):
                ul[tags.li[taglink(d)]]
            return tag[data[0].name, ul]

class IndexPage(rend.Page):
    filename = 'index.html'
    docFactory = loaders.xmlfile(sibpath(__file__, 'templates/index.html'))
    def __init__(self, writer, system):
        self.system = system
    def render_project(self, context, data):
        return context.tag.clear()[self.system.options.projectname]
    def render_project(self, context, data):
        return context.tag.clear()[self.system.options.projectname]
    def render_onlyIfOneRoot(self, context, data):
        if len(self.system.rootobjects) != 1:
            return []
        else:
            root, = self.system.rootobjects
            return context.tag.clear()[
                "Start at ", taglink(root),
                ", the root ", root.kind.lower(), "."]
    def render_onlyIfMultipleRoots(self, context, data):
        if len(self.system.rootobjects) == 1:
            return []
        else:
            return context.tag.clear()

summarypages = [ModuleIndexPage, ClassIndexPage, IndexPage, NameIndexPage]


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

    def render_inhierarchy(self, context, data):
        return context.tag().clear()

    def render_extras(self, context, data):
        return context.tag().clear()

    def render_docstring(self, context, data):
        return doc2html(self.ob)

    def render_maybechildren(self, context, data):
        tag = context.tag()
        if not self.ob.orderedcontents:
            tag.clear()
        return tag

    def data_bases(self, context, data):
        return []

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
        return tag[doc2html(data, summary=True)]

    def data_methods(self, context, data):
        return []


class PackagePage(CommonPage):
    def data_children(self, context, data):
        return sorted([o for o in self.ob.orderedcontents
                       if o.name != '__init__'],
                      key=lambda o2:o2.fullName())

class FunctionParentMixin(object):
    def render_functionName(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[data.name, '(', signature(data.argspec), '):']

    def render_childname(self, context, data):
        if not isinstance(data, model.Function):
            sup = super(FunctionParentMixin, self)
            return sup.render_childname(context, data)
        tag = context.tag()
        tag.clear()
        return tag[tags.a(href='#' + data.fullName())[data.name]]

    def render_functionAnchor(self, context, data):
        return data.fullName()

    def render_functionBody(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[doc2html(data)]

class ModulePage(FunctionParentMixin, CommonPage):
    def data_methods(self, context, data):
        return [o for o in self.ob.orderedcontents
                if isinstance(o, model.Function)]


def taglink(o, label=None):
    if label is None:
        label = o.fullName()
    if isinstance(o, model.Function):
        linktext = link(o.parent) + '#' + o.fullName()
    else:
        linktext = link(o)
    return tags.a(href=linktext)[label]

class ClassPage(FunctionParentMixin, CommonPage):
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

    def render_inhierarchy(self, context, data):
        return context.tag(href="classIndex.html#"+self.ob.fullName())

    def data_children(self, context, data):
        return [o for o in self.ob.orderedcontents
                if isinstance(o, model.Function)]
    data_methods = data_children

    def nested_bases(self, b):
        r = [(b,)]
        for b2 in b.baseobjects:
            if b2 is None:
                continue
            for n in self.nested_bases(b2):
                r.append(n + (b,))
        return r

    def data_bases(self, context, data):
        r = []
        for b in self.ob.baseobjects:
            if b is None:
                continue
            r.extend(self.nested_bases(b))
        return r

    def render_base_sequence(self, context, data):
        p = context.tag.patternGenerator('item2')
        tag = context.tag.clear()
        for d in data[0].orderedcontents:
            for b in (self.ob,) + data[1:]:
                if d.name in b.contents:
                    break
            else:
                tag[p(data=d)]
        return tag

    def render_base_name(self, context, data):
        tag = context.tag.clear()
        tag[tags.a(href=link(data[0]))[data[0].name]]
        if data[1:]:
            tail = []
            for b in data[1:][::-1]:
                tail.append(tags.a(href=link(b))[b.name])
                tail.append(', ')
            del tail[-1]
            tag[' (via ', tail, ')']
        return tag

    def render_maybe_base(self, context, data):
        for d in data[0].orderedcontents:
            for b in (self.ob,) + data[1:]:
                if d.name in b.contents:
                    break
            else:
                return context.tag()
        else:
            return context.tag.clear()

    def render_basechildclass(self, context, data):
        return 'base' + data.kind.lower()

    def render_basechildname(self, context, data):
        tag = context.tag()
        tag.clear()
        return tag[tags.a(href=link(data.parent)+'#'+data.fullName())[data.name]]

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
        return tag[doc2html(docsource, summary=True)]

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
