from compiler import ast
import sys
import os
import cPickle as pickle
import __builtin__
import sets

from compiler.transformer import parse, parseFile
from compiler.visitor import walk

from pydoctor import ast_pp

# originally when I started to write pydoctor I had this idea of a big
# tree of Documentables arranged in an almost arbitrary tree.
#
# this was misguided.  the tree structure is important, to be sure,
# but the arrangement of the tree is far from arbitrary and there is
# at least some code that now relies on this.  so here's a list:
#
#   Packages can contain Packages and Modules
#   Modules can contain Functions and Classes
#   Classes can contain Functions (when they get called Methods) and Classes
#   Functions can't contain anything.

class Documentable(object):
    document_in_parent_page = False
    sourceHref = None
    def __init__(self, system, prefix, name, docstring, parent=None):
        self.system = system
        self.prefix = prefix
        self.name = name
        self.docstring = docstring
        self.parent = parent
        self.parentMod = None
        self.setup()
        if not isinstance(self, Package):
            self.doctarget = self
    def setup(self):
        self.contents = {}
        self.orderedcontents = []
        self._name2fullname = {}
    def fullName(self):
        return self.prefix + self.name
    def __repr__(self):
        return "%s %r"%(self.__class__.__name__, self.fullName())
    def docsources(self):
        yield self
    def name2fullname(self, name):
        if name in self._name2fullname:
            return self._name2fullname[name]
        else:
            return self.parent.name2fullname(name)

    def _resolveName(self, name, verbose):
        system = self.system
        obj = self
        while obj:
            if name in obj.contents:
                return obj.contents[name]
            elif name in obj._name2fullname:
                fn = obj._name2fullname[name]
                o = system.allobjects.get(fn)
                if o is None:
                    for othersys in system.moresystems:
                        o = othersys.allobjects.get(fn)
                        if o is not None:
                            break
                if o is None and verbose > 0:
                    print "from %r, %r resolves to %r which isn't present in the system"%(
                        self.fullName(), name, fn)
                return o
            obj = obj.parent
        obj = self
        while obj:
            for n, fn in obj._name2fullname.iteritems():
                o2 = system.allobjects.get(fn)
                if o2 and name in o2.contents:
                    return o2.contents[name]
            obj = obj.parent
        if name in system.allobjects:
            return system.allobjects[name]
        for othersys in system.moresystems:
            if name in othersys.allobjects:
                return othersys.allobjects[name]
        if verbose > 0:
            print "failed to find %r from %r"%(name, self.fullName())
        return None

    def resolveDottedName(self, dottedname, verbose=None):
        if verbose is None:
            verbose = self.system.options.verbosity
        parts = dottedname.split('.')
        obj = self._resolveName(parts[0], verbose)
        if obj is None:
            return obj
        system = self.system
        for p in parts[1:]:
            if p not in obj.contents:
                if verbose > 0:
                    print "2 didn't find %r from %r"%(dottedname,
                                                      self.fullName())
                return None
            obj = obj.contents[p]
        if verbose > 1:
            print dottedname, '->', obj.fullName(), 'in', self.fullName()
        return obj

    def dottedNameToFullName(self, dottedname):
        if '.' not in dottedname:
            start, rest = dottedname, ''
        else:
            start, rest = dottedname.split('.', 1)
            rest = '.' + rest
        obj = self
        while start not in obj._name2fullname:
            obj = obj.parent
            if obj is None or isinstance(obj, Package):
                return dottedname
        return obj._name2fullname[start] + rest

    def __getstate__(self):
        # this is so very, very evil.
        # see doc/extreme-pickling-pain.txt for more.
        r = {}
        for k, v in self.__dict__.iteritems():
            if isinstance(v, Documentable):
                r['$'+k] = v.fullName()
            elif isinstance(v, list) and v:
                for vv in v:
                    if vv is not None and not isinstance(vv, Documentable):
                        r[k] = v
                        break
                else:
                    rr = []
                    for vv in v:
                        if vv is None:
                            rr.append(vv)
                        else:
                            rr.append(vv.fullName())
                    r['@'+k] = rr
            elif isinstance(v, dict) and v:
                for vv in v.itervalues():
                    if not isinstance(vv, Documentable):
                        r[k] = v
                        break
                else:
                    rr = {}
                    for kk, vv in v.iteritems():
                        rr[kk] = vv.fullName()
                    r['!'+k] = rr
            else:
                r[k] = v
        return r

class Package(Documentable):
    kind = "Package"
    def name2fullname(self, name):
        raise NameError
    def docsources(self):
        yield self.contents['__init__']
    @property
    def doctarget(self):
        return self.contents['__init__']


class Module(Documentable):
    kind = "Module"
    processed = False
    linenumber = 0
    def setup(self):
        super(Module, self).setup()
        self.all = None
    def name2fullname(self, name):
        if name in self._name2fullname:
            return self._name2fullname[name]
        elif name in __builtin__.__dict__:
            return name
        else:
            self.system.warning("optimistic name resolution", name)
            return name


class Class(Documentable):
    kind = "Class"
    def setup(self):
        super(Class, self).setup()
        self.bases = []
        self.rawbases = []
        self.baseobjects = []
        self.subclasses = []
    def allbases(self):
        for b in self.baseobjects:
            if b is None:
                continue
            yield b
            for b2 in b.allbases():
                yield b2


class Function(Documentable):
    document_in_parent_page = True
    kind = "Function"
    def setup(self):
        super(Function, self).setup()
        if isinstance(self.parent, Class):
            self.kind = "Method"
    def docsources(self):
        yield self
        if not isinstance(self.parent, Class):
            return
        for b in self.parent.allbases():
            if self.name in b.contents:
                yield b.contents[self.name]

states = [
    'blank',
    'preparse',
    'imported',
    'parsed',
    'finalized',
    'livechecked',
    ]

class System(object):
    # not done here for circularity reasons:
    #defaultBuilder = astbuilder.ASTBuilder
    sourcebase = None

    def __init__(self):
        self.allobjects = {}
        self.orderedallobjects = []
        self.rootobjects = []
        self.warnings = {}
        # importgraph contains edges {importer:{imported}} but only
        # for module-level import statements
        self.importgraph = {}
        self.state = 'blank'
        self.packages = []
        self.moresystems = []
        self.subsystems = []
        self.urlprefix = ''
        from pydoctor.driver import parse_args
        self.options, _ = parse_args([])
        self.options.verbosity = 3
        self.abbrevmapping = {}
        self.guessedprojectname = 'my project'
        self.epytextproblems = [] # fullNames of objects that failed to epytext properly
        self.verboselevel = 0
        self.needsnl = False
        self.once_msgs = set()

    def verbosity(self, section=None):
        return self.options.verbosity + self.options.verbosity_details.get(section, 0)

    def progress(self, section, i, n, msg):
        if n is None:
            i = str(i)
        else:
            i = '%s/%s'%(i,n)
        if self.verbosity(section) == 0 and sys.stdout.isatty():
            print '\r'+i, msg,
            sys.stdout.flush()
            if i == n:
                self.needsnl = False
                print
            else:
                self.needsnl = True

    def msg(self, section, msg, thresh=0, topthresh=100, nonl=False, wantsnl=True, once=False):
        if once:
            if (section, msg) in self.once_msgs:
                return
            else:
                self.once_msgs.add((section, msg))
        if thresh <= self.verbosity(section) <= topthresh:
            if self.needsnl and wantsnl:
                print
            print msg,
            if nonl:
                self.needsnl = True
                sys.stdout.flush()
            else:
                self.needsnl = False
                print

    def report(self):
        for o in self.rootobjects:
            self._report(o, '')

    def _report(self, o, indent):
        print indent, o
        for o2 in o.orderedcontents:
            self._report(o2, indent+'  ')

    def resolveAlias(self, n):
        if '.' not in n:
            return n
        mod, clsname = n.rsplit('.', 1)
        if not mod:
            return mod
        systems = [self] + self.moresystems
        for system in systems:
            if mod in system.allobjects:
                break
        else:
            return n
        m = system.allobjects[mod]
        if not isinstance(m, Module):
            return n
        if clsname in m._name2fullname:
            newname = m.name2fullname(clsname)
            print newname
            for system in systems:
                if newname in system.allobjects:
                    return newname
            else:
                return self.resolveAlias(newname)
        else:
            return n

    def objForFullName(self, fullName):
        for sys in [self] + self.moresystems:
            if fullName in sys.allobjects:
                return sys.allobjects[fullName]
        return None

    def _warning(self, current, type, detail):
        if current is not None:
            fn = current.fullName()
        else:
            fn = '<None>'
        if self.options.verbosity > 0:
            print fn, type, detail
        self.warnings.setdefault(type, []).append((fn, detail))

    def objectsOfType(self, cls):
        for o in self.orderedallobjects:
            if isinstance(o, cls):
                yield o

    def __setstate__(self, state):
        if 'abbrevmapping' not in state:
            state['abbrevmapping'] = {}
        # this is so very, very evil.
        # see doc/extreme-pickling-pain.txt for more.
        def lookup(name):
            for sys in [self] + self.moresystems + self.subsystems:
                if name in sys.allobjects:
                    return sys.allobjects[name]
            raise KeyError, name
        self.__dict__.update(state)
        for sys in [self] + self.moresystems + self.subsystems:
            if 'allobjects' not in sys.__dict__:
                return
        for sys in [self] + self.moresystems + self.subsystems:
            for obj in sys.orderedallobjects:
                for k, v in obj.__dict__.copy().iteritems():
                    if k.startswith('$'):
                        del obj.__dict__[k]
                        obj.__dict__[k[1:]] = lookup(v)
                    elif k.startswith('@'):
                        n = []
                        for vv in v:
                            if vv is None:
                                n.append(None)
                            else:
                                n.append(lookup(vv))
                        del obj.__dict__[k]
                        obj.__dict__[k[1:]] = n
                    elif k.startswith('!'):
                        n = {}
                        for kk, vv in v.iteritems():
                            n[kk] = lookup(vv)
                        del obj.__dict__[k]
                        obj.__dict__[k[1:]] = n
