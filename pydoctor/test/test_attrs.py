from typing import Type

from pydoctor import epydoc2stan, model
from pydoctor.extensions import attrs
from pydoctor.stanutils import flatten_text
from pydoctor.templatewriter import pages
from pydoctor.test import CapSys

from pydoctor.test.test_astbuilder import fromText, AttrsSystem, type2str

import pytest

attrs_systemcls_param = pytest.mark.parametrize(
    'systemcls', (model.System, # system with all extensions enalbed
                  AttrsSystem, # system with attrs extension only
                 ))

@attrs_systemcls_param
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

@attrs_systemcls_param
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

@attrs_systemcls_param
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

@attrs_systemcls_param
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
    assert isinstance(C, attrs.AttrsClass)
    assert C.attrs_auto_attribs == True
    assert C.contents['a'].kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert C.contents['b'].kind is model.DocumentableKind.INSTANCE_VARIABLE
    assert C.contents['c'].kind is model.DocumentableKind.CLASS_VARIABLE
    assert C.contents['d'].kind is model.DocumentableKind.CLASS_VARIABLE

@attrs_systemcls_param
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
        'test:13: Unable to figure out value for \'auto_attribs\' argument to attr.s(), maybe too complex\n'
        'test:16: Value for "auto_attribs" argument has type "int", expected "bool"\n'
        )

@attrs_systemcls_param
def test_attrs_init_method(systemcls: Type[model.System], capsys: CapSys) -> None:
    src = '''\
    @attr.s
    class C(object):
        c = attr.ib(default=100)
        x = attr.ib(default=1)
        b = attr.ib(default=23)

    @attr.s
    class D(C):
        a = attr.ib(default=42)
        x = attr.ib(default=2)
        d = attr.ib(default=3.14)
    '''
    mod = fromText(src, systemcls=systemcls)
    C = mod.contents['C']
    constructor = C.contents['__init__']
    assert isinstance(constructor, model.Function)
    assert epydoc2stan.format_constructor_short_text(constructor, forclass=C) == 'C(c, x, b)'
    assert flatten_text(pages.format_signature(constructor)) == '(self, c=100, x=1, b=23)'
