from pydoctor import model, ast_pp

from compiler import visitor, transformer, ast
import os, sys, posixpath

class ModuleVistor(object):
    def __init__(self, builder, modname):
        self.builder = builder
        self.system = builder.system
        self.modname = modname
        self.morenodes = []

    def default(self, node):
        for child in node.getChildNodes():
            self.visit(child)

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
        rawbases = []
        bases = []
        baseobjects = []
        current = self.builder.current
        for n in node.bases:
            str_base = ast_pp.pp(n)
            rawbases.append(str_base)
            base = current.dottedNameToFullName(str_base)
            bases.append(base)
            bob = current.resolveDottedName(base)
            if not bob and self.system.options.resolvealiases:
                bob = self.system.allobjects.get(self.system.resolveAlias(base))
            if bob:
                assert (bob.parentMod is self.builder.currentMod or
                        bob.parentMod.processed)
            baseobjects.append(bob)

        cls = self.builder.pushClass(node.name, node.doc)
        if node.lineno is not None:
            cls.linenumber = node.lineno
        if cls.parentMod.sourceHref:
            cls.sourceHref = cls.parentMod.sourceHref + '#L' + str(cls.linenumber)
        cls.rawbases = rawbases
        cls.bases = bases
        cls.baseobjects = baseobjects
        for b in cls.baseobjects:
            if b is not None:
                b.subclasses.append(cls)
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
                assert mod.processed
                for n in mod.contents:
                    name2fullname[n] = modname + '.' + n
                return
            if asname is None:
                asname = fromname
            if isinstance(self.builder.current, model.Module) and \
                   self.builder.current.all is not None and \
                   asname in self.builder.current.all and \
                   modname in self.system.allobjects:
                mod = self.system.allobjects[modname]
                if isinstance(mod, model.Module) and fromname in mod.contents:
                    print 'moving', mod.contents[fromname], 'into', self.builder.current
                    # this code attempts to preserve "rather a lot" of
                    # invariants assumed by various bits of pydoctor and that
                    # are of course not written down anywhere :/
                    ob = mod.contents[fromname]
                    targetmod = self.builder.current
                    del self.system.allobjects[ob.fullName()]
                    ob.parent = ob.parentMod = targetmod
                    ob.prefix = targetmod.fullName() + '.'
                    ob.name = asname
                    self.system.allobjects[ob.fullName()] = ob
                    del mod.contents[fromname]
                    mod.orderedcontents.remove(ob)
                    mod._name2fullname[fromname] = ob.fullName()
                    targetmod.contents[asname] = ob
                    targetmod.orderedcontents.append(ob)
            else:
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
                    fullname = '.'.join(parts)
                    name2fullname[asname] = '.'.join(parts)
            else:
                name2fullname[asname] = fullname

    def visitFunction(self, node):
        func = self.builder.pushFunction(node.name, node.doc)
        if node.lineno is not None:
            func.linenumber = node.lineno
        if func.parentMod.sourceHref:
            func.sourceHref = func.parentMod.sourceHref + '#L' + str(func.linenumber)
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
        #self.postpone(func, node.code)
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
        self.currentMod = None
        self._stack = []
        self.ast_cache = {}

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
        self.push(obj)
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
        self.pop(self.current)

    def push(self, obj):
        self._stack.append(self.current)
        self.current = obj
        if isinstance(obj, model.Module):
            assert self.currentMod is None
            self.currentMod = obj
        elif self.currentMod is not None:
            if obj.parentMod is not None:
                assert obj.parentMod is self.currentMod
            else:
                obj.parentMod = self.currentMod
        else:
            assert obj.parentMod is None

    def pop(self, obj):
        assert self.current is obj, "%r is not %r"%(self.current, obj)
        self.current = self._stack.pop()
        if isinstance(obj, model.Module):
            self.currentMod = None

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
        pass

    def processModuleAST(self, ast, moduleName):
        visitor.walk(ast, self.ModuleVistor(self, moduleName))

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

    def parseFile(self, filePath):
        if filePath in self.ast_cache:
            return self.ast_cache[filePath]
        try:
            ast = transformer.parseFile(filePath)
        except (SyntaxError, ValueError):
            self.warning("cannot parse", filePath)
            ast = None
        self.ast_cache[filePath] = ast
        return ast


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
        if self.system.sourcebase is None:
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


    def preprocessDirectory(self, dirpath):
        assert self.system.state in ['blank', 'preparse']
        found_init_dot_py = False
        if not os.path.exists(dirpath):
            raise Exception, "package path %r does not exist!"%(dirpath,)
        if os.path.basename(dirpath):
            package = self.pushPackage(os.path.basename(dirpath), None)
            package.filepath = dirpath
            self.setSourceHref(package)
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
                self.setSourceHref(mod)
                self.popModule()
        if package:
            self.popPackage()
        if not found_init_dot_py:
            raise Exception, "you must pass a package directory to preprocessDirectory"
        self.system.state = 'preparse'

    def analyseImports(self):
        assert self.system.state in ['preparse']
        modlist = list(self.system.objectsOfType(model.Module))
        for i, mod in enumerate(modlist):
            self.push(mod.parent)
            isf = ImportFinder(self, mod)
            ast = self.parseFile(mod.filepath)
            if not ast:
                continue
            print '\r', i+1, '/', len(modlist), 'modules parsed',
            sys.stdout.flush()
            visitor.walk(ast, isf)
            self.pop(mod.parent)
        print
        self.system.state = 'imported'

    def extractDocstrings(self):
        assert self.system.state in ['imported']
        # and so much more...
        modlist = list(self.system.objectsOfType(model.Module))
        newlist = toposort([m.fullName() for m in modlist], self.system.importgraph)

        for i, mod in enumerate(newlist):
            mod = self.system.allobjects[mod]
            self.push(mod.parent)
            ast = self.parseFile(mod.filepath)
            if not ast:
                continue
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
        self.analyseImports()
        self.extractDocstrings()
        self.finalStateComputations()

model.System.defaultBuilder = ASTBuilder


class ImportFinder(object):
    def __init__(self, builder, mod):
        self.builder = builder
        self.system = builder.system
        self.mod = mod
        self.classLevel = 0

    def default(self, node):
        for child in node.getChildNodes():
            self.visit(child)

    def visitFunction(self, node):
        pass

    def visitClass(self, node):
        self.classLevel += 1
        self.default(node)
        self.classLevel -= 1

    def visitFrom(self, node):
        modname = self.builder.expandModname(node.modname, False)
        mod = self.system.allobjects.get(modname)
        if mod is None:
            return
        if isinstance(mod, model.Module):
            self.system.importgraph.setdefault(
                self.mod.fullName(), set()).add(modname)
        else:
            for fromname, asname in node.names:
                m = modname + '.' + fromname
                if isinstance(self.system.allobjects.get(m), model.Module):
                    self.system.importgraph.setdefault(
                        self.mod.fullName(), set()).add(m)

    def visitImport(self, node):
        for fromname, asname in node.names:
            modname = self.builder.expandModname(fromname)
            if modname in self.system.allobjects:
                self.system.importgraph.setdefault(
                    self.mod.fullName(), set()).add(modname)

    def visitAssign(self, node):
        if not len(node.nodes) == 1 or \
               not self.classLevel == 0 or \
               not isinstance(node.nodes[0], ast.AssName) or \
               not node.nodes[0].name == '__all__' or \
               not isinstance(node.expr, ast.List):
            self.default(node)
            return
        items = node.expr.nodes
        names = []
        for item in items:
            if not isinstance(item, ast.Const) or not isinstance(item.value, str):
                self.default(node)
                return
            names.append(item.value)
        #print self.mod, names
        self.mod.all = names

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
        for j in edges.get(i, set()):
            if j in input:
                del input[j]
                p(j)
        output.append(i)
    while input:
        p(input.popitem()[0])
    return output
