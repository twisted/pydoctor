from typing import List, Optional, Type
import pytest

from pydoctor import model, stanutils
from pydoctor.templatewriter import pages, util
from pydoctor.test.test_astbuilder import fromText, systemcls_param
from pydoctor.test import CapSys

def assert_mro_equals(klass: Optional[model.Documentable], expected_mro: List[str]) -> None:
    assert isinstance(klass, model.Class)
    assert [member.fullName() if isinstance(member, model.Documentable) else member for member in klass.mro(True)] == expected_mro

@systemcls_param
def test_mro(systemcls: Type[model.System],) -> None:
    mod = fromText("""\
    from mod import External
    class C: pass
    class D(C): pass
    class A1: pass
    class B1(A1): pass
    class C1(A1): pass
    class D1(B1, C1): pass
    class E1(C1, B1): pass
    class F1(D1, E1): pass
    class G1(E1, D1): pass
    class Boat: pass
    class DayBoat(Boat): pass
    class WheelBoat(Boat): pass
    class EngineLess(DayBoat): pass
    class SmallMultihull(DayBoat): pass
    class PedalWheelBoat(EngineLess, WheelBoat): pass
    class SmallCatamaran(SmallMultihull): pass
    class Pedalo(PedalWheelBoat, SmallCatamaran): pass
    class OuterA:
        class Inner:
            pass
    class OuterB(OuterA):
        class Inner(OuterA.Inner):
            pass
    class OuterC(OuterA):
        class Inner(OuterA.Inner):
            pass
    class OuterD(OuterC):
        class Inner(OuterC.Inner, OuterB.Inner):
            pass
    class Duplicates(C, C): pass
    class Extension(External): pass
    class MycustomString(str): pass
    from typing import Generic
    class MyGeneric(Generic[T]):...
    class Visitor(MyGeneric[T]):...
    import ast
    class GenericPedalo(MyGeneric[ast.AST], Pedalo):...
    """, 
    modname='mro', systemcls=systemcls
    )
    assert_mro_equals(mod.contents["D"], ["mro.D", "mro.C"])
    assert_mro_equals(mod.contents["D1"], ['mro.D1', 'mro.B1', 'mro.C1', 'mro.A1'])
    assert_mro_equals(mod.contents["E1"], ['mro.E1', 'mro.C1', 'mro.B1', 'mro.A1'])
    assert_mro_equals(mod.contents["Extension"], ["mro.Extension", "mod.External"])
    assert_mro_equals(mod.contents["MycustomString"], ["mro.MycustomString", "str"])
    
    assert_mro_equals(
        mod.contents["PedalWheelBoat"],
        ["mro.PedalWheelBoat", "mro.EngineLess", "mro.DayBoat", "mro.WheelBoat", "mro.Boat"],
    )

    assert_mro_equals(
        mod.contents["SmallCatamaran"],
        ["mro.SmallCatamaran", "mro.SmallMultihull", "mro.DayBoat", "mro.Boat"],
    )

    assert_mro_equals(
        mod.contents["Pedalo"],
        [
            "mro.Pedalo",
            "mro.PedalWheelBoat",
            "mro.EngineLess",
            "mro.SmallCatamaran",
            "mro.SmallMultihull",
            "mro.DayBoat",
            "mro.WheelBoat",
            "mro.Boat"
        ],
    )

    assert_mro_equals(
        mod.contents["OuterD"].contents["Inner"],
        ['mro.OuterD.Inner', 
        'mro.OuterC.Inner',
        'mro.OuterB.Inner', 
        'mro.OuterA.Inner']
    )

    assert_mro_equals(
        mod.contents["Visitor"],
        ['mro.Visitor', 'mro.MyGeneric', 'typing.Generic']
    )

    assert_mro_equals(
        mod.contents["GenericPedalo"],
        ['mro.GenericPedalo',
        'mro.MyGeneric',
        'typing.Generic',
        'mro.Pedalo',
        'mro.PedalWheelBoat',
        'mro.EngineLess',
        'mro.SmallCatamaran',
        'mro.SmallMultihull',
        'mro.DayBoat',
        'mro.WheelBoat',
        'mro.Boat'])

    with pytest.raises(ValueError, match="Cannot compute linearization"):
        model.compute_mro(mod.contents["F1"]) # type:ignore
    with pytest.raises(ValueError, match="Cannot compute linearization"):
        model.compute_mro(mod.contents["G1"]) # type:ignore
    with pytest.raises(ValueError, match="Cannot compute linearization"):
        model.compute_mro(mod.contents["Duplicates"]) # type:ignore

def test_mro_cycle(capsys:CapSys) -> None:
    fromText("""\
    class A(D):...
    class B:...
    class C(A,B):...
    class D(C):...
    """, modname='cycle')
    assert capsys.readouterr().out == '''cycle:1: Cycle found while computing inheritance hierarchy: cycle.A -> cycle.D -> cycle.C -> cycle.A
cycle:3: Cycle found while computing inheritance hierarchy: cycle.C -> cycle.A -> cycle.D -> cycle.C
cycle:4: Cycle found while computing inheritance hierarchy: cycle.D -> cycle.C -> cycle.A -> cycle.D
'''

def test_inherited_docsources()-> None:
    simple = fromText("""\
    class A:
        def a():...
    class B:
        def b():...
    class C(A,B):
        def a():...
        def b():...
    """, modname='normal')

    assert [o.fullName() for o in list(simple.contents['A'].contents['a'].docsources())] == ['normal.A.a']
    assert [o.fullName() for o in list(simple.contents['B'].contents['b'].docsources())] == ['normal.B.b']
    assert [o.fullName() for o in list(simple.contents['C'].contents['b'].docsources())] == ['normal.C.b','normal.B.b']
    assert [o.fullName() for o in list(simple.contents['C'].contents['a'].docsources())] == ['normal.C.a','normal.A.a']

    dimond = fromText("""\
    class _MyBase:
        def z():...
    class A(_MyBase):
        def a():...
        def z():...
    class B(_MyBase):
        def b():...
    class C(A,B):
        def a():...
        def b():...
        def z():...
    """, modname='diamond')

    assert [o.fullName() for o in list(dimond.contents['A'].contents['a'].docsources())] == ['diamond.A.a']
    assert [o.fullName() for o in list(dimond.contents['A'].contents['z'].docsources())] == ['diamond.A.z', 'diamond._MyBase.z']
    assert [o.fullName() for o in list(dimond.contents['B'].contents['b'].docsources())] == ['diamond.B.b']
    assert [o.fullName() for o in list(dimond.contents['C'].contents['b'].docsources())] == ['diamond.C.b','diamond.B.b']
    assert [o.fullName() for o in list(dimond.contents['C'].contents['a'].docsources())] == ['diamond.C.a','diamond.A.a']
    assert [o.fullName() for o in list(dimond.contents['C'].contents['z'].docsources())] == ['diamond.C.z','diamond.A.z', 'diamond._MyBase.z']

def test_overriden_in()-> None:

    simple = fromText("""\
    class A:
        def a():...
    class B:
        def b():...
    class C(A,B):
        def a():...
        def b():...
    """, modname='normal')
    assert stanutils.flatten_text(
        pages.get_override_info(simple.contents['A'],  # type:ignore
                          'a')) == 'overridden in normal.C'
    assert stanutils.flatten_text( 
        pages.get_override_info(simple.contents['B'],  # type:ignore
                          'b')) == 'overridden in normal.C'

    dimond = fromText("""\
    class _MyBase:
        def z():...
    class A(_MyBase):
        def a():...
        def z():...
    class B(_MyBase):
        def b():...
    class C(A,B):
        def a():...
        def b():...
        def z():...
    """, modname='diamond')

    assert stanutils.flatten_text(
        pages.get_override_info(dimond.contents['A'],  # type:ignore
                          'a')) == 'overridden in diamond.C'
    assert stanutils.flatten_text(
        pages.get_override_info(dimond.contents['B'],  # type:ignore
                          'b')) == 'overridden in diamond.C'
    assert stanutils.flatten_text(
        pages.get_override_info(dimond.contents['_MyBase'], #type:ignore
                          'z')) == 'overridden in diamond.A, diamond.C'
    
    assert stanutils.flatten_text(
        pages.get_override_info(dimond.contents['A'],  # type:ignore
                          'z')) == ('overrides diamond._MyBase.z'
                                    'overridden in diamond.C')
    assert stanutils.flatten_text(
        pages.get_override_info(dimond.contents['C'],  # type:ignore
                          'z')) == 'overrides diamond.A.z'
                          
    klass = dimond.contents['_MyBase']
    assert isinstance(klass, model.Class)
    assert klass.subclasses == [dimond.contents['A'], dimond.contents['B']]
    assert list(util.overriding_subclasses(klass, 'z')) == [dimond.contents['A'], dimond.contents['C']]

def test_inherited_members() -> None:
    """
    The inherited_members() function computes only the inherited members
    of a given class. It does not include members defined in the class itself.
    """
    dimond = fromText("""\
    class _MyBase:
        def z():...
    class A(_MyBase):
        def a():...
        def z():...
    class B(_MyBase):
        def b():...
    class C(A,B): 
        ...
    """, modname='diamond')

    assert len(util.inherited_members(dimond.contents['B']))==1 # type:ignore
    assert len(util.inherited_members(dimond.contents['C']))==3 # type:ignore
    assert len(util.inherited_members(dimond.contents['A']))==0 # type:ignore
    assert len(util.inherited_members(dimond.contents['_MyBase']))==0 # type:ignore
