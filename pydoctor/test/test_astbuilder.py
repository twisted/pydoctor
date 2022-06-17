
from typing import Optional, Tuple, Type, List, overload, cast
import ast

import astor


from pydoctor import astbuilder, model, astutils, names
from pydoctor.epydoc.markup import DocstringLinker, ParsedDocstring
from pydoctor.stanutils import flatten, html2stan, flatten_text
from pydoctor.epydoc.markup.epytext import Element, ParsedEpytextDocstring
from pydoctor.epydoc2stan import ensure_parsed_docstring, format_summary, get_parsed_type

from . import CapSys, NotFoundLinker, posonlyargs, typecomment
import pytest

class SimpleSystem(model.System):
    """
    A system with no extensions.
    """
    extensions:List[str] = []

class ZopeInterfaceSystem(model.System):
    """
    A system with only the zope interface extension enabled.
    """
    extensions = ['pydoctor.extensions.zopeinterface']

class DeprecateSystem(model.System):
    """
    A system with only the twisted deprecated extension enabled.
    """
    extensions = ['pydoctor.extensions.deprecate']

class PydanticSystem(model.System):
    # Add our custom extension as extra
    custom_extensions = ['pydoctor.test.test_pydantic_fields']

systemcls_param = pytest.mark.parametrize(
    'systemcls', (model.System, # system with all extensions enalbed
                  ZopeInterfaceSystem, # system with zopeinterface extension only
                  DeprecateSystem, # system with deprecated extension only
                  SimpleSystem, # system with no extensions
                  PydanticSystem,
                 )
    )

def fromText(
        text: str,
        *,
        modname: str = '<test>',
        is_package: bool = False,
        parent_name: Optional[str] = None,
        system: Optional[model.System] = None,
        systemcls: Type[model.System] = model.System
        ) -> model.Module:
    
    if system is None:
        _system = systemcls()
    else:
        _system = system
    assert _system is not None

    if parent_name is None:
        full_name = modname
    else:
        full_name = f'{parent_name}.{modname}'

    builder = _system.systemBuilder(_system)
    builder.addModuleString(text, modname, parent_name, is_package=is_package)
    builder.buildModules()
    mod = _system.allobjects[full_name]
    assert isinstance(mod, model.Module)
    return mod

def unwrap(parsed_docstring: Optional[ParsedDocstring]) -> str:
    
    if parsed_docstring is None:
        raise TypeError("parsed_docstring cannot be None")
    if not isinstance(parsed_docstring, ParsedEpytextDocstring):
        raise TypeError(f"parsed_docstring must be a ParsedEpytextDocstring instance, not {parsed_docstring.__class__.__name__}")
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

def type2html(obj: model.Documentable) -> str:
    parsed_type = get_parsed_type(obj)
    assert parsed_type is not None
    return to_html(parsed_type).replace('<wbr></wbr>', '').replace('<wbr>\n</wbr>', '')

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
    assert isinstance(func, model.Function)
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
    assert isinstance(func, model.Function)
    assert func.is_async is True


@pytest.mark.parametrize('signature', (
    '()',
    '(*, a, b=None)',
    '(*, a=(), b)',
    '(a, b=3, *c, **kw)',
    '(f=True)',
    '(x=0.1, y=-2)',
    r"(s='theory', t='con\'text')",
    ))
@systemcls_param
def test_function_signature(signature: str, systemcls: Type[model.System]) -> None:
    """
    A round trip from source to inspect.Signature and back produces
    the original text.

    @note: Our inspect.Signature Paramters objects are now tweaked such that they might produce HTML tags, handled by the L{PyvalColorizer}.
    """
    mod = fromText(f'def f{signature}: ...', systemcls=systemcls)
    docfunc, = mod.contents.values()
    assert isinstance(docfunc, model.Function)
    # This little trick makes it possible to back reproduce the original signature from the genrated HTML.
    text = flatten_text(html2stan(str(docfunc.signature)))
    assert text == signature

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

    assert isinstance(clsD, model.Class)
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
    assert isinstance(C, model.Class)
    assert isinstance(E, model.Class)
    assert E.baseobjects == [C], E.baseobjects

@systemcls_param
def test_relative_import_in_package(systemcls: Type[model.System]) -> None:
    """Relative imports in a package must be resolved by going up one level
    less, since we don't count "__init__.py" as a level.

    Hierarchy::

      top: def f
       - pkg: imports f and g
          - mod: def g
    """

    top_src = '''
    def f(): pass
    '''
    mod_src = '''
    def g(): pass
    '''
    pkg_src = '''
    from .. import f
    from .mod import g
    '''

    system = systemcls()
    top = fromText(top_src, modname='top', is_package=True, system=system)
    mod = fromText(mod_src, modname='top.pkg.mod', system=system)
    pkg = fromText(pkg_src, modname='pkg', parent_name='top', is_package=True,
                   system=system)

    assert pkg.resolveName('f') is top.contents['f']
    assert pkg.resolveName('g') is mod.contents['g']

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
    fromText('', modname='pkg', is_package=True, system=system)
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

    assert isinstance(clsD, model.Class)
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

    assert isinstance(clsD, model.Class)
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
    D = mod.contents['D']
    assert isinstance(D, model.Class)
    assert D.bases == ['mod.C'], D.bases

@systemcls_param
def test_documented_alias(systemcls: Type[model.System]) -> None:
    """
    All variables that simply points to an attribute or name are now 
    legit L{Attribute} documentable objects with a special kind: L{DocumentableKind.ALIAS}.
    """
    
    mod = fromText('''
    class SimpleClient:
        pass
    class Processor:
        """
        @ivar clientFactory: Callable that returns a client.
        """
        clientFactory = SimpleClient
    ''', systemcls=systemcls, modname='mod')
    P = mod.contents['Processor']
    f = P.contents['clientFactory']
    assert unwrap(f.parsed_docstring) == """Callable that returns a client."""
    assert f.privacyClass is model.PrivacyClass.PUBLIC
    # we now mark aliases with the ALIAS kind!
    assert f.kind is model.DocumentableKind.ALIAS
    assert f.linenumber

    # Verify this is working with inline docstrings as well.,
    #  but the code
    #       currently doesn't support that. We should perhaps store aliases
    #       as Documentables as well, so we can change their 'kind' when
    #       an inline docstring follows the assignment.
    mod = fromText('''
    class SimpleClient:
        pass
    class Processor:
        clientFactory = SimpleClient
        """
        Callable that returns a client.
        """
    ''', systemcls=systemcls, modname='mod')
    P = mod.contents['Processor']
    f = P.contents['clientFactory']
    ensure_parsed_docstring(f)
    assert unwrap(f.parsed_docstring) == """Callable that returns a client."""
    assert f.privacyClass is model.PrivacyClass.VISIBLE
    # we now mark aliases with the ALIAS kind!
    assert f.kind is model.DocumentableKind.ALIAS
    assert f.linenumber


@systemcls_param
def test_expandName_alias(systemcls: Type[model.System]) -> None:
    """
    expandName now follows all kinds of aliases!
    """
    system = systemcls()
    fromText('''
    class BaseClient:
        BAR = 1
        FOO = 2
    ''', system=system, modname='base_mod')
    mod = fromText('''
    import base_mod as _base
    class SimpleClient(_base.BaseClient):
        BARS = SimpleClient.FOO
        FOOS = _base.BaseClient.BAR
    class Processor:
        var = 1
        clientFactory = SimpleClient
        BARS = _base.BaseClient.FOO
    P = Processor
    ''', system=system, modname='mod')
    Processor = mod.contents['Processor']
    assert mod.expandName('Processor.clientFactory')=="mod.SimpleClient"
    assert mod.expandName('Processor.BARS')=="base_mod.BaseClient.FOO"
    assert mod.system.allobjects.get("mod.SimpleClient") is not None
    assert mod.system.allobjects.get("mod.SimpleClient.FOO") is  None
    assert mod.contents['P'].kind is model.DocumentableKind.ALIAS

    from pydoctor import names

    assert names._resolveAlias(mod, cast(model.Attribute, mod.contents['P']))=="mod.Processor"
    assert names._localNameToFullName(mod, 'P')=="mod.Processor"

    assert mod.expandName('P')=="mod.Processor"
    assert mod.expandName('P.var')=="mod.Processor.var"
    assert mod.expandName('P.clientFactory')=="mod.SimpleClient"
    assert mod.expandName('Processor.clientFactory.BARS')=="base_mod.BaseClient.FOO"
    assert mod.expandName('Processor.clientFactory.FOOS')=="base_mod.BaseClient.BAR"
    assert mod.expandName('P.clientFactory.BARS')=="base_mod.BaseClient.FOO"
    assert mod.expandName('P.clientFactory.FOOS')=="base_mod.BaseClient.BAR"
    assert Processor.expandName('clientFactory')=="mod.SimpleClient"
    assert Processor.expandName('BARS')=="base_mod.BaseClient.FOO"
    assert Processor.expandName('clientFactory.BARS')=="base_mod.BaseClient.FOO"

@systemcls_param
def test_expandName_alias_same_name_recursion(systemcls: Type[model.System]) -> None:
    """
    When the name of the alias is the same as the name contained in it's value, 
    it can create a recursion error. The C{indirections} parameter of methods 
    L{CanContainImportsDocumentable._localNameToFullName}, L{Documentable._resolveAlias} and L{Documentable.expandName} prevent an infinite loop where
    the name it beening revolved to the object itself. When this happends, we use the parent object context
    to call L{Documentable.expandName()}, avoiding the infinite recursion.
    """
    system = systemcls()
    base_mod = fromText('''
    class Foo:
        _1=1
        _2=2
        _3=3
    foo = Foo._1
    class Attribute:
        foo = foo
    class Class:
        pass
    ''', system=system, modname='base_mod')
    mod = fromText('''
    from base_mod import Attribute, Class, Foo
    class System:
        Attribute = Attribute
        Class = Class
    class SuperSystem:
        foo = Foo._3
        class Attribute:
            foo = foo
        Attribute = Attribute
    ''', system=system, modname='mod')
    System = mod.contents['System']
    SuperSystem = mod.contents['SuperSystem']
    assert mod.expandName('System.Attribute')=="base_mod.Attribute"
    assert mod.expandName('System.Class')=="base_mod.Class"
    
    assert System.expandName('Attribute')=="base_mod.Attribute"
    assert System.expandName('Class')=="base_mod.Class"
    
    assert mod.expandName('SuperSystem.Attribute')=="mod.SuperSystem.Attribute"
    assert SuperSystem.expandName('Attribute')=="mod.SuperSystem.Attribute"

    assert mod.expandName('SuperSystem.Attribute.foo')=="base_mod.Foo._3"
    assert SuperSystem.expandName('Attribute.foo')=="base_mod.Foo._3"

    assert base_mod.contents['Attribute'].contents['foo'].kind is model.DocumentableKind.ALIAS
    assert mod.contents['System'].contents['Attribute'].kind is model.DocumentableKind.ALIAS

    assert base_mod.contents['Attribute'].contents['foo'].fullName() == 'base_mod.Attribute.foo'
    assert 'base_mod.Attribute.foo' in mod.system.allobjects, str(list(mod.system.allobjects))
    
    f = mod.system.objForFullName('base_mod.Attribute.foo')
    assert isinstance(f, model.Attribute)
    assert f.kind is model.DocumentableKind.ALIAS

    assert mod.expandName('System.Attribute.foo')=="base_mod.Foo._1"
    assert System.expandName('Attribute.foo')=="base_mod.Foo._1"

    assert mod.contents['System'].contents['Attribute'].kind is model.DocumentableKind.ALIAS

    # Tests the .aliases property. 

    assert [o.fullName() for o in base_mod.contents['Foo'].contents['_1'].aliases] == ['base_mod.foo','base_mod.Attribute.foo']
    assert [o.fullName() for o in base_mod.contents['Foo'].contents['_3'].aliases] == ['mod.SuperSystem.foo', 'mod.SuperSystem.Attribute.foo']

@systemcls_param
def test_expandName_import_alias_wins_over_module_level_alias(systemcls: Type[model.System]) -> None:
    """
    
    """
    system = systemcls()
    fromText('''
    ssl = 1
    ''', system=system, modname='twisted.internet')
    mod = fromText('''
    try:
        from twisted.internet import ssl as _ssl
    except ImportError:
        # this code is currently simply signored
        _ssl = None
    ''', system=system, modname='mod')

    assert mod.expandName('_ssl')=="twisted.internet.ssl"
    s = mod.resolveName('_ssl')
    assert isinstance(s, model.Attribute)
    assert s.value is not None
    assert ast.literal_eval(s.value)==1

@systemcls_param
def test_expandName_alias_documentable_module_level(systemcls: Type[model.System]) -> None:

    system = systemcls()
    fromText('''
    ssl = 1
    ''', system=system, modname='twisted.internet')
    mod = fromText('''
    try:
        from twisted.internet import ssl as _ssl
        # This will create a Documentable entry
        ssl = _ssl
    except ImportError:
        # this code is ignored
        ssl = None 
    ''', system=system, modname='mod')

    assert mod.expandName('ssl')=="twisted.internet.ssl"
    assert mod.expandName('_ssl')=="twisted.internet.ssl"
    s = mod.resolveName('ssl')
    assert isinstance(s, model.Attribute)
    assert s.value is not None
    assert ast.literal_eval(s.value)==1
    assert mod.contents['ssl'].kind is model.DocumentableKind.ALIAS

@systemcls_param
def test_expandName_alias_not_documentable_class_level(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    """
    system = systemcls()
    mod = fromText('''
    import sys
    class A:
        if sys.version_info[0] > 3:
            alias = B.b
        else:
            # this code is ignored
            alias = B.a
    class B:
        a = 3
        b = 4
    ''', system=system, modname='mod')
    
    A = mod.contents['A']
    # assert capsys.readouterr().out == '', A.contents['alias']
    s = mod.resolveName('A.alias')
    assert isinstance(s, model.Attribute)
    assert s.fullName() == "mod.B.b", (names._localNameToFullName(A, 'alias'), A.contents['alias'])
    assert s.value is not None
    assert ast.literal_eval(s.value)==4
    assert mod.contents['A'].contents['alias'].kind is model.DocumentableKind.ALIAS

@systemcls_param
def test_expandName_alias_documentale_class_level(systemcls: Type[model.System]) -> None:
    system = systemcls()
    mod = fromText('''
    import sys
    class A:
        alias = None
        if sys.version_info[0] > 3:
            alias = B.b
        else:
            # this code is currently simply signored
            # because it's not in a 'body'.
            alias = B.a
    class B:
        a = 3
        b = 4
    ''', system=system, modname='mod')

    s = mod.resolveName('A.alias')
    assert isinstance(s, model.Attribute)
    assert s.fullName() == "mod.B.b"
    assert s.value is not None
    assert ast.literal_eval(s.value)==4
    assert mod.contents['A'].contents['alias'].kind is model.DocumentableKind.ALIAS

@systemcls_param
def test_aliases_property(systemcls: Type[model.System]) -> None:
    base_mod = '''
    class Z:
        pass
    '''
    src = '''
    import base_mod
    from abc import ABC
    class A(ABC):
        _1=1
        _2=2
        _3=3
        class_ = B # this is a forward reference
    
    class B(A):
        _1=a_1
        _2=A._2
        _3=A._3
        class_ = a

    a = A
    a_1 = A._1
    b = B
    bob = b.class_.class_.class_
    lol = b.class_.class_
    blu = b.class_
    mod = base_mod
    '''
    system = systemcls()
    fromText(base_mod, system=system, modname='base_mod')
    fromText(src, system=system)

    A = system.allobjects['<test>.A']
    B = system.allobjects['<test>.B']
    _base_mod = system.allobjects['base_mod']

    assert isinstance(A, model.Class)
    assert A.subclasses == [system.allobjects['<test>.B']]

    assert [o.fullName() for o in A.aliases] == ['<test>.B.class_', '<test>.a', '<test>.bob', '<test>.blu']
    assert [o.fullName() for o in B.aliases] == ['<test>.A.class_', '<test>.b', '<test>.lol']
    assert [o.fullName() for o in A.contents['_1'].aliases] == ['<test>.B._1', '<test>.a_1']
    assert [o.fullName() for o in A.contents['_2'].aliases] == ['<test>.B._2']
    assert [o.fullName() for o in A.contents['_3'].aliases] == ['<test>.B._3']
    assert [o.fullName() for o in _base_mod.aliases] == ['<test>.mod']

    # Aliases cannot currently have aliases because resolveName() always follows the aliases. 
    assert [o.fullName() for o in A.contents['class_'].aliases] == []
    assert [o.fullName() for o in B.contents['class_'].aliases] == []

@systemcls_param
def test_aliases_re_export(systemcls: Type[model.System]) -> None:

    src = '''
    # Import and re-export some external lib

    from constantly import NamedConstant, ValueConstant, FlagConstant, Names, Values, Flags
    from mylib import core
    from mylib.core import Observable
    from mylib.core._impl import Processor
    Patator = core.Patator

    __all__ = ["NamedConstant", "ValueConstant", "FlagConstant", "Names", "Values", "Flags",
               "Processor","Patator","Observable"]
    '''
    system = systemcls()
    fromText(src, system=system)
    assert system.allobjects['<test>.ValueConstant'].kind is model.DocumentableKind.ALIAS
    n = system.allobjects['<test>.NamedConstant']
    assert isinstance(n, model.Attribute)
    assert astor.to_source(n.value).strip() == 'constantly.NamedConstant' == astutils.node2fullname(n.value, n.parent)

    n = system.allobjects['<test>.Processor']
    assert isinstance(n, model.Attribute)
    assert n.kind is model.DocumentableKind.ALIAS
    assert astor.to_source(n.value).strip() == 'mylib.core._impl.Processor' == astutils.node2fullname(n.value, n.parent)

    assert system.allobjects['<test>.ValueConstant'].kind is model.DocumentableKind.ALIAS
    n = system.allobjects['<test>.Observable']
    assert isinstance(n, model.Attribute)
    assert n.kind is model.DocumentableKind.ALIAS
    assert astor.to_source(n.value).strip() == 'mylib.core.Observable' == astutils.node2fullname(n.value, n.parent)

    n = system.allobjects['<test>.Patator']
    assert isinstance(n, model.Attribute)
    assert n.kind is model.DocumentableKind.ALIAS
    assert astor.to_source(n.value).strip() == 'core.Patator'
    assert astutils.node2fullname(n.value, n.parent) == 'mylib.core.Patator'

@systemcls_param
def test_exportName_re_exported_aliases(systemcls: Type[model.System]) -> None:
    """
    What if we re-export an alias?
    """

    # TODO: fix this test.
    base_mod = '''
    class Zoo:
        _1=1
    class Hey:
        _2=2
    Z = Zoo
    H = Hey
    '''
    src = '''
    from base_mod import Z, H
    __all__ = ["Z", "H"]
    '''
    system = systemcls()

    builder = system.systemBuilder(system)
    builder.addModuleString(base_mod, modname='base_mod')
    builder.addModuleString(src, modname='mod')
    builder.buildModules()

    mod = system.allobjects['mod']
    bmod = system.allobjects['base_mod']
    alias = system.allobjects['mod.Z']

    assert mod.expandName('Z') == "Zoo" # Should be "base_mod.Zoo"
    assert mod.expandName('Z._1') == "Zoo._1" # Should be "base_mod.Zoo._1", linked to https://github.com/twisted/pydoctor/issues/295

    assert bmod.expandName('Z._1') == "base_mod.Zoo._1"
    assert bmod.expandName('Zoo._1') == "base_mod.Zoo._1"
    
    assert isinstance(alias, model.Attribute)
    assert alias.kind is model.DocumentableKind.ALIAS
    assert alias.alias == 'Zoo'

    assert alias.resolved_alias is None # This should not be None!


@systemcls_param
def test_expandName_aliasloops(systemcls: Type[model.System]) -> None:

    src = '''
    from abc import ABC
    class A(ABC):
        _1=C._2
        _2=2
    
    class B(A):
        _1=A._2
        _2=A._1

    class C(A,B):
        _1=A._1
        _2=B._2 
        # this could crash with an infitine recursion error!
    '''
    system = systemcls()
    fromText(src, system=system)
    A = system.allobjects['<test>.A']
    B = system.allobjects['<test>.B']
    C = system.allobjects['<test>.C']

    assert A.expandName('_1') == '<test>.A._1'
    assert B.expandName('_2') == '<test>.B._2'
    assert C.expandName('_2') == '<test>.C._2'
    assert C.expandName('_1') == '<test>.C._1'

@systemcls_param
def test_import_name_already_defined(systemcls: Type[model.System]) -> None:
    # from cpython asyncio/__init__.py
    mod1src = """
    def get_running_loop():
        ...

    def set_running_loop(loop):
        ...
        
    try:
        from _asyncio import (get_running_loop, set_running_loop,)
    except ImportError:
        pass
    """

    mod2src = """
    # For pydoctor, this will import the mod1 version if the names, 
    # This is probably an implementation limitation.
    # We don't handle duplicates and ambiguity in the best manner.
    # The imports are stored in a different dict than the documentable,
    # It's checked after the contents entries, which could be overriden by 
    # a name in the _localNameToFullName_map, but we don't check that currently.
    # It only works when explicitely re-exported with __all__.

    from mod1 import *
    """

    system = systemcls()
    builder = system.systemBuilder(system)
    builder.addModuleString(mod1src, 'mod1', is_package=True)
    builder.addModuleString(mod2src, 'mod2', is_package=True)
    builder.buildModules()

    mod1 = system.allobjects['mod1']
    mod2 = system.allobjects['mod2']

    assert mod2.expandName('get_running_loop') == 'mod1.get_running_loop'
    assert mod2.expandName('set_running_loop') == 'mod1.set_running_loop'
    
    assert list(mod1.contents) == ['get_running_loop', 'set_running_loop']

@systemcls_param
def test_re_export_name_defined(systemcls: Type[model.System], capsys: CapSys) -> None:
    # from cpython asyncio/__init__.py
    mod1src = """
    
    # this will export the _asyncio version if the names instead!
    __all__ = (
        'set_running_loop', 
        'get_running_loop',
    )

    def get_running_loop():
        ...

    def set_running_loop(loop):
        ...
        
    try:
        from _asyncio import (get_running_loop, set_running_loop,)
    except ImportError:
        pass
    """

    mod2src = """
    # for pydoctor, this will import the _asyncio version if the names instead!
    from mod1 import *
    """

    system = systemcls()
    builder = system.systemBuilder(system)
    builder.addModuleString(mod1src, 'mod1', is_package=True)
    builder.addModuleString(mod2src, 'mod2', is_package=True)
    builder.buildModules()

    mod1 = system.allobjects['mod1']
    mod2 = system.allobjects['mod2']

    assert mod2.expandName('get_running_loop') == '_asyncio.get_running_loop'
    assert mod2.expandName('set_running_loop') == '_asyncio.set_running_loop'

    assert mod1.contents['get_running_loop'].kind == model.DocumentableKind.ALIAS
    assert mod1.contents['set_running_loop'].kind == model.DocumentableKind.ALIAS
    
    assert list(mod1.contents) == ['get_running_loop', 'set_running_loop']
    
    out = capsys.readouterr().out
    assert all(s in out for s in ["duplicate Function 'mod1.get_running_loop'", "duplicate Function 'mod1.set_running_loop'"]), out

@systemcls_param
def test_re_export_name_defined_alt(systemcls: Type[model.System], capsys: CapSys) -> None:
    # from cpython asyncio/__init__.py
    mod1src= """
    
    # this will export the local version if the names,
    # because they are defined after the imports of the same names.
    __all__ = (
        'set_running_loop', 
        'get_running_loop',
    )

    err = False
    try:
        from _asyncio import (get_running_loop, set_running_loop,)
    except ImportError:
        err = True

    if err:
        def get_running_loop():
            ...

        def set_running_loop(loop):
            ...
    """

    mod2src = """
    # for pydoctor, this will import the mod1 version if the names. 
    # Even if in the test code, the most correct thing to do would be 
    # to export the _asyncio. 
    # Since pydoctor does not proceed with a path-sentive AST analysis,
    # the names defined in the "if err:" overrides the imports, even if 
    # in therory we could determine their exclusivity and choose the best one.

    from mod1 import *
    """

    system = systemcls()
    builder = system.systemBuilder(system)
    builder.addModuleString(mod1src, 'mod1', is_package=True)
    builder.addModuleString(mod2src, 'mod2', is_package=True)
    builder.buildModules()

    mod2 = system.allobjects['mod2']

    assert mod2.expandName('get_running_loop') == 'mod1.get_running_loop'
    assert mod2.expandName('set_running_loop') == 'mod1.set_running_loop'
    

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
    A = mod.contents['A']
    assert isinstance(A, model.Class)
    assert [b.name for b in A.allbases()] == ['A 0']

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
def test_docformat_recognition(systemcls: Type[model.System]) -> None:
    """The value assigned to __docformat__ is parsed to Module.docformat."""
    mod = fromText('''
    __docformat__ = 'Epytext en'

    def f():
        pass
    ''', systemcls=systemcls)
    assert mod.docformat == 'epytext'
    assert '__docformat__' not in mod.contents

@systemcls_param
def test_docformat_warn_not_str(systemcls: Type[model.System], capsys: CapSys) -> None:

    mod = fromText('''
    __docformat__ = [i for i in range(3)]

    def f():
        pass
    ''', systemcls=systemcls, modname='mod')
    captured = capsys.readouterr().out
    assert captured == 'mod:2: Cannot parse value assigned to "__docformat__": not a string\n'
    assert mod.docformat is None
    assert '__docformat__' not in mod.contents

@systemcls_param
def test_docformat_warn_not_str2(systemcls: Type[model.System], capsys: CapSys) -> None:

    mod = fromText('''
    __docformat__ = 3.14

    def f():
        pass
    ''', systemcls=systemcls, modname='mod')
    captured = capsys.readouterr().out
    assert captured == 'mod:2: Cannot parse value assigned to "__docformat__": not a string\n'
    assert mod.docformat == None
    assert '__docformat__' not in mod.contents

@systemcls_param
def test_docformat_warn_empty(systemcls: Type[model.System], capsys: CapSys) -> None:

    mod = fromText('''
    __docformat__ = '  '

    def f():
        pass
    ''', systemcls=systemcls, modname='mod')
    captured = capsys.readouterr().out
    assert captured == 'mod:2: Cannot parse value assigned to "__docformat__": empty value\n'
    assert mod.docformat == None
    assert '__docformat__' not in mod.contents

@systemcls_param
def test_docformat_warn_overrides(systemcls: Type[model.System], capsys: CapSys) -> None:
    mod = fromText('''
    __docformat__ = 'numpy'

    def f():
        pass

    __docformat__ = 'restructuredtext'
    ''', systemcls=systemcls, modname='mod')
    captured = capsys.readouterr().out
    assert captured == 'mod:7: Assignment to "__docformat__" overrides previous assignment\n'
    assert mod.docformat == 'restructuredtext'
    assert '__docformat__' not in mod.contents

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
    assert mod.contents['C'].contents['f'].kind is model.DocumentableKind.CLASS_METHOD
    mod = fromText('''
    class C:
        def f(klass):
            pass
        f = classmethod(f)
    ''', systemcls=systemcls)
    assert mod.contents['C'].contents['f'].kind is model.DocumentableKind.CLASS_METHOD

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
    assert isinstance(C, model.Class)
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
    assert isinstance(C, model.Class)
    assert len(C.decorators) == 1
    (name, args), = C.decorators
    assert name == 'test.cd'
    assert args is not None
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
    assert C.contents['method_undecorated'].kind is model.DocumentableKind.METHOD
    assert C.contents['method_static'].kind is model.DocumentableKind.STATIC_METHOD
    assert C.contents['method_class'].kind is model.DocumentableKind.CLASS_METHOD
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
    mod_a = fromText('''
    def f(): pass
    ''', modname='a', is_package=True, system=system)
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
    fromText('''
    # This module intentionally left blank.
    ''', modname='a', system=system, is_package=True)
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
    assert a.privacyClass is model.PrivacyClass.PUBLIC
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
    assert a.privacyClass is model.PrivacyClass.PUBLIC
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
    assert a.privacyClass is model.PrivacyClass.PUBLIC
    assert a.kind is model.DocumentableKind.INSTANCE_VARIABLE
    b = C.contents['_b']
    assert b.docstring == """inline doc for _b"""
    assert b.privacyClass is model.PrivacyClass.PRIVATE
    assert b.kind is model.DocumentableKind.INSTANCE_VARIABLE
    c = C.contents['c']
    assert c.docstring == """inline doc for c"""
    assert c.privacyClass is model.PrivacyClass.PUBLIC
    assert c.kind is model.DocumentableKind.INSTANCE_VARIABLE
    d = C.contents['d']
    assert d.docstring == """inline doc for d"""
    assert d.privacyClass is model.PrivacyClass.PUBLIC
    assert d.kind is model.DocumentableKind.INSTANCE_VARIABLE
    e = C.contents['e']
    assert not e.docstring
    f = C.contents['f']
    assert f.docstring == """inline doc for f"""
    assert f.privacyClass is model.PrivacyClass.PUBLIC
    assert f.kind is model.DocumentableKind.INSTANCE_VARIABLE

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
    assert fun.kind is model.DocumentableKind.FUNCTION
    assert fun.docstring == """Happy Happy Joy Joy"""
    CLS = mod.contents['CLS']
    assert CLS.kind is model.DocumentableKind.CLASS
    assert CLS.docstring == """Clears the screen"""
    method1 = CLS.contents['method1']
    assert method1.kind is model.DocumentableKind.METHOD
    assert method1.docstring == "Updated docstring #1"
    method2 = CLS.contents['method2']
    assert method2.kind is model.DocumentableKind.METHOD
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
    assert l1.kind is model.DocumentableKind.VARIABLE
    assert l1.docstring == """module-level l"""
    m1 = mod.contents['m']
    assert m1.kind is model.DocumentableKind.VARIABLE
    assert m1.docstring == """module-level m"""
    C = mod.contents['C']
    assert sorted(C.contents.keys()) == ['__init__', 'a', 'k', 'l', 'm']
    a = C.contents['a']
    assert a.kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert a.docstring == """inline doc for a"""
    k = C.contents['k']
    assert k.kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert unwrap(k.parsed_docstring) == """class level doc for k"""
    l2 = C.contents['l']
    assert l2.kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert l2.docstring == """instance l"""
    m2 = C.contents['m']
    assert m2.kind is model.DocumentableKind.CLASS_VARIABLE
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
    assert a.kind is model.DocumentableKind.CLASS_VARIABLE
    b = C.contents['b']
    assert unwrap(b.parsed_docstring) == """second"""
    assert str(unwrap(b.parsed_type)) == 'string'
    assert b.kind is model.DocumentableKind.CLASS_VARIABLE
    c = C.contents['c']
    assert c.docstring == """third"""
    assert str(unwrap(c.parsed_type)) == 'string'
    assert c.kind is model.DocumentableKind.CLASS_VARIABLE
    d = C.contents['d']
    assert unwrap(d.parsed_docstring) == """fourth"""
    assert str(unwrap(d.parsed_type)) == 'string'
    assert d.kind is model.DocumentableKind.INSTANCE_VARIABLE
    e = C.contents['e']
    assert unwrap(e.parsed_docstring) == """fifth"""
    assert str(unwrap(e.parsed_type)) == 'string'
    assert e.kind is model.DocumentableKind.INSTANCE_VARIABLE
    f = C.contents['f']
    assert f.docstring == """sixth"""
    assert str(unwrap(f.parsed_type)) == 'string'
    assert f.kind is model.DocumentableKind.INSTANCE_VARIABLE
    g = C.contents['g']
    assert g.docstring == """seventh"""
    assert str(unwrap(g.parsed_type)) == 'string'
    assert g.kind is model.DocumentableKind.INSTANCE_VARIABLE

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
    assert type2str(cast(model.Attribute, mod.contents['d']).annotation) == 'dict[str, int]'
    # We don't use ignore comments for anything at the moment,
    # but do verify that their presence doesn't break things.
    assert type2str(cast(model.Attribute, mod.contents['i']).annotation) == 'list'
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
    assert isinstance(cast(model.Attribute, mod.contents['x']).annotation, ast.expr)
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
    assert cast(model.Attribute, C.contents['n']).annotation is None
    # These expressions are considered too complex for pydoctor.
    # Maybe we can use an external type inferrer at some point.
    assert cast(model.Attribute, C.contents['x']).annotation is None
    assert cast(model.Attribute, C.contents['y']).annotation is None
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

    A = C.contents['a']
    B = C.contents['b']
    _C = C.contents['c']
    D = C.contents['d']
    E = C.contents['e']

    assert isinstance(A, model.Attribute)
    assert isinstance(B, model.Attribute)
    assert isinstance(_C, model.Attribute)
    assert isinstance(D, model.Attribute)
    assert isinstance(E, model.Attribute)

    assert type2str(A.annotation) == 'int'
    assert type2str(B.annotation) == 'int'
    assert type2str(_C.annotation) == 'C'
    assert type2str(D.annotation) == 'bool'
    assert type2str(E.annotation) == 'int'

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
    assert C.contents['a'].kind is model.DocumentableKind.INSTANCE_VARIABLE

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
    assert C.contents['a'].kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert C.contents['b'].kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert C.contents['c'].kind is model.DocumentableKind.CLASS_VARIABLE
    assert C.contents['d'].kind is model.DocumentableKind.CLASS_VARIABLE

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
    assert prop.kind is model.DocumentableKind.PROPERTY
    assert prop.docstring == """For sale."""
    assert type2str(prop.annotation) == 'str'

    oldschool = C.contents['oldschool']
    assert isinstance(oldschool, model.Attribute)
    assert oldschool.kind is model.DocumentableKind.PROPERTY
    assert isinstance(oldschool.parsed_docstring, ParsedEpytextDocstring)
    assert unwrap(oldschool.parsed_docstring) == """For rent."""
    assert flatten(format_summary(oldschool)) == 'For rent.'
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
    assert getter.kind is model.DocumentableKind.PROPERTY
    assert getter.docstring == """Getter."""

    setter = C.contents['prop.setter']
    assert isinstance(setter, model.Function)
    assert setter.kind is model.DocumentableKind.METHOD
    assert setter.docstring == """Setter."""

    deleter = C.contents['prop.deleter']
    assert isinstance(deleter, model.Function)
    assert deleter.kind is model.DocumentableKind.METHOD
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
    assert deprecated.kind is model.DocumentableKind.PROPERTY

    async_prop = C.contents['remote_value']
    assert isinstance(async_prop, model.Attribute)
    assert async_prop.kind is model.DocumentableKind.PROPERTY

    abstract_prop = C.contents['name']
    assert isinstance(abstract_prop, model.Attribute)
    assert abstract_prop.kind is model.DocumentableKind.PROPERTY


@pytest.mark.parametrize('decoration', ('classmethod', 'staticmethod'))
@systemcls_param
def test_property_conflict(
        decoration: str, systemcls: Type[model.System], capsys: CapSys
        ) -> None:
    """Warn when a method is decorated as both property and class/staticmethod.
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
    assert C.contents['prop'].kind is model.DocumentableKind.PROPERTY
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

@systemcls_param
def test_constant_module(systemcls: Type[model.System]) -> None:
    """
    Module variables with all-uppercase names are recognized as constants.
    """
    mod = fromText('''
    LANG = 'FR'
    ''', systemcls=systemcls)
    lang = mod.contents['LANG']
    assert isinstance(lang, model.Attribute)
    assert lang.kind is model.DocumentableKind.CONSTANT
    assert ast.literal_eval(getattr(mod.resolveName('LANG'), 'value')) == 'FR'

@systemcls_param
def test_constant_module_with_final(systemcls: Type[model.System]) -> None:
    """
    Module variables annotated with typing.Final are recognized as constants.
    """
    mod = fromText('''
    from typing import Final
    lang: Final = 'fr'
    ''', systemcls=systemcls)
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'fr'

@systemcls_param
def test_constant_module_with_typing_extensions_final(systemcls: Type[model.System]) -> None:
    """
    Module variables annotated with typing_extensions.Final are recognized as constants.
    """
    mod = fromText('''
    from typing_extensions import Final
    lang: Final = 'fr'
    ''', systemcls=systemcls)
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'fr'

@systemcls_param
def test_constant_module_with_final_subscript1(systemcls: Type[model.System]) -> None:
    """
    It can recognize constants defined with typing.Final[something]
    """
    mod = fromText('''
    from typing import Final
    lang: Final[Sequence[str]] = ('fr', 'en')
    ''', systemcls=systemcls)
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == ('fr', 'en')
    assert astor.to_source(attr.annotation).strip() == "Sequence[str]"

@systemcls_param
def test_constant_module_with_final_subscript2(systemcls: Type[model.System]) -> None:
    """
    It can recognize constants defined with typing.Final[something]. 
    And it automatically remove the Final part from the annotation.
    """
    mod = fromText('''
    import typing
    lang: typing.Final[tuple] = ('fr', 'en')
    ''', systemcls=systemcls)
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == ('fr', 'en')
    assert astbuilder.node2fullname(attr.annotation, attr) == "tuple"

@systemcls_param
def test_constant_module_with_final_subscript_invalid_warns(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    It warns if there is an invalid Final annotation.
    """
    mod = fromText('''
    from typing import Final
    lang: Final[tuple, 12:13] = ('fr', 'en')
    ''', systemcls=systemcls, modname='mod')
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == ('fr', 'en')
    
    captured = capsys.readouterr().out
    assert "mod:3: Annotation is invalid, it should not contain slices.\n" == captured

    assert astor.to_source(attr.annotation).strip() == "tuple[str, ...]"

@systemcls_param
def test_constant_module_with_final_subscript_invalid_warns2(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    It warns if there is an invalid Final annotation.
    """
    mod = fromText('''
    import typing
    lang: typing.Final[12:13] = ('fr', 'en')
    ''', systemcls=systemcls, modname='mod')
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == ('fr', 'en')
    
    captured = capsys.readouterr().out
    assert "mod:3: Annotation is invalid, it should not contain slices.\n" == captured

    assert astor.to_source(attr.annotation).strip() == "tuple[str, ...]"

@systemcls_param
def test_constant_module_with_final_annotation_gets_infered(systemcls: Type[model.System]) -> None:
    """
    It can recognize constants defined with typing.Final. 
    It will infer the type of the constant if Final do not use subscripts.
    """
    mod = fromText('''
    import typing
    lang: typing.Final = 'fr'
    ''', systemcls=systemcls)
    attr = mod.resolveName('lang')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'fr'
    assert astbuilder.node2fullname(attr.annotation, attr) == "str"

@systemcls_param
def test_constant_class(systemcls: Type[model.System]) -> None:
    """
    Class variables with all-uppercase names are recognized as constants.
    """
    mod = fromText('''
    class Clazz:
        """Class."""
        LANG = 'FR'
    ''', systemcls=systemcls)
    attr = mod.resolveName('Clazz.LANG')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'FR'


@systemcls_param
def test_all_caps_variable_in_instance_is_not_a_constant(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    Currently, it does not mark instance members as constants, never.
    """
    mod = fromText('''
    from typing import Final
    class Clazz:
        """Class."""
        def __init__(**args):
            self.LANG: Final = 'FR'
    ''', systemcls=systemcls)
    attr = mod.resolveName('Clazz.LANG')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.INSTANCE_VARIABLE
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'FR'
    captured = capsys.readouterr().out
    assert not captured

@systemcls_param
def test_constant_override_in_instace_warns(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    It warns when a constant is beeing re defined in instance. But it ignores it's value. 
    """
    mod = fromText('''
    class Clazz:
        """Class."""
        LANG = 'EN'
        def __init__(self, **args):
            self.LANG = 'FR'
    ''', systemcls=systemcls, modname="mod")
    attr = mod.resolveName('Clazz.LANG')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'EN'

    captured = capsys.readouterr().out
    assert "mod:6: Assignment to constant \"LANG\" inside an instance is ignored, this value will not be part of the docs.\n" == captured

@systemcls_param
def test_constant_override_in_instace_warns2(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    It warns when a constant is beeing re defined in instance. But it ignores it's value. 
    Even if the actual constant definition is detected after the instance variable of the same name.
    """
    mod = fromText('''
    class Clazz:
        """Class."""
        def __init__(self, **args):
            self.LANG = 'FR'
        LANG = 'EN'
    ''', systemcls=systemcls, modname="mod")
    attr = mod.resolveName('Clazz.LANG')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 'EN'

    captured = capsys.readouterr().out
    assert "mod:5: Assignment to constant \"LANG\" inside an instance is ignored, this value will not be part of the docs.\n" == captured

@systemcls_param
def test_constant_override_in_module_warns(systemcls: Type[model.System], capsys: CapSys) -> None:

    mod = fromText('''
    """Mod."""
    import sys
    IS_64BITS = False
    if sys.maxsize > 2**32:
        IS_64BITS = True
    ''', systemcls=systemcls, modname="mod")
    attr = mod.resolveName('IS_64BITS')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == True

    captured = capsys.readouterr().out
    assert "mod:6: Assignment to constant \"IS_64BITS\" overrides previous assignment at line 4, the original value will not be part of the docs.\n" == captured

@systemcls_param
def test_constant_override_do_not_warns_when_defined_in_class_docstring(systemcls: Type[model.System], capsys: CapSys) -> None:
    """
    Constant can be documented as variables at docstring level without any warnings.
    """
    mod = fromText('''
    class Clazz:
        """
        @cvar LANG: French.
        """
        LANG = 99
    ''', systemcls=systemcls, modname="mod")
    attr = mod.resolveName('Clazz.LANG')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 99
    captured = capsys.readouterr().out
    assert not captured

@systemcls_param
def test_constant_override_do_not_warns_when_defined_in_module_docstring(systemcls: Type[model.System], capsys: CapSys) -> None:

    mod = fromText('''
    """
    @var LANG: French.
    """
    LANG = 99
    ''', systemcls=systemcls, modname="mod")
    attr = mod.resolveName('LANG')
    assert isinstance(attr, model.Attribute)
    assert attr.kind == model.DocumentableKind.CONSTANT
    assert attr.value is not None
    assert ast.literal_eval(attr.value) == 99
    captured = capsys.readouterr().out
    assert not captured

@systemcls_param
def test__name__equals__main__is_skipped(systemcls: Type[model.System]) -> None:
    """
    Code inside of C{if __name__ == '__main__'} should be skipped.
    """
    mod = fromText('''
    foo = True

    if __name__ == '__main__':
        var = True

        def fun():
            pass

        class Class:
            pass

    def bar():
        pass
    ''', modname='test', systemcls=systemcls)
    assert tuple(mod.contents) == ('foo', 'bar')

@systemcls_param
def test_variable_named_like_current_module(systemcls: Type[model.System]) -> None:
    """
    Test for U{issue #474<https://github.com/twisted/pydoctor/issues/474>}.
    """
    mod = fromText('''
    example = True
    ''', systemcls=systemcls, modname="example")
    assert 'example' in mod.contents

@systemcls_param
def test_package_name_clash(systemcls: Type[model.System]) -> None:
    system = systemcls()
    builder = system.systemBuilder(system)

    builder.addModuleString('', 'mod', is_package=True)
    builder.addModuleString('', 'sub', parent_name='mod', is_package=True)

    assert isinstance(system.allobjects['mod.sub'], model.Module)

    # The following statement completely overrides module 'mod' and all it's submodules.
    builder.addModuleString('', 'mod', is_package=True)

    with pytest.raises(KeyError):
        system.allobjects['mod.sub']

    builder.addModuleString('', 'sub2', parent_name='mod', is_package=True)

    assert isinstance(system.allobjects['mod.sub2'], model.Module)

@systemcls_param
def test_reexport_wildcard(systemcls: Type[model.System]) -> None:
    """
    If a target module,
    explicitly re-export via C{__all__} a set of names
    that were initially imported from a sub-module via a wildcard,
    those names are documented as part of the target module.
    """
    system = systemcls()
    builder = system.systemBuilder(system)
    builder.addModuleString('''
    from ._impl import *
    from _impl2 import *
    __all__ = ['f', 'g', 'h', 'i', 'j']
    ''', modname='top', is_package=True)

    builder.addModuleString('''
    def f(): 
        pass
    def g():
        pass
    def h():
        pass
    ''', modname='_impl', parent_name='top')
    
    builder.addModuleString('''
    class i: pass
    class j: pass
    ''', modname='_impl2')

    builder.buildModules()

    assert system.allobjects['top._impl'].resolveName('f') == system.allobjects['top'].contents['f']
    assert system.allobjects['_impl2'].resolveName('i') == system.allobjects['top'].contents['i']
    assert all(n in system.allobjects['top'].contents for n in  ['f', 'g', 'h', 'i', 'j'])

@systemcls_param
def test_module_level_attributes_and_aliases(systemcls: Type[model.System]) -> None:
    """
    Currently, the first analyzed assigment wins, basically. I believe further logic should be added
    such that definitions in the orelse clause of the Try node is processed before the 
    except handlers. This way could define our aliases both there and in the body of the
    Try node and fall back to what's defnied in the handlers if the names doesn't exist yet.
    """
    system = systemcls()
    builder = system.systemBuilder(system)
    builder.addModuleString('''
    ssl = 1
    ''', modname='twisted.internet')
    builder.addModuleString('''
    try:
        from twisted.internet import ssl as _ssl
        # The first analyzed assigment to an alias wins.
        ssl = _ssl
        # For classic variables, the rules are the same.
        var = 1
        # For constants, the rules are still the same.
        VAR = 1
        # Looks like a constant, but should be treated like an alias
        ALIAS = _ssl
    except ImportError:
        ssl = None
        var = 2
        VAR = 2
        ALIAS = None
    ''', modname='mod')
    builder.buildModules()
    mod = system.allobjects['mod']
    
    # Test alias
    assert mod.expandName('ssl')=="twisted.internet.ssl"
    assert mod.expandName('_ssl')=="twisted.internet.ssl"
    s = mod.resolveName('ssl')
    assert isinstance(s, model.Attribute)
    assert s.value is not None
    assert ast.literal_eval(s.value)==1
    assert s.kind == model.DocumentableKind.VARIABLE
    
    # Test variable
    assert mod.expandName('var')=="mod.var"
    v = mod.resolveName('var')
    assert isinstance(v, model.Attribute)
    assert v.value is not None
    assert ast.literal_eval(v.value)==1
    assert v.kind == model.DocumentableKind.VARIABLE

    # Test constant
    assert mod.expandName('VAR')=="mod.VAR"
    V = mod.resolveName('VAR')
    assert isinstance(V, model.Attribute)
    assert V.value is not None
    assert ast.literal_eval(V.value)==1
    assert V.kind == model.DocumentableKind.CONSTANT

    # Test looks like constant but actually an alias.
    assert mod.expandName('ALIAS')=="twisted.internet.ssl"
    s = mod.resolveName('ALIAS')
    assert isinstance(s, model.Attribute)
    assert s.value is not None
    assert ast.literal_eval(s.value)==1
    assert s.kind == model.DocumentableKind.VARIABLE

