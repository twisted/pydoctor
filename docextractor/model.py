from compiler import ast
import sys
import os
import cPickle as pickle
import __builtin__
import sets

from compiler.transformer import parse, parseFile
from compiler.visitor import walk

from docextractor import ast_pp

class Documentable(object):
    def __init__(self, system, prefix, name, docstring, parent=None):
        self.system = system
        self.prefix = prefix
        self.name = name
        self.docstring = docstring
        self.parent = parent
        self.setup()
    def setup(self):
        self.contents = {}
        self.orderedcontents = []
        self._name2fullname = {}
    def fullName(self):
        return self.prefix + self.name
    def shortdocstring(self):
        docstring = self.docstring
        if docstring:
            docstring = docstring.rstrip()
            if len(docstring) > 20:
                docstring = docstring[:8] + '...' + docstring[-8:]
        return docstring
    def __repr__(self):
        return "%s %r"%(self.__class__.__name__, self.fullName())
    def name2fullname(self, name):
        if name in self._name2fullname:
            return self._name2fullname[name]
        else:
            return self.parent.name2fullname(name)

    def resolveDottedName(self, dottedname, verbose=False):
        parts = dottedname.split('.')
        obj = self
        system = self.system
        while parts[0] not in obj._name2fullname:
            obj = obj.parent
            if obj is None:
                if parts[0] in system.allobjects:
                    obj = system.allobjects[parts[0]]
                    break
                if verbose:
                    print "1 didn't find %r from %r"%(dottedname,
                                                      self.fullName())
                return None
        else:
            fn = obj._name2fullname[parts[0]]
            if fn in system.allobjects:
                obj = system.allobjects[fn]
            else:
                if verbose:
                    print "1.5 didn't find %r from %r"%(dottedname,
                                                        self.fullName())
                return None
        for p in parts[1:]:
            if p not in obj.contents:
                if verbose:
                    print "2 didn't find %r from %r"%(dottedname,
                                                      self.fullName())
                return None
            obj = obj.contents[p]
        if verbose:
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
            if obj is None:
                return dottedname
        return obj._name2fullname[start] + rest

    def __getstate__(self):
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


class Module(Documentable):
    kind = "Module"
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


class Function(Documentable):
    kind = "Function"


class ModuleVistor(object):
    def __init__(self, system, modname):
        self.system = system
        self.modname = modname
        self.morenodes = []

    def default(self, node):
        for child in node.getChildNodes():
            self.visit(child)

    def postpone(self, docable, node):
        self.morenodes.append((docable, node))

    def visitModule(self, node):
        if self.system.current and self.modname in self.system.current.contents:
            m = self.system.current.contents[self.modname]
            assert m.docstring is None
            m.docstring = node.doc
            self.system.push(m)
            self.default(node)
            self.system.pop(m)
        else:
            self.system.pushModule(self.modname, node.doc)
            self.default(node)
            self.system.popModule()

    def visitClass(self, node):
        cls = self.system.pushClass(node.name, node.doc)
        for n in node.bases:
            str_base = ast_pp.pp(n)
            cls.rawbases.append(str_base)
            base = cls.dottedNameToFullName(str_base)
            cls.bases.append(base)
        self.default(node)
        self.system.popClass()

    def visitFrom(self, node):
        modname = expandModname(self.system, node.modname)
        name2fullname = self.system.current._name2fullname
        for fromname, asname in node.names:
            if fromname == '*':
                self.system.warning("import *", modname)
                if modname not in self.system.allobjects:
                    return
                mod = self.system.allobjects[modname]
                # this might fail if you have an import-* cycle, or if
                # you're just not running the import star finder to
                # save time (not that this is possibly without
                # commenting stuff out yet, but...)
                if mod.processed:
                    for n in mod.contents:
                        name2fullname[n] = modname + '.' + n
                else:
                    self.system.warning("unresolvable import *", modname)
                return
            if asname is None:
                asname = fromname
            name2fullname[asname] = modname + '.' + fromname

    def visitImport(self, node):
        name2fullname = self.system.current._name2fullname
        for fromname, asname in node.names:
            fullname = expandModname(self.system, fromname)
            if asname is None:
                asname = fromname.split('.', 1)[0]
                # aaaaargh! python sucks.
                parts = fullname.split('.')
                for i, part in enumerate(fullname.split('.')[::-1]):
                    if part == asname:
                        fullname = '.'.join(parts[:len(parts)-i])
                        name2fullname[asname] = fullname
                        break
                else:
                    name2fullname[asname] = '.'.join(parts)
            else:
                name2fullname[asname] = fullname

    def visitFunction(self, node):
        func = self.system.pushFunction(node.name, node.doc)
        # ast.Function has a pretty lame representation of
        # arguments. Let's convert it to a nice concise format
        # somewhat like what inspect.getargspec returns
        argnames = node.argnames[:]
        kwname = starargname = None
        if node.kwargs:
            kwname = argnames.pop(-1)
        if node.varargs:
            starargname = argnames.pop(-1)
        defaults = []
        for default in node.defaults:
            try:
                defaults.append(ast_pp.pp(default))
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                self.system.warning("unparseable default", "%s: %s %r"%(e.__class__.__name__,
                                                                       e, default))
                defaults.append('???')
        # argh, convert unpacked-arguments from tuples to lists,
        # because that's what getargspec uses and the unit test
        # compares it
        argnames2 = []
        for argname in argnames:
            if isinstance(argname, tuple):
                argname = list(argname)
            argnames2.append(argname)
        func.argspec = (argnames2, starargname, kwname, tuple(defaults))
        self.postpone(func, node.code)
        self.system.popFunction()


class System(object):
    Class = Class
    Module = Module
    Package = Package
    Function = Function
    ModuleVistor = ModuleVistor

    def __init__(self):
        self.current = None
        self._stack = []
        self.allobjects = {}
        self.orderedallobjects = []
        self.rootobjects = []
        self.warnings = {}
        # importstargraph contains edges {importer:[imported]} but only
        # for import * statements
        self.importstargraph = {}

    def _push(self, cls, name, docstring):
        if self.current:
            prefix = self.current.fullName() + '.'
            parent = self.current
        else:
            prefix = ''
            parent = None
        obj = cls(self, prefix, name, docstring, parent)
        if parent:
            parent.orderedcontents.append(obj)
            parent.contents[name] = obj
            parent._name2fullname[name] = obj.fullName()
        else:
            self.rootobjects.append(obj)
        self.current = obj
        self.orderedallobjects.append(obj)
        fullName = obj.fullName()
        #print 'push', cls.__name__, fullName
        if fullName in self.allobjects:
            obj = self.handleDuplicate(obj)
        else:
            self.allobjects[obj.fullName()] = obj
        return obj

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
        self.warning("duplicate", self.allobjects[obj.fullName()])
        self.allobjects[obj.fullName()] = obj
        return obj


    def _pop(self, cls):
        assert isinstance(self.current, cls)
##         if self.current.parent:
##             print 'pop', self.current.fullName(), '->', self.current.parent.fullName()
##         else:
##             print 'pop', self.current.fullName(), '->', self.current.parent
        self.current = self.current.parent

    def push(self, obj):
        self._stack.append(self.current)
        self.current = obj

    def pop(self, obj):
        assert self.current is obj, "%r is not %r"%(self.current, obj)
        self.current = self._stack.pop()

    def pushClass(self, name, docstring):
        return self._push(self.Class, name, docstring)
    def popClass(self):
        self._pop(self.Class)

    def pushModule(self, name, docstring):
        return self._push(self.Module, name, docstring)
    def popModule(self):
        self._pop(self.Module)

    def pushFunction(self, name, docstring):
        return self._push(self.Function, name, docstring)
    def popFunction(self):
        self._pop(self.Function)

    def pushPackage(self, name, docstring):
        return self._push(self.Package, name, docstring)
    def popPackage(self):
        self._pop(self.Package)

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
        mod, clsname = n.split('.')
        if not mod or mod not in self.allobjects:
            return n
        m = self.allobjects[mod]
        if not isinstance(m, Module):
            return n
        if clsname in m._name2fullname:
            newname = m.name2fullname(clsname)
            if newname not in self.allobjects:
                return self.resolveAlias(newname)
            else:
                return newname

    def resolveAliases(self):
        for ob in self.orderedallobjects:
            if not isinstance(ob, Class):
                continue
            for i, b in enumerate(ob.bases):
                if b not in self.allobjects:
                    ob.bases[i] = self.resolveAlias(b)

    def warning(self, type, detail):
        if self.current is not None:
            fn = self.current.fullName()
        else:
            fn = '<None>'
        print fn, type, detail
        self.warnings.setdefault(type, []).append((fn, detail))

    def objectsOfType(self, cls):
        for o in self.orderedallobjects:
            if isinstance(o, cls):
                yield o

    def finalStateComputations(self):
        self.recordBasesAndSubclasses()

    def recordBasesAndSubclasses(self):
        for cls in self.objectsOfType(Class):
            for n in cls.rawbases:
                o = cls.parent.resolveDottedName(n)
                cls.baseobjects.append(o)
                if o:
                    o.subclasses.append(cls)

    def __setstate__(self, state):
        self.__dict__.update(state)
        for obj in self.orderedallobjects:
            for k, v in obj.__dict__.copy().iteritems():
                if k.startswith('$'):
                    del obj.__dict__[k]
                    obj.__dict__[k[1:]] = self.allobjects[v]
                elif k.startswith('@'):
                    n = []
                    for vv in v:
                        if vv is None:
                            n.append(None)
                        else:
                            n.append(self.allobjects[vv])
                    del obj.__dict__[k]
                    obj.__dict__[k[1:]] = n
                elif k.startswith('!'):
                    n = {}
                    for kk, vv in v.iteritems():
                        n[kk] = self.allobjects[vv]
                    del obj.__dict__[k]
                    obj.__dict__[k[1:]] = n


def expandModname(system, modname, givewarning=True):
    c = system.current
    if '.' in modname:
        prefix, suffix = modname.split('.', 1)
        suffix = '.' + suffix
    else:
        prefix, suffix = modname, ''
    while c is not None and not isinstance(c, Package):
        c = c.parent
    while c is not None:
        if prefix in c.contents:
            break
        c = c.parent
    if c is not None:
        if givewarning:
            system.warning("local import", modname)
        return c.contents[prefix].fullName() + suffix
    else:
        return prefix + suffix

class ImportStarFinder(object):
    def __init__(self, system, modfullname):
        self.system = system
        self.modfullname = modfullname

    def visitFrom(self, node):
        if node.names[0][0] == '*':
            modname = expandModname(self.system, node.modname, False)
            self.system.importstargraph.setdefault(
                self.modfullname, []).append(modname)

def processModuleAst(ast, name, system):
    mv = system.ModuleVistor(system, name)
    walk(ast, mv)
    while mv.morenodes:
        obj, node = mv.morenodes.pop(0)
        system.push(obj)
        mv.visit(node)
        system.pop(obj)


def fromText(src, modname='<test>', system=None):
    if system is None:
        _system = System()
    else:
        _system = system
    processModuleAst(parse(src), modname, _system)
    if system is None:
        _system.finalStateComputations()
    return _system.rootobjects[0]


def preprocessDirectory(system, dirpath):
    package = system.pushPackage(os.path.basename(dirpath), None)
    for fname in os.listdir(dirpath):
        fullname = os.path.join(dirpath, fname)
        if os.path.isdir(fullname) and os.path.exists(os.path.join(fullname, '__init__.py')) and fname != 'test':
            preprocessDirectory(system, fullname)
        elif fname.endswith('.py'):
            modname = os.path.splitext(fname)[0]
            mod = system.pushModule(modname, None)
            mod.filepath = fullname
            mod.processed = False
            system.popModule()
    system.popPackage()

def findImportStars(system):
    modlist = list(system.objectsOfType(Module))
    for mod in modlist:
        system.push(mod.parent)
        isf = ImportStarFinder(system, mod.fullName())
        walk(parseFile(mod.filepath), isf)
        system.pop(mod.parent)

def extractDocstrings(system):
    # and so much more...
    modlist = list(system.objectsOfType(Module))
    newlist = toposort([m.fullName() for m in modlist], system.importstargraph)

    for mod in newlist:
        mod = system.allobjects[mod]
        system.push(mod.parent)
        processModuleAst(parseFile(mod.filepath), mod.name, system)
        mod.processed = True
        system.pop(mod.parent)

def finalStateComputations(system):
    system.finalStateComputations()

def processDirectory(system, dirpath):
    preprocessDirectory(system, dirpath)
    findImportStars(system)
    extractDocstrings(system)
    finalStateComputations(system)

def toposort(input, edges):
    # this doesn't detect cycles in any clever way.
    output = []
    input = dict.fromkeys(input)
    def p(i):
        for j in edges.get(i, []):
            if j in input:
                del input[j]
                p(j)
        output.append(i)
    while input:
        p(input.popitem()[0])
    return output


def main(systemcls, argv):
    if '-r' in argv:
        argv.remove('-r')
        assert len(argv) == 1
        system = systemcls()
        processDirectory(system, argv[0])
        pickle.dump(system, open('da.out', 'wb'), pickle.HIGHEST_PROTOCOL)
        print
        print 'warning summary:'
        for k, v in system.warnings.iteritems():
            print k, len(v)
    else:
        system = systemcls()
        for fname in argv:
            modname = os.path.splitext(os.path.basename(fname))[0] # XXX!
            processModuleAst(parseFile(fname), modname, system)
        system.report()



if __name__ == '__main__':
    main(System, sys.argv[1:])
