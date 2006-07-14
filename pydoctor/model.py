from compiler import ast
import sys
import os
import cPickle as pickle
import __builtin__
import sets

from compiler.transformer import parse, parseFile
from compiler.visitor import walk

from pydoctor import ast_pp

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
                for othersys in system.moresystems:
                    if parts[0] in othersys.allobjects:
                        obj = othersys.allobjects[parts[0]]
                        break
                else:
                    if verbose:
                        print "1 didn't find %r from %r"%(dottedname,
                                                      self.fullName())
                    return None
                break
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


states = [
    'blank',
    'preparse',
    'importstarred',
    'parsed',
    'finalized',
    ]


class System(object):

    def __init__(self):
        self.allobjects = {}
        self.orderedallobjects = []
        self.rootobjects = []
        self.warnings = {}
        # importstargraph contains edges {importer:[imported]} but only
        # for import * statements
        self.importstargraph = {}
        self.state = 'blank'
        self.packages = []
        self.moresystems = []
        self.urlprefix = ''

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

    def _warning(self, current, type, detail):
        if current is not None:
            fn = current.fullName()
        else:
            fn = '<None>'
        print fn, type, detail
        self.warnings.setdefault(type, []).append((fn, detail))

    def objectsOfType(self, cls):
        for o in self.orderedallobjects:
            if isinstance(o, cls):
                yield o

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['moresystems']
        return state

    def __setstate__(self, state):
        self.moresystems = []
        # this is so very, very evil.
        # see doc/extreme-pickling-pain.txt for more.
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
