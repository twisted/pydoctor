from docextractor import model
from os.path import join as opj
import os, inspect, shutil

try:
    from epydoc.markup import epytext
    EPYTEXT = True
except:
    EPYTEXT = False

def link(o):
    return o.fullName()+'.html'

def linkto(o, label=None):
    if label is None:
        label = o.fullName()
    return '<a href="%s">%s</a>'%(link(o), label)

def summaryDoc(obj):
    """Generate a one-line summary of a docstring."""
    if isinstance(obj, model.Package):
        obj = obj.contents['__init__']
    doc = obj.docstring
    if not doc or not doc.strip():
        return 'Undocumented'
    # Return the first line of the docstring (that actually has stuff)
    for doc in doc.splitlines():
        if doc.strip(): 
            return doc

def boringDocstring(doc):
    """Generate an HTML representation of a docstring in a really boring
    way."""
    # inspect.getdoc requires an object with a __doc__ attribute, not
    # just a string :-(
    if doc is None or not doc.strip():
        return '<pre class="undocumented">Undocumented</pre>'
    def crappit(): pass
    crappit.__doc__ = doc
    return '<pre>%s</pre>' % inspect.getdoc(crappit)

errcount = 0

def doc2html(obj, doc):
    """Generate an HTML representation of a docstring"""
    if doc is None or not doc.strip():
        return '<div class="undocumented">Undocumented</div>'
    if not EPYTEXT:
        print 'not epytext'
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
            global errcount
            errcount += len(errs)
            return boringDocstring(doc)
    pdoc, fields = pdoc.split_fields()
    crap = pdoc.to_html(_EpydocLinker(obj))
    s = '<div>%s</div>' % (crap,)
    for field in fields:
        s += (('<div class="metadata"><span class="tag">%s</span>'
              '<span class="arg">%s</span>'
              '<span class="body">%s</span></div>')
              % (field.tag(), field.arg(),
                 field.body().to_html(_EpydocLinker(obj))))
    return s


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

def mediumName(obj):
    fn = obj.fullName()
    if '.' not in fn:
        return fn
    path, name = fn.rsplit('.', 1)
    return '.'.join([p[0] for p in path.split('.')]) + '.' + name

class SystemWriter(object):
    """Construct me with a directory to write files to and call
    writeIndividualFiles and/or writeModuleIndex."""
    def __init__(self, base):
        self.base = base

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(sibpath(__file__, 'apidocs.css'), 
                        os.path.join(self.base, 'apidocs.css'))

    def writeIndividualFiles(self, stuff):
        """Writes HTML files for every documentable passed, recursively. This
        looks up methods like 'genPage_DOCUMENTABLETYPE' on self to
        get the HTML for particular kinds of documentables.
        """
        for sub in stuff:
            html = self.getHTMLFor(sub)
            f = open(opj(self.base, link(sub)), 'w')
            f.write(html)
            f.close()
            self.writeIndividualFiles(sub.orderedcontents)

    def getHTMLFor(self, o):
        for cls in o.__class__.__mro__:
            fun = getattr(self, 'html_%s' % (cls.__name__,), None)
            if fun is not None:
                break
        else:
            raise TypeError("Don't know how to document a "+o.__class__.__name__)
        d = fun(o)
        d = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">        
        <html><head>
        <link rel="stylesheet" type="text/css" href="apidocs.css"/>
        </head>
        <body>%s</body>
        ''' % (d,)
        return d

    def generateModuleIndex(self, pkg):
        x = "<html><body><h1>Package %s</h1>" % pkg.fullName()
        x += '<ul>%s</ul>' % self._allModules(pkg)
        x += '</body></html>'
        return x

    def writeModuleIndex(self, pkg):
        """Writes a module index to the file 'moduleindex.html' in the doc
        directory."""
        f = open(opj(self.base, 'moduleindex.html'), 'w')
        f.write(self.generateModuleIndex(pkg))
        f.close()

    ## HTML Generators for Documentable types

    def html_Package(self, pkg):
        x = '<h1 class="package">Package %s</h1>' % (mediumName(pkg),)
        x += self._parentLink(pkg)
        z = doc2html(pkg, pkg.contents['__init__'].docstring)
        x += '<div class="toplevel">%s</div>' % (z,)
        x += self._genChildren([x for x in pkg.orderedcontents 
                                 if x.name != '__init__'])
        return x

    def html_Module(self, mod):
        x = '<h1 class="module">Module %s</h1>' % (mediumName(mod),)
        x += self._parentLink(mod)
        z = doc2html(mod, mod.docstring)
        x += '<div class="toplevel">%s</div>' % (z,)
        x += self._genChildren(mod.orderedcontents)
        return x

    def bases_html(self, cls):
        r = []
        for n, o in zip(cls.rawbases, cls.baseobjects):
            if o is None:
                r.append(n)
            else:
                r.append('<a href="%s">%s</a>'%(link(o), n))
        if r:
            return '(' + ', '.join(r) + ')'
        else:
            return ''

    def html_Class(self, cls):
        x = '<h1 class="%s">%s %s%s:</h1>' % (cls.kind.lower(), cls.kind, mediumName(cls), self.bases_html(cls))
        x += self._parentLink(cls)
        if cls.subclasses:
            x += '<p>known subclasses: %s</p>'%(', '.join(
                map(linkto, cls.subclasses)))
        z = doc2html(cls, cls.docstring)
        x += '<div class="toplevel">%s</div>' % (z,)
        link = lambda x: '#' + x.fullName()
        x += self._genChildren(cls.orderedcontents, link=link)
        for meth in cls.orderedcontents:
            if not isinstance(meth, model.Function):
                continue
            x += '''
            <div class="function">
            <div class="functionHeader">def <a name="%s">%s:</a></div>
            <div class="functionBody">%s</div>
            </div>''' % (
                meth.fullName(),
                self._funsig(meth), doc2html(meth, meth.docstring))
        return x

    def html_TwistedClass(self, cls):
        x = '<h1 class="%s">%s %s%s:</h1>' % (cls.kind.lower(), cls.kind, mediumName(cls), self.bases_html(cls))
        x += self._parentLink(cls)
        if cls.subclasses:
            x += '<p>known subclasses: %s</p>'%(', '.join(
                map(linkto, cls.subclasses)))
        if cls.isinterface and cls.implementedby:
            x += '<p>known implementations: %s</p>'%(', '.join(
                map(linkto, cls.implementedby)))
        elif cls.implements:
            links = []
            for interface in cls.implements:
                if interface in cls.system.allobjects:
                    links.append(linkto(cls.system.allobjects[interface]))
                else:
                    links.append(interface)
            x += '<p>implements interfaces: %s</p>'%(', '.join(links))
        z = doc2html(cls, cls.docstring)
        x += '<div class="toplevel">%s</div>' % (z,)
        link = lambda x: '#' + x.fullName()
        x += self._genChildren(cls.orderedcontents, link=link)
        for meth in cls.orderedcontents:
            if not isinstance(meth, model.Function):
                continue
            x += '''
            <div class="function">
            <div class="functionHeader">def <a name="%s">%s:</a></div>
            %s
            <div class="functionBody">%s</div></div>''' % (
                meth.fullName(),
                self._funsig(meth),
                self.interfaceInfo(cls, meth),
                doc2html(meth, meth.docstring))
        return x

    def interfaceInfo(self, cls, meth):
        for interface in cls.implements:
            if interface in cls.system.allobjects:
                io = cls.system.allobjects[interface]
                if meth.name in io.contents:
                    return '<div class="interfaceinfo">from %s</div>'%(linkto(io),)
        return ''
                    
    def html_Function(self, fun):
        x = '<h1 class="function">Function %s:</h1>' % (self._funsig(fun))
        x += self._parentLink(fun)
        x += doc2html(fun, fun.docstring)
        return x

    ## Utilities
    def _funsig(self, fun):
        return '%s(%s)' % (fun.name, signature(fun.argspec))

    def _genChildren(self, children, link=link):
        """Render a table mapping children names to summary docstrings."""
        x = '<table class="children">'
        for obj in children:
            x += ('<tr class="%(kindLower)s"><td>%(kind)s</td>'
                  '<td><a href="%(link)s">%(name)s</a>'
                  '</td><td>%(doc)s</td></tr>') % {
                'kindLower': obj.kind.lower(),
                'kind': obj.kind,
                'link': link(obj),
                'name': obj.name,
                'doc': summaryDoc(obj)}
        x += '</table>'
        return x

    def _parentLink(self, o):
        """A link to the Documentable's parent."""
        if not o.parent: 
            return ''
        return '<div id="part">Part of <a href="%s">%s</a></div>' % (
            link(o.parent), o.parent.fullName())

    def _allModules(self, pkg):
        """Generates an HTML representation of all modules (including
        packages) in a nested list."""
        x = ""
        # orderedcontents isn't ordered for modules, for some reason.
        pkg.orderedcontents.sort(key=lambda o: o.fullName())
        for mod in pkg.orderedcontents:
            if mod.name == '__init__':
                # XXX Rehh??
                continue
            MOD = isinstance(mod, model.Module)
            PKG = isinstance(mod, model.Package)
            if MOD or PKG:
                x += '<li><a href="%(link)s">%(name)s</a> - %(doc)s</li>' % {
                    'name': mod.fullName(),
                    'link': link(mod),
                    'doc': summaryDoc(mod)}
            if isinstance(mod, model.Package):
                x += '<ul>%s</ul>' % self._allModules(mod)
        return x

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

def main(args):
    from optparse import OptionParser
    import cPickle
    parser = OptionParser()
    parser.add_option('-f', '--file', dest='filename',
                      help="Open this file")
    parser.add_option('-m', '--module', dest='module',
                      help="Python object to generate API docs for.")
    parser.add_option('-o', '--output', dest='output',
                      help="Directory to save HTML files to")
    options, args = parser.parse_args()

    fn = 'da.out'
    if options.filename:
        fn = options.filename
    out = 'apidocs'
    if options.output:
        out = options.output

    docsys = cPickle.load(open(fn, 'rb'))
    syswriter = SystemWriter(out)
    syswriter.prepOutputDirectory()
    if options.module:
        obj = docsys.allobjects[options.module]
        print "WRITING DOCS FOR", obj.fullName()
        syswriter.writeIndividualFiles([obj])
    else:
        syswriter.writeModuleIndex(docsys.rootobjects[0])
        syswriter.writeIndividualFiles(docsys.rootobjects)

    print errcount, 'epytext errors'

if __name__ == '__main__': 
    main()
