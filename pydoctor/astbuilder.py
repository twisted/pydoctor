"""Convert ASTs into L{pydoctor.model.Documentable} instances."""

from __future__ import print_function

import ast
from itertools import chain

import astor
from pydoctor import epydoc2stan, model
from six import string_types


def parseFile(path):
    """Parse the contents of a Python source file."""
    with open(path, 'rb') as f:
        src = f.read() + b'\n'
    return parse(src)


def parse(buf):
    """Parse the contents of a Unicode or bytes string."""
    return ast.parse(buf)


def node2dottedname(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    else:
        return None
    if len(parts) == 1 and parts[0] in ('True', 'False', 'None'):
        # On Python 3, these are NameConstant nodes, but on Python 2
        # they are Name nodes.
        return None
    parts.reverse()
    return parts


def node2fullname(expr, ctx):
    dottedname = node2dottedname(expr)
    if dottedname is None:
        return None
    base = ctx.expandName(dottedname[0])
    if base:
        return '.'.join([base] + dottedname[1:])
    else:
        return None


class ModuleVistor(ast.NodeVisitor):
    def __init__(self, builder, module):
        self.builder = builder
        self.system = builder.system
        self.module = module

    def default(self, node):
        self.currAttr = None
        for child in node.body:
            self.newAttr = None
            self.visit(child)
            self.currAttr = self.newAttr
        self.newAttr = None

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

        cls = self.builder.pushClass(node.name, doc, node.lineno)
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

        for b in cls.baseobjects:
            if b is not None:
                b.subclasses.append(cls)
        self.default(node)
        self.builder.popClass()

    def visit_ImportFrom(self, node):
        if not isinstance(self.builder.current, model.CanContainImportsDocumentable):
            self.builder.warning("processing import statement in odd context",
                                 str(self.builder.current))
            return

        if node.module is None:
            return
        modname = self.builder.expandModname(node.module)
        mod = self.system.getProcessedModule(modname)
        if mod is not None:
            assert mod.state in [model.ProcessingState.PROCESSING,
                                 model.ProcessingState.PROCESSED]
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
                    names = (
                        k
                        for k in chain(mod.contents.keys(),
                                       mod._localNameToFullName_map.keys())
                        if not k.startswith('_')
                        )
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
            self.builder.warning("processing import statement in odd context",
                                 str(self.builder.current))
            return
        _localNameToFullName = self.builder.current._localNameToFullName_map
        for al in node.names:
            fromname, asname = al.name, al.asname
            fullname = self.builder.expandModname(fromname)

            mod = self.system.getProcessedModule(fullname)
            if mod is not None:
                assert mod.state in [model.ProcessingState.PROCESSING,
                                     model.ProcessingState.PROCESSED]
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
        if not isinstance(expr, ast.Call):
            return False
        func = expr.func
        if not isinstance(func, ast.Name):
            return False
        func = func.id
        args = expr.args
        if len(args) != 1:
            return False
        arg, = args
        if not isinstance(arg, ast.Name):
            return False
        arg = arg.id
        if target == arg and func in ['staticmethod', 'classmethod']:
            target = self.builder.current.contents.get(target)
            if isinstance(target, model.Function):
                if target.kind != 'Method':
                    self.system.msg('ast', 'XXX')
                else:
                    target.kind = func.title().replace('m', ' M')
                    return True
        return False

    def _handleAliasing(self, target, expr):
        ctx = self.builder.current
        full_name = node2fullname(expr, ctx)
        if full_name is None:
            return False
        ctx._localNameToFullName_map[target] = full_name
        return True

    def _handleModuleVar(self, target, annotation, lineno):
        obj = self.builder.current.resolveName(target)
        if obj is None:
            obj = self.builder.addAttribute(target, None, None)
        if isinstance(obj, model.Attribute):
            obj.kind = 'Variable'
            obj.annotation = annotation
            obj.setLineNumber(lineno)
            self.newAttr = obj

    def _handleAssignmentInModule(self, target, annotation, expr, lineno):
        if not self._handleAliasing(target, expr):
            self._handleModuleVar(target, annotation, lineno)

    def _handleClassVar(self, target, annotation, lineno):
        obj = self.builder.current.contents.get(target)
        if not isinstance(obj, model.Attribute):
            obj = self.builder.addAttribute(target, None, None)
        if obj.kind is None:
            obj.kind = 'Class Variable'
        obj.annotation = annotation
        obj.setLineNumber(lineno)
        self.newAttr = obj

    def _handleInstanceVar(self, target, annotation, lineno):
        func = self.builder.current
        if not isinstance(func, model.Function):
            return
        cls = func.parent
        if not isinstance(cls, model.Class):
            return
        obj = cls.contents.get(target)
        if obj is None:
            obj = self.builder.addAttribute(target, None, None, cls)
        if isinstance(obj, model.Attribute):
            obj.kind = 'Instance Variable'
            obj.annotation = annotation
            obj.setLineNumber(lineno)
            self.newAttr = obj

    def _handleAssignmentInClass(self, target, annotation, expr, lineno):
        if not self._handleAliasing(target, expr):
            self._handleClassVar(target, annotation, lineno)

    def _handleAssignment(self, targetNode, annotation, expr, lineno):
        if isinstance(targetNode, ast.Name):
            target = targetNode.id
            scope = self.builder.current
            if isinstance(scope, model.Module):
                self._handleAssignmentInModule(target, annotation, expr, lineno)
            elif isinstance(scope, model.Class):
                if not self._handleOldSchoolDecoration(target, expr):
                    self._handleAssignmentInClass(target, annotation, expr, lineno)
        elif isinstance(targetNode, ast.Attribute):
            value = targetNode.value
            if isinstance(value, ast.Name) and value.id == 'self':
                self._handleInstanceVar(targetNode.attr, annotation, lineno)

    def visit_Assign(self, node):
        lineno = node.lineno
        expr = node.value
        annotation = _annotation_from_attrib(expr, self.builder.current)
        if annotation is None:
            annotation = _infer_type(expr)
        for target in node.targets:
            if isinstance(target, ast.Tuple):
                for elem in target.elts:
                    # Note: We skip type and aliasing analysis for this case,
                    #       but we do record line numbers.
                    self._handleAssignment(elem, None, None, lineno)
            else:
                self._handleAssignment(target, annotation, expr, lineno)

    def visit_AnnAssign(self, node):
        annotation = _unstring_annotation(node.annotation)
        self._handleAssignment(node.target, annotation, node.value, node.lineno)

    def visit_Expr(self, node):
        value = node.value
        if isinstance(value, ast.Str):
            attr = self.currAttr
            if attr is not None:
                attr.docstring = value.s

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        doc = None
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            doc = node.body[0].value.s
        func = self.builder.pushFunction(node.name, doc, node.lineno)
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

        args = []

        for arg in node.args.args:
            if isinstance(arg, (ast.Tuple, ast.List)):
                args.append([x.id for x in arg.elts])
            elif isinstance(arg, ast.Name):
                args.append(arg.id)
            else:
                args.append(arg.arg)

        varargname = node.args.vararg
        if varargname and not isinstance(varargname, string_types):
            varargname = varargname.arg

        kwargname = node.args.kwarg
        if kwargname and not isinstance(kwargname, string_types):
            kwargname = kwargname.arg

        defaults = []

        for default in node.args.defaults:
            if isinstance(default, ast.Num):
                defaults.append(str(default.n))
            else:
                defaults.append(astor.to_source(default).strip())

        func.argspec = (args, varargname, kwargname, tuple(defaults))
        self.default(node)
        self.builder.popFunction()


def _annotation_from_attrib(expr, ctx):
    """Get the type of an C{attr.ib} definition.
    @param expr: The expression's AST.
    @param ctx: The context in which this expression is evaluated.
    @return: A type annotation, or None if the expression is not
             an C{attr.ib} definition or contains no type information.
    """
    if isinstance(expr, ast.Call) \
            and node2fullname(expr.func, ctx) in ('attr.ib', 'attr.attrib'):
        keywords = {kw.arg: kw.value for kw in expr.keywords}
        typ = keywords.get('type')
        if typ is not None:
            return _unstring_annotation(typ)
        default = keywords.get('default')
        if default is not None:
            return _infer_type(default)
    return None


class _AnnotationStringParser(ast.NodeTransformer):
    def visit_Str(self, node):
        expr, = ast.parse(node.s).body
        return self.visit(expr.value)

_unstring_annotation = _AnnotationStringParser().visit


def _infer_type(expr):
    """Infer an expression's type.
    @param expr: The expression's AST.
    @return: A type annotation, or None if the expression has no obvious type.
    """

    try:
        value = ast.literal_eval(expr)
    except ValueError:
        return None
    else:
        return _annotation_for_value(value)

def _annotation_for_value(value):
    if value is None:
        return None
    name = type(value).__name__
    if isinstance(value, (dict, list, set, tuple)):
        name = name.capitalize()
        ann_elem = _annotation_for_elements(value)
        if isinstance(value, dict):
            ann_value = _annotation_for_elements(value.values())
            if ann_value is None:
                ann_elem = None
            elif ann_elem is not None:
                ann_elem = ast.Tuple(elts=[ann_elem, ann_value])
        if ann_elem is not None:
            if name == 'Tuple':
                ann_elem = ast.Tuple(elts=[ann_elem, ast.Ellipsis()])
            return ast.Subscript(value=ast.Name(id=name),
                                 slice=ast.Index(value=ann_elem))
    return ast.Name(id=name)

def _annotation_for_elements(sequence):
    names = set()
    for elem in sequence:
        ann = _annotation_for_value(elem)
        if isinstance(ann, ast.Name):
            names.add(ann.id)
        else:
            # Nested sequences are too complex.
            return None
    if len(names) == 1:
        name = names.pop()
        return ast.Name(id=name)
    else:
        # Empty sequence or no uniform type.
        return None


class ASTBuilder(object):
    ModuleVistor = ModuleVistor

    def __init__(self, system):
        self.system = system
        self.current = None
        self.currentMod = None
        self._stack = []
        self.ast_cache = {}

    def _push(self, cls, name, docstring, lineno):
        obj = cls(self.system, name, docstring, self.current)
        self.system.addObject(obj)
        self.push(obj)
        obj.setLineNumber(lineno)
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
        if not isinstance(obj, model.Function):
            epydoc2stan.extract_fields(obj)

    def pop(self, obj):
        assert self.current is obj, "%r is not %r"%(self.current, obj)
        self.current = self._stack.pop()
        if isinstance(obj, model.Module):
            self.currentMod = None

    def pushClass(self, name, docstring, lineno):
        return self._push(self.system.Class, name, docstring, lineno)
    def popClass(self):
        self._pop(self.system.Class)

    def pushFunction(self, name, docstring, lineno):
        return self._push(self.system.Function, name, docstring, lineno)
    def popFunction(self):
        self._pop(self.system.Function)

    def addAttribute(self, target, docstring, kind, parent=None):
        if parent is None:
            parent = self.current
        system = self.system
        parentMod = self.currentMod
        attr = system.Attribute(system, target, docstring, parent)
        attr.kind = kind
        attr.parentMod = parentMod
        system.addObject(attr)
        return attr

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
