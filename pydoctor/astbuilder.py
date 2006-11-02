from pydoctor import model, ast_pp

from compiler import visitor, transformer
import os, sys

class ModuleVistor(object):
    def __init__(self, builder, modname):
        self.builder = builder
        self.system = builder.system
        self.modname = modname
        self.morenodes = []

    def default(self, node):
        for child in node.getChildNodes():
            self.visit(child)

    def postpone(self, docable, node):
        self.morenodes.append((docable, node))

    def visitModule(self, node):
        if self.builder.current and self.modname in self.builder.current.contents:
            m = self.builder.current.contents[self.modname]
            assert m.docstring is None
            m.docstring = node.doc
            self.builder.push(m)
            self.default(node)
            self.builder.pop(m)
        else:
            if not self.builder.current:
                roots = [x for x in self.system.rootobjects if x.name == self.modname]
                if roots:
                    mod, = roots
                    self.builder.push(mod)
                    self.default(node)
                    self.builder.pop(mod)
                    return
            self.builder.pushModule(self.modname, node.doc)
            self.default(node)
            self.builder.popModule()

    def visitClass(self, node):
        cls = self.builder.pushClass(node.name, node.doc)
        if node.lineno is not None:
            cls.linenumber = node.lineno
        for n in node.bases:
            str_base = ast_pp.pp(n)
            cls.rawbases.append(str_base)
            base = cls.dottedNameToFullName(str_base)
            cls.bases.append(base)
        self.default(node)
        self.builder.popClass()

    def visitFrom(self, node):
        modname = self.builder.expandModname(node.modname)
        name2fullname = self.builder.current._name2fullname
        for fromname, asname in node.names:
            if fromname == '*':
                self.builder.warning("import *", modname)
                if modname not in self.system.allobjects:
                    return
                mod = self.system.allobjects[modname]
                if isinstance(mod, model.Package):
                    self.builder.warning("import * from a package", modname)
                    return
                # this might fail if you have an import-* cycle, or if
                # you're just not running the import star finder to
                # save time
                if mod.processed:
                    for n in mod.contents:
                        name2fullname[n] = modname + '.' + n
                else:
                    self.builder.warning("unresolvable import *", modname)
                return
            if asname is None:
                asname = fromname
            name2fullname[asname] = modname + '.' + fromname

    def visitImport(self, node):
        name2fullname = self.builder.current._name2fullname
        for fromname, asname in node.names:
            fullname = self.builder.expandModname(fromname)
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
        func = self.builder.pushFunction(node.name, node.doc)
        if node.lineno is not None:
            func.linenumber = node.lineno
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
                self.builder.warning("unparseable default", "%s: %s %r"%(e.__class__.__name__,
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
        self.builder.popFunction()

class ASTBuilder(object):
    Class = model.Class
    Module = model.Module
    Package = model.Package
    Function = model.Function
    ModuleVistor = ModuleVistor

    def __init__(self, system):
        self.system = system
        self.current = None
        self._stack = []

    def _push(self, cls, name, docstring):
        if self.current:
            if isinstance(self.current, model.Module) and \
                   self.current.name == '__init__':
                prefix = self.current.parent.fullName() + '.'
            else:
                prefix = self.current.fullName() + '.'
            parent = self.current
        else:
            prefix = ''
            parent = None
        obj = cls(self.system, prefix, name, docstring, parent)
        if parent:
            parent.orderedcontents.append(obj)
            parent.contents[name] = obj
            parent._name2fullname[name] = obj.fullName()
        else:
            self.system.rootobjects.append(obj)
        self.current = obj
        self.system.orderedallobjects.append(obj)
        fullName = obj.fullName()
        #print 'push', cls.__name__, fullName
        if fullName in self.system.allobjects:
            obj = self.handleDuplicate(obj)
        else:
            self.system.allobjects[obj.fullName()] = obj
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
        while (fn + ' ' + str(i)) in self.system.allobjects:
            i += 1
        prev = self.system.allobjects[obj.fullName()]
        prev.name = obj.name + ' ' + str(i)
        self.system.allobjects[prev.fullName()] = prev
        self.warning("duplicate", self.system.allobjects[obj.fullName()])
        self.system.allobjects[obj.fullName()] = obj
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

    def warning(self, type, detail):
        self.system._warning(self.current, type, detail)

    def _finalStateComputations(self):
        if self.system.options.resolvealiases:
            self.system.resolveAliases()
        self.recordBasesAndSubclasses()

    def recordBasesAndSubclasses(self):
        for cls in self.system.objectsOfType(model.Class):
            for n in cls.bases:
                o = cls.parent.resolveDottedName(n, verbose=False)
                cls.baseobjects.append(o)
                if o:
                    o.subclasses.append(cls)
        for cls in self.system.objectsOfType(model.Class):
            for name, meth in cls.contents.iteritems():
                if meth.docstring is None:
                    for b in cls.allbases():
                        if name in b.contents:
                            overriddenmeth = b.contents[name]
                            if overriddenmeth.docstring is not None:
                                meth.docstring = overriddenmeth.docstring
                                meth.docsource = overriddenmeth
                                break
                            
                    

    def processModuleAST(self, ast, moduleName):
        mv = self.ModuleVistor(self, moduleName)
        visitor.walk(ast, mv)
        while mv.morenodes:
            obj, node = mv.morenodes.pop(0)
            self.push(obj)
            mv.visit(node)
            self.pop(obj)

    def expandModname(self, modname, givewarning=True):
        c = self.current
        if '.' in modname:
            prefix, suffix = modname.split('.', 1)
            suffix = '.' + suffix
        else:
            prefix, suffix = modname, ''
        while c is not None and not isinstance(c, model.Package):
            c = c.parent
        while c is not None:
            if prefix in c.contents:
                break
            c = c.parent
        if c is not None:
            if givewarning:
                self.warning("local import", modname)
            return c.contents[prefix].fullName() + suffix
        else:
            return prefix + suffix

    def preprocessDirectory(self, dirpath):
        assert self.system.state in ['blank', 'preparse']
        found_init_dot_py = False
        if os.path.basename(dirpath):
            package = self.pushPackage(os.path.basename(dirpath), None)
        else:
            package = None
        for fname in os.listdir(dirpath):
            fullname = os.path.join(dirpath, fname)
            if os.path.isdir(fullname) and os.path.exists(os.path.join(fullname, '__init__.py')) and fname != 'test':
                self.preprocessDirectory(fullname)
            elif fname.endswith('.py') and not fname.startswith('.'):
                if fname == '__init__.py':
                    found_init_dot_py = True
                modname = os.path.splitext(fname)[0]
                mod = self.pushModule(modname, None)
                mod.filepath = fullname
                mod.processed = False
                self.popModule()
        if package:
            self.popPackage()
        if not found_init_dot_py:
            raise Exception, "you must pass a package directory to preprocessDirectory"
        self.system.state = 'preparse'

    def findImportStars(self):
        assert self.system.state in ['preparse']
        modlist = list(self.system.objectsOfType(model.Module))
        for i, mod in enumerate(modlist):
            self.push(mod.parent)
            isf = ImportStarFinder(self, mod.fullName())
            try:
                ast = transformer.parseFile(mod.filepath)
            except (SyntaxError, ValueError):
                self.warning("cannot parse", mod.filepath)
            print '\r', i+1, '/', len(modlist), 'modules parsed',
            sys.stdout.flush()
            visitor.walk(ast, isf)
            self.pop(mod.parent)
        print
        self.system.state = 'importstarred'

    def extractDocstrings(self):
        assert self.system.state in ['preparse', 'importstarred']
        # and so much more...
        modlist = list(self.system.objectsOfType(model.Module))
        newlist = toposort([m.fullName() for m in modlist], self.system.importstargraph)

        for i, mod in enumerate(newlist):
            mod = self.system.allobjects[mod]
            self.push(mod.parent)
            try:
                ast = transformer.parseFile(mod.filepath)
            except (SyntaxError, ValueError):
                self.warning("cannot parse", mod.filepath)
            self.processModuleAST(ast, mod.name)
            print '\r', i+1, '/', len(newlist), 'modules parsed',
            print sum(len(v) for v in self.system.warnings.itervalues()), 'warnings', 
            sys.stdout.flush()
            mod.processed = True
            self.pop(mod.parent)
        print
        self.system.state = 'parsed'

    def finalStateComputations(self):
        assert self.system.state in ['parsed']
        self._finalStateComputations()
        self.system.state = 'finalized'

    def processDirectory(self, dirpath):
        self.preprocessDirectory(dirpath)
        self.findImportStars()
        self.extractDocstrings()
        self.finalStateComputations()

model.System.defaultBuilder = ASTBuilder


class ImportStarFinder(object):
    def __init__(self, builder, modfullname):
        self.builder = builder
        self.system = builder.system
        self.modfullname = modfullname

    def visitFrom(self, node):
        if node.names[0][0] == '*':
            modname = self.builder.expandModname(node.modname, False)
            self.system.importstargraph.setdefault(
                self.modfullname, []).append(modname)

def fromText(src, modname='<test>', system=None):
    if system is None:
        _system = System()
    else:
        _system = system
    processModuleAst(parse(src), modname, _system)
    if system is None:
        _system.finalStateComputations()
    return _system.rootobjects[0]

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
