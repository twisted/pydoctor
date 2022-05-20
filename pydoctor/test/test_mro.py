from typing import List, Optional, Type
import pytest

from pydoctor import model
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

    with pytest.raises(ValueError, match="Cannot compute linearization"):
        model.compute_mro(mod.contents["F1"]) # type:ignore
    with pytest.raises(ValueError, match="Cannot compute linearization"):
        model.compute_mro(mod.contents["G1"]) # type:ignore
    with pytest.raises(ValueError, match="Cannot compute linearization"):
        model.compute_mro(mod.contents["Duplicates"]) # type:ignore

def test_mro_cycle(capsys:CapSys) -> None:
    mod = fromText("""\
    class A(D):...
    class B:...
    class C(A,B):...
    class D(C):...
    """, modname='cycle')
    assert capsys.readouterr().out == '''cycle:1: Cycle found while computing inheritance hierarchy: cycle.A -> cycle.D -> cycle.C -> cycle.A
cycle:3: Cycle found while computing inheritance hierarchy: cycle.C -> cycle.A -> cycle.D -> cycle.C
cycle:4: Cycle found while computing inheritance hierarchy: cycle.D -> cycle.C -> cycle.A -> cycle.D
'''
