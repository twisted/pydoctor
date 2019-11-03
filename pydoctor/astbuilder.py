"""Convert ASTs into L{pydoctor.model.Documentable} instances."""

from __future__ import print_function

import ast

import astor
from pydoctor import model


def parseFile(path):
    """Duplicate of L{compiler.parseFile} that uses L{MyTransformer}."""
    f = open(path, "U")
    src = f.read() + "\n"
    f.close()
    return parse(src)


def parse(buf):
    """Duplicate of L{compiler.parse} that uses L{MyTransformer}."""
    return ast.parse(buf)


def node2dottedname(node):
    return astor.to_source(node).strip().split(".")

class ModuleVistor(ast.NodeVisitor):
    def __init__(self, builder, module):
        self.builder = builder
        self.system = builder.system
        self.module = module

    def default(self, node):
        for child in node.body:
            self.visit(child)

    def visit_Module(self, node):
        assert self.module.docstring is None

        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            self.module.docstring = node.body[0].value.s
        self.builder.push(self.module)
        self.default(node)
        self.builder.pop(self.module)

    def visit_ClassDef(self, node):
        rawbases = []
        bases = []
        baseobjects = []

        for n in node.bases:
            if isinstance(n, ast.Name):
                str_base = n.id
            else:
                str_base = astor.to_source(n).strip()

            rawbases.append(str_base)
            full_name = self.builder.current.expandName(str_base)
            bases.append(full_name)
            baseobj = self.system.objForFullName(full_name)
            if not isinstance(baseobj, model.Class):
                baseobj = None
            baseobjects.append(baseobj)

        doc = None
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            doc = node.body[0].value.s

        cls = self.builder.pushClass(node.name, doc)
        cls.decorators = []
        cls.rawbases = rawbases
        cls.bases = bases
        cls.baseobjects = baseobjects

        def node2data(node):
            dotted_name = node2dottedname(node)
            if dotted_name is None:
                return None
            dotted_name = '.'.join(dotted_name)
            full_name = self.builder.current.expandName(dotted_name)
            obj = self.system.objForFullName(full_name)
            return (dotted_name, full_name, obj)

        if node.decorator_list:
            for decnode in node.decorator_list:
                if isinstance(decnode, ast.Call):
                    args = []
                    for arg in decnode.args:
                        args.append(node2data(arg))
                    base = node2data(decnode.func)
                else:
                    base = node2data(decnode)
                    args = None
                cls.decorators.append((base, args))
        cls.raw_decorators = node.decorator_list if node.decorator_list else []

        if node.lineno is not None:
            cls.linenumber = node.lineno
        if cls.parentMod.sourceHref:
            cls.sourceHref = cls.parentMod.sourceHref + '#L' + \
                             str(cls.linenumber)
        for b in cls.baseobjects:
            if b is not None:
                b.subclasses.append(cls)
        self.default(node)
        self.builder.popClass()

    def visit_ImportFrom(self, node):
        if not isinstance(self.builder.current, model.CanContainImportsDocumentable):
            self.warning("processing import statement in odd context")
            return

        if node.module is None:
            return
        modname = self.builder.expandModname(node.module)
        mod = self.system.getProcessedModule(modname)
        if mod is not None:
            assert mod.state in [model.PROCESSING, model.PROCESSED]
            expandName = mod.expandName
        else:
            expandName = lambda name: modname + '.' + name
        _localNameToFullName = self.builder.current._localNameToFullName_map
        for al in node.names:
            fromname, asname = al.name, al.asname
            if fromname == '*':
                if mod is None:
                    self.builder.warning("import * from unknown", modname)
                    return
                self.builder.warning("import *", modname)
                if mod.all is not None:
                    names = mod.all
                else:
                    names = mod.contents.keys() + mod._localNameToFullName_map.keys()
                    names = [k for k in names if not k.startswith('_')]
                for n in names:
                    _localNameToFullName[n] = expandName(n)
                return
            if asname is None:
                asname = fromname
            if isinstance(self.builder.current, model.Module) and \
                   self.builder.current.all is not None and \
                   asname in self.builder.current.all and \
                   modname in self.system.allobjects:
                mod = self.system.allobjects[modname]
                if isinstance(mod, model.Module) and \
                       fromname in mod.contents and \
                       (mod.all is None or fromname not in mod.all):
                    self.system.msg(
                        "astbuilder",
                        "moving %r into %r"
                        % (mod.contents[fromname].fullName(),
                           self.builder.current.fullName()))
                    ob = mod.contents[fromname]
                    ob.reparent(self.builder.current, asname)
                    continue
            if isinstance(
                self.system.objForFullName(modname), model.Package):
                self.system.getProcessedModule(modname + '.' + fromname)
            _localNameToFullName[asname] = expandName(fromname)

    def visit_Import(self, node):
        """Process an import statement.

        The grammar for the statement is roughly:

        mod_as := DOTTEDNAME ['as' NAME]
        import_stmt := 'import' mod_as (',' mod_as)*

        and this is translated into a node which is an instance of Import wih
        an attribute 'names', which is in turn a list of 2-tuples
        (dotted_name, as_name) where as_name is None if there was no 'as foo'
        part of the statement.
        """
        if not isinstance(self.builder.current, model.CanContainImportsDocumentable):
            self.warning("processing import statement in odd context")
            return
        _localNameToFullName = self.builder.current._localNameToFullName_map
        for al in node.names:
            fromname, asname = al.name, al.asname
            fullname = self.builder.expandModname(fromname)

            mod = self.system.getProcessedModule(fullname)
            if mod is not None:
                assert mod.state in [model.PROCESSING, model.PROCESSED]
                expandName = mod.expandName
            else:
                expandName = lambda name: name
            if asname is None:
                asname = fromname.split('.', 1)[0]
                # aaaaargh! python sucks.
                parts = fullname.split('.')
                for i, part in enumerate(fullname.split('.')[::-1]):
                    if part == asname:
                        fullname = '.'.join(parts[:len(parts)-i])
                        _localNameToFullName[asname] = expandName(fullname)
                        break
                else:
                    fullname = '.'.join(parts)
                    _localNameToFullName[asname] = '.'.join(parts)
            else:
                _localNameToFullName[asname] = fullname


    def _handleOldSchoolDecoration(self, target, expr):
        if isinstance(self.builder.current, model.Class):
            if not isinstance(expr, ast.Call):
                return
            func = expr.func
            if not isinstance(func, ast.Name):
                return
            func = func.id
            args = expr.args
            if len(args) != 1:
                return
            arg, = args
            if not isinstance(arg, ast.Name):
                return
            arg = arg.id
            if target == arg and func in ['staticmethod', 'classmethod']:
                target = self.builder.current.contents.get(target)
                if target and isinstance(target, model.Function):
                    if target.kind != 'Method':
                        self.system.msg('ast', 'XXX')
                    else:
                        target.kind = func.title().replace('m', ' M')

    def _handleAliasing(self, target, expr):
        dottedname = node2dottedname(expr)
        if dottedname is None:
            return
        if not isinstance(self.builder.current, model.CanContainImportsDocumentable):
            return
        c = self.builder.current
        base = None
        if dottedname[0] in c._localNameToFullName_map:
            base = c._localNameToFullName_map[dottedname[0]]
        elif dottedname[0] in c.contents:
            base = c.contents[dottedname[0]].fullName()
        if base:
            c._localNameToFullName_map[target] = '.'.join([base] + dottedname[1:])

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            return
        if not isinstance(node.targets[0], ast.Name):
            return
        target = node.targets[0].id
        self._handleOldSchoolDecoration(target, node.value)
        self._handleAliasing(target, node.value)

    def visit_FunctionDef(self, node):
        doc = ""
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            doc = node.body[0].value.s
        func = self.builder.pushFunction(node.name, doc)
        func.decorators = node.decorator_list
        if isinstance(func.parent, model.Class) and node.decorator_list:
            isclassmethod = False
            isstaticmethod = False
            for d in node.decorator_list:
                if isinstance(d, ast.Name):
                    if d.id == 'classmethod':
                        isclassmethod = True
                    elif d.id == 'staticmethod':
                        isstaticmethod = True
            if isstaticmethod:
                if isclassmethod:
                    self.system.msg(
                        'ast', '%r is both class- and static-method?'%(
                        func.fullName(),), thresh=-1)
                else:
                    func.kind = 'Static Method'
            elif isclassmethod:
                func.kind = 'Class Method'
        if node.lineno is not None:
            func.linenumber = node.lineno
        if func.parentMod.sourceHref:
            func.sourceHref = func.parentMod.sourceHref + '#L' + \
                              str(func.linenumber)

        args = []

        for arg in node.args.args:
            if isinstance(arg, (ast.Tuple, ast.List)):
                args.append([x.id for x in arg.elts])
            elif isinstance(arg, ast.Name):
                args.append(arg.id)

        defaults = []

        for default in node.args.defaults:
            if isinstance(default, ast.Num):
                defaults.append(str(default.n))
            else:
                defaults.append(astor.to_source(default).strip())

        func.argspec = (args, node.args.vararg, node.args.kwarg, tuple(defaults))
        self.builder.popFunction()

class ASTBuilder(object):
    ModuleVistor = ModuleVistor

    def __init__(self, system):
        self.system = system
        self.current = None
        self.currentMod = None
        self._stack = []
        self.ast_cache = {}

    def _push(self, cls, name, docstring):
        obj = cls(self.system, name, docstring, self.current)
        self.system.addObject(obj)
        self.push(obj)
        return obj

    def _pop(self, cls):
        assert isinstance(self.current, cls)
        self.pop(self.current)

    def push(self, obj):
        self._stack.append(self.current)
        self.current = obj
        if isinstance(obj, model.Module):
            assert self.currentMod is None
            obj.parentMod = self.currentMod = obj
        elif self.currentMod is not None:
            if obj.parentMod is not None:
                assert obj.parentMod is self.currentMod
            else:
                obj.parentMod = self.currentMod
        else:
            assert obj.parentMod is None
        # Method-level import to avoid a circular dependency.
        from pydoctor import epydoc2stan
        for attrobj in epydoc2stan.extract_fields(obj):
            self.system.addObject(attrobj)

    def pop(self, obj):
        assert self.current is obj, "%r is not %r"%(self.current, obj)
        self.current = self._stack.pop()
        if isinstance(obj, model.Module):
            self.currentMod = None

    def pushClass(self, name, docstring):
        return self._push(self.system.Class, name, docstring)
    def popClass(self):
        self._pop(self.system.Class)

    def pushModule(self, name, docstring):
        return self._push(self.system.Module, name, docstring)
    def popModule(self):
        self._pop(self.system.Module)

    def pushFunction(self, name, docstring):
        return self._push(self.system.Function, name, docstring)
    def popFunction(self):
        self._pop(self.system.Function)

    def pushPackage(self, name, docstring):
        return self._push(self.system.Package, name, docstring)
    def popPackage(self):
        self._pop(self.system.Package)

    def warning(self, type, detail):
        self.system._warning(self.current, type, detail)

    def processModuleAST(self, ast, mod):
        findAll(ast, mod)

        self.ModuleVistor(self, mod).visit(ast)

    def expandModname(self, modname):
        if '.' in modname:
            prefix, suffix = modname.split('.', 1)
            suffix = '.' + suffix
        else:
            prefix, suffix = modname, ''
        package = self.current.parentMod.parent
        while package is not None:
            if prefix in package.contents:
                self.warning("local import", modname)
                return package.contents[prefix].fullName() + suffix
            package = package.parent
        return modname

    def parseFile(self, filePath):
        if filePath in self.ast_cache:
            return self.ast_cache[filePath]
        try:
            ast = parseFile(filePath)
        except (SyntaxError, ValueError):
            self.warning("cannot parse", filePath)
            ast = None
        self.ast_cache[filePath] = ast
        return ast

model.System.defaultBuilder = ASTBuilder

def findAll(modast, mod):
    """Find and attempt to parse into a list of names the __all__ of a module's AST."""
    for node in modast.body:
        if isinstance(node, ast.Assign) and \
               len(node.targets) == 1 and \
               isinstance(node.targets[0], ast.Name) and \
               node.targets[0].id == '__all__':
            if mod.all is not None:
                mod.system.msg('all', "multiple assignments to %s.__all__ ??"%(mod.fullName(),))
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                mod.system.msg('all', "couldn't parse %s.__all__"%(mod.fullName(),))
                continue
            items = node.value.elts
            names = []
            for item in items:
                if not isinstance(item, ast.Str):
                    mod.system.msg('all', "couldn't parse %s.__all__"%(mod.fullName(),))
                    continue
                names.append(item.s)
                mod.all = names
