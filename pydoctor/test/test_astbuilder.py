from typing import Optional, Tuple, Type, overload
import ast
import textwrap

import astor

from twisted.python._pydoctor import TwistedSystem

from pydoctor import astbuilder, model
from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring, flatten
from pydoctor.epydoc.markup.epytext import Element, ParsedEpytextDocstring
from pydoctor.epydoc2stan import format_summary, get_parsed_type
from pydoctor.zopeinterface import ZopeInterfaceSystem

from . import CapSys, NotFoundLinker, posonlyargs, typecomment
import pytest


systemcls_param = pytest.mark.parametrize(
    'systemcls', (model.System, ZopeInterfaceSystem, TwistedSystem)
    )

def fromAST(
        ast: ast.Module,
        modname: str = '<test>',
        parent_name: Optional[str] = None,
        system: Optional[model.System] = None,
        buildercls: Optional[Type[astbuilder.ASTBuilder]] = None,
        systemcls: Type[model.System] = model.System
        ) -> model.Module:
    if system is None:
        _system = systemcls()
    else:
        _system = system
    if buildercls is None:
        buildercls = _system.defaultBuilder
    builder = buildercls(_system)
    if parent_name is None:
        full_name = modname
    else:
        full_name = f'{parent_name}.{modname}'
        # Set containing package as parent.
        builder.current = _system.allobjects[parent_name]
    mod: model.Module = builder._push(_system.Module, modname, 0)
    builder._pop(_system.Module)
    builder.processModuleAST(ast, mod)
    assert mod is _system.allobjects[full_name]
    mod.state = model.ProcessingState.PROCESSED
    if system is None:
        # Assume that an implicit system will only contain one module,
        # so post-process it as a convenience.
        _system.postProcess()
    return mod

def fromText(
        text: str,
        *,
        modname: str = '<test>',
        parent_name: Optional[str] = None,
        system: Optional[model.System] = None,
        buildercls: Optional[Type[astbuilder.ASTBuilder]] = None,
        systemcls: Type[model.System] = model.System
        ) -> model.Module:
    ast = astbuilder._parse(textwrap.dedent(text))
    return fromAST(ast, modname, parent_name, system, buildercls, systemcls)

def unwrap(parsed_docstring: ParsedEpytextDocstring) -> str:
    epytext = parsed_docstring._tree
    assert epytext is not None
    assert epytext.tag == 'epytext'
    assert len(epytext.children) == 1
    para = epytext.children[0]
    assert isinstance(para, Element)
    assert para.tag == 'para'
    assert len(para.children) == 1
    value = para.children[0]
    assert isinstance(value, str)
    return value

def to_html(
        parsed_docstring: ParsedDocstring,
        linker: DocstringLinker = NotFoundLinker()
        ) -> str:
    return flatten(parsed_docstring.to_stan(linker))

@overload
def type2str(type_expr: None) -> None: ...

@overload
def type2str(type_expr: ast.expr) -> str: ...

def type2str(type_expr: Optional[ast.expr]) -> Optional[str]:
    if type_expr is None:
        return None
    else:
        src = astor.to_source(type_expr)
        assert isinstance(src, str)
        return src.strip()

def ann_str_and_line(obj: model.Documentable) -> Tuple[str, int]:
    """Return the textual representation and line number of an object's
    type annotation.
    @param obj: Documentable object with a type annotation.
    """
    ann = obj.annotation # type: ignore[attr-defined]
    assert ann is not None
    return type2str(ann), ann.lineno

def test_node2fullname() -> None:
    """The node2fullname() function finds the full (global) name for
    a name expression in the AST.
    """

    mod = fromText('''
    class session:
        from twisted.conch.interfaces import ISession
    ''', modname='test')

    def lookup(expr: str) -> Optional[str]:
        node = ast.parse(expr, mode='eval')
        assert isinstance(node, ast.Expression)
        return astbuilder.node2fullname(node.body, mod)

    # None is returned for non-name nodes.
    assert lookup('123') is None
    # Local names are returned with their full name.
    assert lookup('session') == 'test.session'
    # A name that has no match at the top level is returned as-is.
    assert lookup('nosuchname') == 'nosuchname'
    # Unknown names are resolved as far as possible.
    assert lookup('session.nosuchname') == 'test.session.nosuchname'
    # Aliases are resolved on local names.
    assert lookup('session.ISession') == 'twisted.conch.interfaces.ISession'
    # Aliases are resolved on global names.
    assert lookup('test.session.ISession') == 'twisted.conch.interfaces.ISession'

@systemcls_param
def test_no_docstring(systemcls: Type[model.System]) -> None:
    # Inheritance of the docstring of an overridden method depends on
    # methods with no docstring having None in their 'docstring' field.
    mod = fromText('''
    def f():
        pass
    class C:
        def m(self):
            pass
    ''', modname='test', systemcls=systemcls)
    f = mod.contents['f']
    assert f.docstring is None
    m = mod.contents['C'].contents['m']
    assert m.docstring is None

@systemcls_param
def test_function_simple(systemcls: Type[model.System]) -> None:
    src = '''
    """ MOD DOC """
    def f():
        """This is a docstring."""
    '''
    mod = fromText(src, systemcls=systemcls)
    assert len(mod.contents) == 1
    func, = mod.contents.values()
    assert func.fullName() == '<test>.f'
    assert func.docstring == """This is a docstring."""
    assert func.is_async is False


@systemcls_param
def test_function_async(systemcls: Type[model.System]) -> None:
    src = '''
    """ MOD DOC """
    async def a():
        """This is a docstring."""
    '''
    mod = fromText(src, systemcls=systemcls)
    assert len(mod.contents) == 1
    func, = mod.contents.values()
    assert func.fullName() == '<test>.a'
    assert func.docstring == """This is a docstring."""
    assert func.is_async is True


@pytest.mark.parametrize('signature', (
    '()',
    '(*, a, b=None)',
    '(*, a=(), b)',
    '(a, b=3, *c, **kw)',
    '(f=True)',
    '(x=0.1, y=-2)',
    '(s=\'theory\', t="con\'text")',
    ))
@systemcls_param
def test_function_signature(signature: str, systemcls: Type[model.System]) -> None:
    """A round trip from source to inspect.Signature and back produces
    the original text.
    """
    mod = fromText(f'def f{signature}: ...', systemcls=systemcls)
    docfunc, = mod.contents.values()
    assert isinstance(docfunc, model.Function)
    assert str(docfunc.signature) == signature

@posonlyargs
@pytest.mark.parametrize('signature', (
    '(x, y, /)',
    '(x, y=0, /)',
    '(x, y, /, z, w)',
    '(x, y, /, z, w=42)',
    '(x, y, /, z=0, w=0)',
    '(x, y=3, /, z=5, w=7)',
    '(x, /, *v, a=1, b=2)',
    '(x, /, *, a=1, b=2, **kwargs)',
    ))
@systemcls_param
def test_function_signature_posonly(signature: str, systemcls: Type[model.System]) -> None:
    test_function_signature(signature, systemcls)


@pytest.mark.parametrize('signature', (
    '(a, a)',
    ))
@systemcls_param
def test_function_badsig(signature: str, systemcls: Type[model.System], capsys: CapSys) -> None:
    """When a function has an invalid signature, an error is logged and
    the empty signature is returned.

    Note that most bad signatures lead to a SyntaxError, which we cannot
    recover from. This test checks what happens if the AST can be produced
    but inspect.Signature() rejects the parsed parameters.
    """
    mod = fromText(f'def f{signature}: ...', systemcls=systemcls, modname='mod')
    docfunc, = mod.contents.values()
    assert isinstance(docfunc, model.Function)
    assert str(docfunc.signature) == '()'
    captured = capsys.readouterr().out
    assert captured.startswith("mod:1: mod.f has invalid parameters: ")


@systemcls_param
def test_class(systemcls: Type[model.System]) -> None:
    src = '''
    class C:
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src, systemcls=systemcls)
    assert len(mod.contents) == 1
    cls, = mod.contents.values()
    assert cls.fullName() == '<test>.C'
    assert cls.docstring == None
    assert len(cls.contents) == 1
    func, = cls.contents.values()
    assert func.fullName() == '<test>.C.f'
    assert func.docstring == """This is a docstring."""


@systemcls_param
def test_class_with_base(systemcls: Type[model.System]) -> None:
    src = '''
    class C:
        def f():
            """This is a docstring."""
    class D(C):
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src, systemcls=systemcls)
    assert len(mod.contents) == 2
    clsC, clsD = mod.contents.values()
    assert clsC.fullName() == '<test>.C'
    assert clsC.docstring == None
    assert len(clsC.contents) == 1

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 1
    base, = clsD.bases
    assert base == '<test>.C'

@systemcls_param
def test_follow_renaming(systemcls: Type[model.System]) -> None:
    src = '''
    class C: pass
    D = C
    class E(D): pass
    '''
    mod = fromText(src, systemcls=systemcls)
    C = mod.contents['C']
    E = mod.contents['E']
    assert E.baseobjects == [C], E.baseobjects

@systemcls_param
@pytest.mark.parametrize('level', (1, 2, 3, 4))
def test_relative_import_past_top(
        systemcls: Type[model.System],
        level: int,
        capsys: CapSys
        ) -> None:
    """A warning is logged when a relative import goes beyond the top-level
    package.
    """
    system = systemcls()
    system.ensurePackage('pkg')
    fromText(f'''
    from {'.' * level + 'X'} import A
    ''', modname='mod', parent_name='pkg', system=system)
    captured = capsys.readouterr().out
    if level == 1:
        assert not captured
    else:
        assert f'pkg.mod:2: relative import level ({level}) too high\n' == captured

@systemcls_param
def test_class_with_base_from_module(systemcls: Type[model.System]) -> None:
    src = '''
    from X.Y import A
    from Z import B as C
    class D(A, C):
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src, systemcls=systemcls)
    assert len(mod.contents) == 1
    clsD, = mod.contents.values()

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 2
    base1, base2 = clsD.bases
    assert base1 == 'X.Y.A'
    assert base2 == 'Z.B'

    src = '''
    import X
    import Y.Z as M
    class D(X.A, X.B.C, M.C):
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src, systemcls=systemcls)
    assert len(mod.contents) == 1
    clsD, = mod.contents.values()

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 3
    base1, base2, base3 = clsD.bases
    assert base1 == 'X.A', base1
    assert base2 == 'X.B.C', base2
    assert base3 == 'Y.Z.C', base3

@systemcls_param
def test_aliasing(systemcls: Type[model.System]) -> None:
    def addsrc(system: model.System) -> None:
        src_private = '''
        class A:
            pass
        '''
        src_export = '''
        from _private import A as B
        __all__ = ['B']
        '''
        src_user = '''
        from public import B
        class C(B):
            pass
        '''
        fromText(src_private, modname='_private', system=system)
        fromText(src_export, modname='public', system=system)
        fromText(src_user, modname='app', system=system)

    system = systemcls()
    addsrc(system)
    C = system.allobjects['app.C']
    assert isinstance(C, model.Class)
    # An older version of this test expected _private.A as the result.
    # The expected behavior was changed because:
    # - relying on on-demand processing of other modules is unreliable when
    #   there are cyclic imports: expandName() on a module that is still being
    #   processed can return the not-found result for a name that does exist
    # - code should be importing names from their official home, so if we
    #   import public.B then for the purposes of documentation public.B is
    #   the name we should use
    assert C.bases == ['public.B']

@systemcls_param
def test_more_aliasing(systemcls: Type[model.System]) -> None:
    def addsrc(system: model.System) -> None:
        src_a = '''
        class A:
            pass
        '''
        src_b = '''
        from a import A as B
        '''
        src_c = '''
        from b import B as C
        '''
        src_d = '''
        from c import C
        class D(C):
            pass
        '''
        fromText(src_a, modname='a', system=system)
        fromText(src_b, modname='b', system=system)
        fromText(src_c, modname='c', system=system)
        fromText(src_d, modname='d', system=system)

    system = systemcls()
    addsrc(system)
    D = system.allobjects['d.D']
    assert isinstance(D, model.Class)
    # An older version of this test expected a.A as the result.
    # Read the comment in test_aliasing() to learn why this was changed.
    assert D.bases == ['c.C']

@systemcls_param
def test_aliasing_recursion(systemcls: Type[model.System]) -> None:
    system = systemcls()
    src = '''
    class C:
        pass
    from mod import C
    class D(C):
        pass
    '''
    mod = fromText(src, modname='mod', system=system)
    assert mod.contents['D'].bases == ['mod.C'], mod.contents['D'].bases

@systemcls_param
def test_documented_no_alias(systemcls: Type[model.System]) -> None:
    """A variable that is documented should not be considered an alias."""
    # TODO: We should also verify this for inline docstrings, but the code
    #       currently doesn't support that. We should perhaps store aliases
    #       as Documentables as well, so we can change their 'kind' when
    #       an inline docstring follows the assignment.
    mod = fromText('''
    class SimpleClient:
        pass
    class Processor:
        """
        @ivar clientFactory: Callable that returns a client.
        """
        clientFactory = SimpleClient
    ''', systemcls=systemcls)
    P = mod.contents['Processor']
    f = P.contents['clientFactory']
    assert unwrap(f.parsed_docstring) == """Callable that returns a client."""
    assert f.privacyClass is model.PrivacyClass.VISIBLE
    assert f.kind == 'Instance Variable'
    assert f.linenumber

@systemcls_param
def test_subclasses(systemcls: Type[model.System]) -> None:
    src = '''
    class A:
        pass
    class B(A):
        pass
    '''
    system = fromText(src, systemcls=systemcls).system
    A = system.allobjects['<test>.A']
    assert isinstance(A, model.Class)
    assert A.subclasses == [system.allobjects['<test>.B']]

@systemcls_param
def test_inherit_names(systemcls: Type[model.System]) -> None:
    src = '''
    class A:
        pass
    class A(A):
        pass
    '''
    mod = fromText(src, systemcls=systemcls)
    assert [b.name for b in mod.contents['A'].allbases()] == ['A 0']

@systemcls_param
def test_nested_class_inheriting_from_same_module(systemcls: Type[model.System]) -> None:
    src = '''
    class A:
        pass
    class B:
        class C(A):
            pass
    '''
    fromText(src, systemcls=systemcls)

@systemcls_param
def test_all_recognition(systemcls: Type[model.System]) -> None:
    """The value assigned to __all__ is parsed to Module.all."""
    mod = fromText('''
    def f():
        pass
    __all__ = ['f']
    ''', systemcls=systemcls)
    assert mod.all == ['f']
    assert '__all__' not in mod.contents

@systemcls_param
def test_all_in_class_non_recognition(systemcls: Type[model.System]) -> None:
    """A class variable named __all__ is just an ordinary variable and
    does not affect Module.all.
    """
    mod = fromText('''
    class C:
        __all__ = ['f']
    ''', systemcls=systemcls)
    assert mod.all is None
    assert '__all__' not in mod.contents
    assert '__all__' in mod.contents['C'].contents

@systemcls_param
def test_all_multiple(systemcls: Type[model.System], capsys: CapSys) -> None:
    """If there are multiple assignments to __all__, a warning is logged
    and the last assignment takes effect.
    """
    mod = fromText('''
    __all__ = ['f']
    __all__ = ['g']
    ''', modname='mod', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == 'mod:3: Assignment to "__all__" overrides previous assignment\n'
    assert mod.all == ['g']

@systemcls_param
def test_all_bad_sequence(systemcls: Type[model.System], capsys: CapSys) -> None:
    """Values other than lists and tuples assigned to __all__ have no effect
    and a warning is logged.
    """
    mod = fromText('''
    __all__ = {}
    ''', modname='mod', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == 'mod:2: Cannot parse value assigned to "__all__"\n'
    assert mod.all is None

@systemcls_param
def test_all_nonliteral(systemcls: Type[model.System], capsys: CapSys) -> None:
    """Non-literals in __all__ are ignored."""
    mod = fromText('''
    __all__ = ['a', 'b', '.'.join(['x', 'y']), 'c']
    ''', modname='mod', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == 'mod:2: Cannot parse element 2 of "__all__"\n'
    assert mod.all == ['a', 'b', 'c']

@systemcls_param
def test_all_nonstring(systemcls: Type[model.System], capsys: CapSys) -> None:
    """Non-string literals in __all__ are ignored."""
    mod = fromText('''
    __all__ = ('a', 'b', 123, 'c', True)
    ''', modname='mod', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == (
        'mod:2: Element 2 of "__all__" has type "int", expected "str"\n'
        'mod:2: Element 4 of "__all__" has type "bool", expected "str"\n'
        )
    assert mod.all == ['a', 'b', 'c']

@systemcls_param
def test_all_allbad(systemcls: Type[model.System], capsys: CapSys) -> None:
    """If no value in __all__ could be parsed, the result is an empty list."""
    mod = fromText('''
    __all__ = (123, True)
    ''', modname='mod', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == (
        'mod:2: Element 0 of "__all__" has type "int", expected "str"\n'
        'mod:2: Element 1 of "__all__" has type "bool", expected "str"\n'
        )
    assert mod.all == []

@systemcls_param
def test_classmethod(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        @classmethod
        def f(klass):
            pass
    ''', systemcls=systemcls)
    assert mod.contents['C'].contents['f'].kind == 'Class Method'
    mod = fromText('''
    class C:
        def f(klass):
            pass
        f = classmethod(f)
    ''', systemcls=systemcls)
    assert mod.contents['C'].contents['f'].kind == 'Class Method'

@systemcls_param
def test_classdecorator(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    def cd(cls):
        pass
    @cd
    class C:
        pass
    ''', modname='mod', systemcls=systemcls)
    C = mod.contents['C']
    assert C.decorators == [('mod.cd', None)]


@systemcls_param
def test_classdecorator_with_args(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    def cd(): pass
    class A: pass
    @cd(A)
    class C:
        pass
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert len(C.decorators) == 1
    (name, args), = C.decorators
    assert name == 'test.cd'
    assert len(args) == 1
    arg, = args
    assert astbuilder.node2fullname(arg, mod) == 'test.A'


@systemcls_param
def test_methoddecorator(systemcls: Type[model.System], capsys: CapSys) -> None:
    mod = fromText('''
    class C:
        def method_undecorated():
            pass

        @staticmethod
        def method_static():
            pass

        @classmethod
        def method_class(cls):
            pass

        @staticmethod
        @classmethod
        def method_both():
            pass
    ''', modname='mod', systemcls=systemcls)
    C = mod.contents['C']
    assert C.contents['method_undecorated'].kind == 'Method'
    assert C.contents['method_static'].kind == 'Static Method'
    assert C.contents['method_class'].kind == 'Class Method'
    captured = capsys.readouterr().out
    assert captured == "mod:14: mod.C.method_both is both classmethod and staticmethod\n"


@systemcls_param
def test_assignment_to_method_in_class(systemcls: Type[model.System]) -> None:
    """An assignment to a method in a class body does not change the type
    of the documentable.

    If the name we assign to exists and it does not belong to an Attribute
    (it's a Function instead, in this test case), the assignment will be
    ignored.
    """
    mod = fromText('''
    class Base:
        def base_method():
            """Base method docstring."""

    class Sub(Base):
        base_method = wrap_method(base_method)
        """Overriding the docstring is not supported."""

        def sub_method():
            """Sub method docstring."""
        sub_method = wrap_method(sub_method)
        """Overriding the docstring is not supported."""
    ''', systemcls=systemcls)
    assert isinstance(mod.contents['Base'].contents['base_method'], model.Function)
    assert mod.contents['Sub'].contents.get('base_method') is None
    sub_method = mod.contents['Sub'].contents['sub_method']
    assert isinstance(sub_method, model.Function)
    assert sub_method.docstring == """Sub method docstring."""


@systemcls_param
def test_assignment_to_method_in_init(systemcls: Type[model.System]) -> None:
    """An assignment to a method inside __init__() does not change the type
    of the documentable.

    If the name we assign to exists and it does not belong to an Attribute
    (it's a Function instead, in this test case), the assignment will be
    ignored.
    """
    mod = fromText('''
    class Base:
        def base_method():
            """Base method docstring."""

    class Sub(Base):
        def sub_method():
            """Sub method docstring."""

        def __init__(self):
            self.base_method = wrap_method(self.base_method)
            """Overriding the docstring is not supported."""
            self.sub_method = wrap_method(self.sub_method)
            """Overriding the docstring is not supported."""
    ''', systemcls=systemcls)
    assert isinstance(mod.contents['Base'].contents['base_method'], model.Function)
    assert mod.contents['Sub'].contents.get('base_method') is None
    sub_method = mod.contents['Sub'].contents['sub_method']
    assert isinstance(sub_method, model.Function)
    assert sub_method.docstring == """Sub method docstring."""


@systemcls_param
def test_import_star(systemcls: Type[model.System]) -> None:
    mod_a = fromText('''
    def f(): pass
    ''', modname='a', systemcls=systemcls)
    mod_b = fromText('''
    from a import *
    ''', modname='b', system=mod_a.system)
    assert mod_b.resolveName('f') == mod_a.contents['f']


@systemcls_param
def test_import_func_from_package(systemcls: Type[model.System]) -> None:
    """Importing a function from a package should look in the C{__init__}
    module.

    In this test the following hierarchy is constructed::

        package a
          module __init__
            defines function 'f'
          module c
            imports function 'f'
        module b
          imports function 'f'

    We verify that when module C{b} and C{c} import the name C{f} from
    package C{a}, they import the function C{f} from the module C{a.__init__}.
    """
    system = systemcls()
    system.ensurePackage('a')
    mod_a = fromText('''
    def f(): pass
    ''', modname='__init__', parent_name='a', system=system)
    mod_b = fromText('''
    from a import f
    ''', modname='b', system=system)
    mod_c = fromText('''
    from . import f
    ''', modname='c', parent_name='a', system=system)
    assert mod_b.resolveName('f') == mod_a.contents['f']
    assert mod_c.resolveName('f') == mod_a.contents['f']


@systemcls_param
def test_import_module_from_package(systemcls: Type[model.System]) -> None:
    """Importing a module from a package should not look in C{__init__}
    module.

    In this test the following hierarchy is constructed::

        package a
          module __init__
          module b
            defines function 'f'
        module c
          imports module 'a.b'

    We verify that when module C{c} imports the name C{b} from package C{a},
    it imports the module C{a.b} which contains C{f}.
    """
    system = systemcls()
    system.ensurePackage('a')
    fromText('''
    # This module intentionally left blank.
    ''', modname='__init__', parent_name='a', system=system)
    mod_b = fromText('''
    def f(): pass
    ''', modname='b', parent_name='a', system=system)
    mod_c = fromText('''
    from a import b
    f = b.f
    ''', modname='c', system=system)
    assert mod_c.resolveName('f') == mod_b.contents['f']


@systemcls_param
def test_inline_docstring_modulevar(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    """regular module docstring

    @var b: doc for b
    """

    """not a docstring"""

    a = 1
    """inline doc for a"""

    b = 2

    def f():
        pass
    """not a docstring"""
    ''', modname='test', systemcls=systemcls)
    assert sorted(mod.contents.keys()) == ['a', 'b', 'f']
    a = mod.contents['a']
    assert a.docstring == """inline doc for a"""
    b = mod.contents['b']
    assert unwrap(b.parsed_docstring) == """doc for b"""
    f = mod.contents['f']
    assert not f.docstring

@systemcls_param
def test_inline_docstring_classvar(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        """regular class docstring"""

        def f(self):
            pass
        """not a docstring"""

        a = 1
        """inline doc for a"""

        """not a docstring"""

        _b = 2
        """inline doc for _b"""

        None
        """not a docstring"""
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == ['_b', 'a', 'f']
    f = C.contents['f']
    assert not f.docstring
    a = C.contents['a']
    assert a.docstring == """inline doc for a"""
    assert a.privacyClass is model.PrivacyClass.VISIBLE
    b = C.contents['_b']
    assert b.docstring == """inline doc for _b"""
    assert b.privacyClass is model.PrivacyClass.PRIVATE

@systemcls_param
def test_inline_docstring_annotated_classvar(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        """regular class docstring"""

        a: int
        """inline doc for a"""

        _b: int = 4
        """inline doc for _b"""
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == ['_b', 'a']
    a = C.contents['a']
    assert a.docstring == """inline doc for a"""
    assert a.privacyClass is model.PrivacyClass.VISIBLE
    b = C.contents['_b']
    assert b.docstring == """inline doc for _b"""
    assert b.privacyClass is model.PrivacyClass.PRIVATE

@systemcls_param
def test_inline_docstring_instancevar(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        """regular class docstring"""

        d = None
        """inline doc for d"""

        f = None
        """inline doc for f"""

        def __init__(self):
            self.a = 1
            """inline doc for a"""

            """not a docstring"""

            self._b = 2
            """inline doc for _b"""

            x = -1
            """not a docstring"""

            self.c = 3
            """inline doc for c"""

            self.d = 4

            self.e = 5
        """not a docstring"""

        def set_f(self, value):
            self.f = value
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == [
        '__init__', '_b', 'a', 'c', 'd', 'e', 'f', 'set_f'
        ]
    a = C.contents['a']
    assert a.docstring == """inline doc for a"""
    assert a.privacyClass is model.PrivacyClass.VISIBLE
    assert a.kind == 'Instance Variable'
    b = C.contents['_b']
    assert b.docstring == """inline doc for _b"""
    assert b.privacyClass is model.PrivacyClass.PRIVATE
    assert b.kind == 'Instance Variable'
    c = C.contents['c']
    assert c.docstring == """inline doc for c"""
    assert c.privacyClass is model.PrivacyClass.VISIBLE
    assert c.kind == 'Instance Variable'
    d = C.contents['d']
    assert d.docstring == """inline doc for d"""
    assert d.privacyClass is model.PrivacyClass.VISIBLE
    assert d.kind == 'Instance Variable'
    e = C.contents['e']
    assert not e.docstring
    f = C.contents['f']
    assert f.docstring == """inline doc for f"""
    assert f.privacyClass is model.PrivacyClass.VISIBLE
    assert f.kind == 'Instance Variable'

@systemcls_param
def test_inline_docstring_annotated_instancevar(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        """regular class docstring"""

        a: int

        def __init__(self):
            self.a = 1
            """inline doc for a"""

            self.b: int = 2
            """inline doc for b"""
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == ['__init__', 'a', 'b']
    a = C.contents['a']
    assert a.docstring == """inline doc for a"""
    b = C.contents['b']
    assert b.docstring == """inline doc for b"""

@systemcls_param
def test_docstring_assignment(systemcls: Type[model.System], capsys: CapSys) -> None:
    mod = fromText(r'''
    def fun():
        pass

    class CLS:

        def method1():
            """Temp docstring."""
            pass

        def method2():
            pass

        method1.__doc__ = "Updated docstring #1"

    fun.__doc__ = "Happy Happy Joy Joy"
    CLS.__doc__ = "Clears the screen"
    CLS.method2.__doc__ = "Updated docstring #2"

    None.__doc__ = "Free lunch!"
    real.__doc__ = "Second breakfast"
    fun.__doc__ = codecs.encode('Pnrfne fnynq', 'rot13')
    CLS.method1.__doc__ = 4

    def mark_unavailable(func):
        # No warning: docstring updates in functions are ignored.
        func.__doc__ = func.__doc__ + '\n\nUnavailable on this system.'
    ''', systemcls=systemcls)
    fun = mod.contents['fun']
    assert fun.kind == 'Function'
    assert fun.docstring == """Happy Happy Joy Joy"""
    CLS = mod.contents['CLS']
    assert CLS.kind == 'Class'
    assert CLS.docstring == """Clears the screen"""
    method1 = CLS.contents['method1']
    assert method1.kind == 'Method'
    assert method1.docstring == "Updated docstring #1"
    method2 = CLS.contents['method2']
    assert method2.kind == 'Method'
    assert method2.docstring == "Updated docstring #2"
    captured = capsys.readouterr()
    lines = captured.out.split('\n')
    assert len(lines) > 0 and lines[0] == \
        "<test>:20: Unable to figure out target for __doc__ assignment"
    assert len(lines) > 1 and lines[1] == \
        "<test>:21: Unable to figure out target for __doc__ assignment: " \
        "computed full name not found: real"
    assert len(lines) > 2 and lines[2] == \
        "<test>:22: Unable to figure out value for __doc__ assignment, " \
        "maybe too complex"
    assert len(lines) > 3 and lines[3] == \
        "<test>:23: Ignoring value assigned to __doc__: not a string"
    assert len(lines) == 5 and lines[-1] == ''

@systemcls_param
def test_docstring_assignment_detuple(systemcls: Type[model.System], capsys: CapSys) -> None:
    """We currently don't trace values for detupling assignments, so when
    assigning to __doc__ we get a warning about the unknown value.
    """
    fromText('''
    def fun():
        pass

    fun.__doc__, other = 'Detupling to __doc__', 'is not supported'
    ''', modname='test', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == (
        "test:5: Unable to figure out value for __doc__ assignment, maybe too complex\n"
        )

@systemcls_param
def test_variable_scopes(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    l = 1
    """module-level l"""

    m = 1
    """module-level m"""

    class C:
        """class docstring

        @ivar k: class level doc for k
        """

        a = None

        k = 640

        m = 2
        """class-level m"""

        def __init__(self):
            self.a = 1
            """inline doc for a"""
            self.l = 2
            """instance l"""
    ''', modname='test', systemcls=systemcls)
    l1 = mod.contents['l']
    assert l1.kind == 'Variable'
    assert l1.docstring == """module-level l"""
    m1 = mod.contents['m']
    assert m1.kind == 'Variable'
    assert m1.docstring == """module-level m"""
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == ['__init__', 'a', 'k', 'l', 'm']
    a = C.contents['a']
    assert a.kind == 'Instance Variable'
    assert a.docstring == """inline doc for a"""
    k = C.contents['k']
    assert k.kind == 'Instance Variable'
    assert unwrap(k.parsed_docstring) == """class level doc for k"""
    l2 = C.contents['l']
    assert l2.kind == 'Instance Variable'
    assert l2.docstring == """instance l"""
    m2 = C.contents['m']
    assert m2.kind == 'Class Variable'
    assert m2.docstring == """class-level m"""

@systemcls_param
def test_variable_types(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        """class docstring

        @cvar a: first
        @type a: string

        @type b: string
        @cvar b: second

        @type c: string

        @ivar d: fourth
        @type d: string

        @type e: string
        @ivar e: fifth

        @type f: string

        @type g: string
        """

        a = "A"

        b = "B"

        c = "C"
        """third"""

        def __init__(self):

            self.d = "D"

            self.e = "E"

            self.f = "F"
            """sixth"""

            self.g = g = "G"
            """seventh"""
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == [
        '__init__', 'a', 'b', 'c', 'd', 'e', 'f', 'g'
        ]
    a = C.contents['a']
    assert unwrap(a.parsed_docstring) == """first"""
    assert str(unwrap(a.parsed_type)) == 'string'
    assert a.kind == 'Class Variable'
    b = C.contents['b']
    assert unwrap(b.parsed_docstring) == """second"""
    assert str(unwrap(b.parsed_type)) == 'string'
    assert b.kind == 'Class Variable'
    c = C.contents['c']
    assert c.docstring == """third"""
    assert str(unwrap(c.parsed_type)) == 'string'
    assert c.kind == 'Class Variable'
    d = C.contents['d']
    assert unwrap(d.parsed_docstring) == """fourth"""
    assert str(unwrap(d.parsed_type)) == 'string'
    assert d.kind == 'Instance Variable'
    e = C.contents['e']
    assert unwrap(e.parsed_docstring) == """fifth"""
    assert str(unwrap(e.parsed_type)) == 'string'
    assert e.kind == 'Instance Variable'
    f = C.contents['f']
    assert f.docstring == """sixth"""
    assert str(unwrap(f.parsed_type)) == 'string'
    assert f.kind == 'Instance Variable'
    g = C.contents['g']
    assert g.docstring == """seventh"""
    assert str(unwrap(g.parsed_type)) == 'string'
    assert g.kind == 'Instance Variable'

@systemcls_param
def test_annotated_variables(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        """class docstring

        @cvar a: first
        @type a: string

        @type b: string
        @cvar b: second
        """

        a: str = "A"

        b: str

        c: str = "C"
        """third"""

        d: str
        """fourth"""

        e: List['C']
        """fifth"""

        f: 'List[C]'
        """sixth"""

        g: 'List["C"]'
        """seventh"""

        def __init__(self):
            self.s: List[str] = []
            """instance"""

    m: bytes = b"M"
    """module-level"""
    ''', modname='test', systemcls=systemcls)

    def type2html(obj: model.Documentable) -> str:
        parsed_type = get_parsed_type(obj)
        assert parsed_type is not None
        return to_html(parsed_type)

    C = mod.contents['C']
    a = C.contents['a']
    assert unwrap(a.parsed_docstring) == """first"""
    assert type2html(a) == 'string'
    b = C.contents['b']
    assert unwrap(b.parsed_docstring) == """second"""
    assert type2html(b) == 'string'
    c = C.contents['c']
    assert c.docstring == """third"""
    assert type2html(c) == '<code>str</code>'
    d = C.contents['d']
    assert d.docstring == """fourth"""
    assert type2html(d) == '<code>str</code>'
    e = C.contents['e']
    assert e.docstring == """fifth"""
    assert type2html(e) == '<code>List[C]</code>'
    f = C.contents['f']
    assert f.docstring == """sixth"""
    assert type2html(f) == '<code>List[C]</code>'
    g = C.contents['g']
    assert g.docstring == """seventh"""
    assert type2html(g) == '<code>List[C]</code>'
    s = C.contents['s']
    assert s.docstring == """instance"""
    assert type2html(s) == '<code>List[str]</code>'
    m = mod.contents['m']
    assert m.docstring == """module-level"""
    assert type2html(m) == '<code>bytes</code>'

@typecomment
@systemcls_param
def test_type_comment(systemcls: Type[model.System], capsys: CapSys) -> None:
    mod = fromText('''
    d = {} # type: dict[str, int]
    i = [] # type: ignore[misc]
    ''', systemcls=systemcls)
    assert type2str(mod.contents['d'].annotation) == 'dict[str, int]'
    # We don't use ignore comments for anything at the moment,
    # but do verify that their presence doesn't break things.
    assert type2str(mod.contents['i'].annotation) == 'list'
    assert not capsys.readouterr().out

@systemcls_param
def test_unstring_annotation(systemcls: Type[model.System]) -> None:
    """Annotations or parts thereof that are strings are parsed and
    line number information is preserved.
    """
    mod = fromText('''
    a: "int"
    b: 'str' = 'B'
    c: list["Thingy"]
    ''', systemcls=systemcls)
    assert ann_str_and_line(mod.contents['a']) == ('int', 2)
    assert ann_str_and_line(mod.contents['b']) == ('str', 3)
    assert ann_str_and_line(mod.contents['c']) == ('list[Thingy]', 4)

@pytest.mark.parametrize('annotation', ("[", "pass", "1 ; 2"))
@systemcls_param
def test_bad_string_annotation(
        annotation: str, systemcls: Type[model.System], capsys: CapSys
        ) -> None:
    """Invalid string annotations must be reported as syntax errors."""
    mod = fromText(f'''
    x: "{annotation}"
    ''', modname='test', systemcls=systemcls)
    assert isinstance(mod.contents['x'].annotation, ast.expr)
    assert "syntax error in annotation" in capsys.readouterr().out

@pytest.mark.parametrize('annotation,expected', (
    ("Literal['[', ']']", "Literal['[', ']']"),
    ("typing.Literal['pass', 'raise']", "typing.Literal['pass', 'raise']"),
    ("Optional[Literal['1 ; 2']]", "Optional[Literal['1 ; 2']]"),
    ("'Literal'['!']", "Literal['!']"),
    (r"'Literal[\'if\', \'while\']'", "Literal['if', 'while']"),
    ))
def test_literal_string_annotation(annotation: str, expected: str) -> None:
    """Strings inside Literal annotations must not be recursively parsed."""
    stmt, = ast.parse(annotation).body
    assert isinstance(stmt, ast.Expr)
    unstringed = astbuilder._AnnotationStringParser().visit(stmt.value)
    assert astor.to_source(unstringed).strip() == expected

@systemcls_param
def test_inferred_variable_types(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    class C:
        a = "A"
        b = 2
        c = ['a', 'b', 'c']
        d = {'a': 1, 'b': 2}
        e = (True, False, True)
        f = 1.618
        g = {2, 7, 1, 8}
        h = []
        i = ['r', 2, 'd', 2]
        j = ((), ((), ()))
        n = None
        x = list(range(10))
        y = [n for n in range(10) if n % 2]
        def __init__(self):
            self.s = ['S']
            self.t = t = 'T'
    m = b'octets'
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert ann_str_and_line(C.contents['a']) == ('str', 3)
    assert ann_str_and_line(C.contents['b']) == ('int', 4)
    assert ann_str_and_line(C.contents['c']) == ('list[str]', 5)
    assert ann_str_and_line(C.contents['d']) == ('dict[str, int]', 6)
    assert ann_str_and_line(C.contents['e']) == ('tuple[bool, ...]', 7)
    assert ann_str_and_line(C.contents['f']) == ('float', 8)
    assert ann_str_and_line(C.contents['g']) == ('set[int]', 9)
    # Element type is unknown, not uniform or too complex.
    assert ann_str_and_line(C.contents['h']) == ('list', 10)
    assert ann_str_and_line(C.contents['i']) == ('list', 11)
    assert ann_str_and_line(C.contents['j']) == ('tuple', 12)
    # It is unlikely that a variable actually will contain only None,
    # so we should treat this as not be able to infer the type.
    assert C.contents['n'].annotation is None
    # These expressions are considered too complex for pydoctor.
    # Maybe we can use an external type inferrer at some point.
    assert C.contents['x'].annotation is None
    assert C.contents['y'].annotation is None
    # Type inference isn't different for module and instance variables,
    # so we don't need to re-test everything.
    assert ann_str_and_line(C.contents['s']) == ('list[str]', 17)
    # Check that type is inferred on assignments with multiple targets.
    assert ann_str_and_line(C.contents['t']) == ('str', 18)
    assert ann_str_and_line(mod.contents['m']) == ('bytes', 19)

@systemcls_param
def test_attrs_attrib_type(systemcls: Type[model.System]) -> None:
    """An attr.ib's "type" or "default" argument is used as an alternative
    type annotation.
    """
    mod = fromText('''
    import attr
    from attr import attrib
    @attr.s
    class C:
        a = attr.ib(type=int)
        b = attrib(type=int)
        c = attr.ib(type='C')
        d = attr.ib(default=True)
        e = attr.ib(123)
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert type2str(C.contents['a'].annotation) == 'int'
    assert type2str(C.contents['b'].annotation) == 'int'
    assert type2str(C.contents['c'].annotation) == 'C'
    assert type2str(C.contents['d'].annotation) == 'bool'
    assert type2str(C.contents['e'].annotation) == 'int'

@systemcls_param
def test_attrs_attrib_instance(systemcls: Type[model.System]) -> None:
    """An attr.ib attribute is classified as an instance variable."""
    mod = fromText('''
    import attr
    @attr.s
    class C:
        a = attr.ib(type=int)
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert C.contents['a'].kind == 'Instance Variable'

@systemcls_param
def test_attrs_attrib_badargs(systemcls: Type[model.System], capsys: CapSys) -> None:
    """."""
    fromText('''
    import attr
    @attr.s
    class C:
        a = attr.ib(nosuchargument='bad')
    ''', modname='test', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == (
        'test:5: Invalid arguments for attr.ib(): got an unexpected keyword argument "nosuchargument"\n'
        )

@systemcls_param
def test_attrs_auto_instance(systemcls: Type[model.System]) -> None:
    """Attrs auto-attributes are classified as instance variables."""
    mod = fromText('''
    from typing import ClassVar
    import attr
    @attr.s(auto_attribs=True)
    class C:
        a: int
        b: bool = False
        c: ClassVar[str]  # explicit class variable
        d = 123  # ignored by auto_attribs because no annotation
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']
    assert C.contents['a'].kind == 'Instance Variable'
    assert C.contents['b'].kind == 'Instance Variable'
    assert C.contents['c'].kind == 'Class Variable'
    assert C.contents['d'].kind == 'Class Variable'

@systemcls_param
def test_attrs_args(systemcls: Type[model.System], capsys: CapSys) -> None:
    """Non-existing arguments and invalid values to recognized arguments are
    rejected with a warning.
    """
    fromText('''
    import attr

    @attr.s()
    class C0: ...

    @attr.s(repr=False)
    class C1: ...

    @attr.s(auto_attribzzz=True)
    class C2: ...

    @attr.s(auto_attribs=not False)
    class C3: ...

    @attr.s(auto_attribs=1)
    class C4: ...
    ''', modname='test', systemcls=systemcls)
    captured = capsys.readouterr().out
    assert captured == (
        'test:10: Invalid arguments for attr.s(): got an unexpected keyword argument "auto_attribzzz"\n'
        'test:13: Unable to figure out value for "auto_attribs" argument to attr.s(), maybe too complex\n'
        'test:16: Value for "auto_attribs" argument to attr.s() has type "int", expected "bool"\n'
        )

@systemcls_param
def test_detupling_assignment(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    a, b, c = range(3)
    ''', modname='test', systemcls=systemcls)
    assert sorted(mod.contents.keys()) == ['a', 'b', 'c']

@systemcls_param
def test_property_decorator(systemcls: Type[model.System]) -> None:
    """A function decorated with '@property' is documented as an attribute."""
    mod = fromText('''
    class C:
        @property
        def prop(self) -> str:
            """For sale."""
            return 'seaside'
        @property
        def oldschool(self):
            """
            @return: For rent.
            @rtype: string
            @see: U{https://example.com/}
            """
            return 'downtown'
    ''', modname='test', systemcls=systemcls)
    C = mod.contents['C']

    prop = C.contents['prop']
    assert isinstance(prop, model.Attribute)
    assert prop.kind == 'Property'
    assert prop.docstring == """For sale."""
    assert type2str(prop.annotation) == 'str'

    oldschool = C.contents['oldschool']
    assert isinstance(oldschool, model.Attribute)
    assert oldschool.kind == 'Property'
    assert isinstance(oldschool.parsed_docstring, ParsedEpytextDocstring)
    assert unwrap(oldschool.parsed_docstring) == """For rent."""
    assert flatten(format_summary(oldschool)) == '<span>For rent.</span>'
    assert isinstance(oldschool.parsed_type, ParsedEpytextDocstring)
    assert str(unwrap(oldschool.parsed_type)) == 'string'
    fields = oldschool.parsed_docstring.fields
    assert len(fields) == 1
    assert fields[0].tag() == 'see'


@systemcls_param
def test_property_setter(systemcls: Type[model.System], capsys: CapSys) -> None:
    """Property setter and deleter methods are renamed, so they don't replace
    the property itself.
    """
    mod = fromText('''
    class C:
        @property
        def prop(self):
            """Getter."""
        @prop.setter
        def prop(self, value):
            """Setter."""
        @prop.deleter
        def prop(self):
            """Deleter."""
    ''', modname='mod', systemcls=systemcls)
    C = mod.contents['C']

    getter = C.contents['prop']
    assert isinstance(getter, model.Attribute)
    assert getter.kind == 'Property'
    assert getter.docstring == """Getter."""

    setter = C.contents['prop.setter']
    assert isinstance(setter, model.Function)
    assert setter.kind == 'Method'
    assert setter.docstring == """Setter."""

    deleter = C.contents['prop.deleter']
    assert isinstance(deleter, model.Function)
    assert deleter.kind == 'Method'
    assert deleter.docstring == """Deleter."""


@systemcls_param
def test_property_custom(systemcls: Type[model.System], capsys: CapSys) -> None:
    """Any custom decorator with a name ending in 'property' makes a method
    into a property getter.
    """
    mod = fromText('''
    class C:
        @deprecate.deprecatedProperty(incremental.Version("Twisted", 18, 7, 0))
        def processes(self):
            return {}
        @async_property
        async def remote_value(self):
            return await get_remote_value()
        @abc.abstractproperty
        def name(self):
            raise NotImplementedError
    ''', modname='mod', systemcls=systemcls)
    C = mod.contents['C']

    deprecated = C.contents['processes']
    assert isinstance(deprecated, model.Attribute)
    assert deprecated.kind == 'Property'

    async_prop = C.contents['remote_value']
    assert isinstance(async_prop, model.Attribute)
    assert async_prop.kind == 'Property'

    abstract_prop = C.contents['name']
    assert isinstance(abstract_prop, model.Attribute)
    assert abstract_prop.kind == 'Property'


@pytest.mark.parametrize('decoration', ('classmethod', 'staticmethod'))
@systemcls_param
def test_property_conflict(
        decoration: str, systemcls: Type[model.System], capsys: CapSys
        ) -> None:
    """Warn when a function is decorated as both property and class/staticmethod.
    These decoration combinations do not create class/static properties.
    """
    mod = fromText(f'''
    class C:
        @{decoration}
        @property
        def prop():
            raise NotImplementedError
    ''', modname='mod', systemcls=systemcls)
    C = mod.contents['C']
    assert C.contents['prop'].kind == 'Property'
    captured = capsys.readouterr().out
    assert captured == f"mod:3: mod.C.prop is both property and {decoration}\n"

@systemcls_param
def test_ignore_function_contents(systemcls: Type[model.System]) -> None:
    mod = fromText('''
    def outer():
        """Outer function."""

        class Clazz:
            """Inner class."""

        def func():
            """Inner function."""

        var = 1
        """Local variable."""
    ''', systemcls=systemcls)
    outer = mod.contents['outer']
    assert not outer.contents
