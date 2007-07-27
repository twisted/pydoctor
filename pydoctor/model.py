import os
import sys
import __builtin__

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
    def __init__(self, system, name, docstring, parent=None):
        self.system = system
        if parent is not None:
            if (parent.parent and isinstance(parent.parent, Package)
                and isinstance(parent, Module)
                and parent.name == '__init__'):
                self.prefix = parent.parent.fullName() + '.'
            else:
                self.prefix = parent.fullName() + '.'
        else:
            self.prefix = ''
        self.name = name
        self.docstring = docstring
        self.parent = parent
        self.parentMod = None
        self.setup()
        if not isinstance(self, Package):
            self.doctarget = self

        if system is None:
            return

        if parent:
            parent.orderedcontents.append(self)
            parent.contents[name] = self
            parent._name2fullname[name] = self.fullName()
        else:
            system.rootobjects.append(self)
        system.orderedallobjects.append(self)
        fullName = self.fullName()
        if fullName in system.allobjects:
            system.handleDuplicate(self)
        else:
            system.allobjects[fullName] = self

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
    Class = Class
    Module = Module
    Package = Package
    Function = Function
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
        self.unprocessed_modules = set()

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
            if newname == n:
                return newname
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

    def shouldInclude(self, ob):
        return True

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



    # if we assume:
    #
    # - that svn://divmod.org/trunk is checked out into ~/src/Divmod
    #
    # - that http://divmod.org/trac/browser/trunk is the trac URL to the
    #   above directory
    #
    # - that ~/src/Divmod/Nevow/nevow is passed to pydoctor as an
    #   "--add-package" argument
    #
    # we want to work out the sourceHref for nevow.flat.ten.  the answer
    # is http://divmod.org/trac/browser/trunk/Nevow/nevow/flat/ten.py.
    #
    # we can work this out by finding that Divmod is the top of the svn
    # checkout, and posixpath.join-ing the parts of the filePath that
    # follows that.
    #
    #  http://divmod.org/trac/browser/trunk
    #                          ~/src/Divmod/Nevow/nevow/flat/ten.py

    def setSourceHref(self, mod):
        if self.sourcebase is None:
            mod.sourceHref = None
            return

        trailing = []
        dir, fname = os.path.split(mod.filepath)
        while os.path.exists(os.path.join(dir, '.svn')):
            dir, dirname = os.path.split(dir)
            trailing.append(dirname)

        # now trailing[-1] would be 'Divmod' in the above example
        del trailing[-1]
        trailing.reverse()
        trailing.append(fname)

        mod.sourceHref = posixpath.join(mod.system.sourcebase, *trailing)

    def addModule(self, modpath, parentPackage=None):
        assert self.state in ['blank', 'preparse']
        fname = os.path.basename(modpath)
        modname = os.path.splitext(fname)[0]
        mod = self.Module(self, modname, None, parentPackage)
        self.progress(
            "addModule", len(self.orderedallobjects),
            None, "modules and packages discovered")
        mod.filepath = modpath
        self.unprocessed_modules.add(mod)
        self.setSourceHref(mod)
        self.state = 'preparse'

    def addDirectory(self, dirpath, parentPackage=None):
        assert self.state in ['blank', 'preparse']
        if not os.path.exists(dirpath):
            raise Exception("package path %r does not exist!"
                            %(dirpath,))
        if not os.path.exists(os.path.join(dirpath, '__init__.py')):
            raise Exception("you must pass a package directory to "
                            "preprocessDirectory")
        package = self.Package(self, os.path.basename(dirpath),
                               None, parentPackage)
        package.filepath = dirpath
        self.setSourceHref(package)
        for fname in os.listdir(dirpath):
            fullname = os.path.join(dirpath, fname)
            if os.path.isdir(fullname):
                initname = os.path.join(fullname, '__init__.py')
                if os.path.exists(initname):
                    self.addDirectory(fullname, package)
            elif fname.endswith('.py') and not fname.startswith('.'):
                self.addModule(fullname, package)
        self.state = 'preparse'

    def handleDuplicate(self, obj):
        '''This is called when we see two objects with the same
        .fullName(), for example:

        class C:
            if something:
                def meth(self):
                    implementation 1
            else:
                def meth(self):
                    implementation 2

        The default is that the second definition "wins".
        '''
        i = 0
        fn = obj.fullName()
        while (fn + ' ' + str(i)) in self.allobjects:
            i += 1
        prev = self.allobjects[obj.fullName()]
        prev.name = obj.name + ' ' + str(i)
        self.allobjects[prev.fullName()] = prev
        self._warning(obj.parent, "duplicate", self.allobjects[obj.fullName()])
        self.allobjects[obj.fullName()] = obj
        return obj
