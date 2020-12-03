from typing import Type
import os

from pydoctor import model

testpackages = os.path.join(os.path.dirname(__file__), 'testpackages')

def processPackage(packname: str, systemcls: Type[model.System] = model.System) -> model.System:
    testpackage = os.path.join(testpackages, packname)
    system = systemcls()
    system.addPackage(testpackage)
    system.process()
    return system

def test_relative_import() -> None:
    system = processPackage("relativeimporttest")
    cls = system.allobjects['relativeimporttest.mod1.C']
    assert isinstance(cls, model.Class)
    assert cls.bases == ['relativeimporttest.mod2.B']

def test_package_docstring() -> None:
    system = processPackage("relativeimporttest")
    assert (system.allobjects['relativeimporttest.__init__'].docstring ==
            "DOCSTRING")

def test_modnamedafterbuiltin() -> None:
    # well, basically the test is that this doesn't explode:
    system = processPackage("modnamedafterbuiltin")
    # but let's test _something_
    dict_class = system.allobjects['modnamedafterbuiltin.mod.Dict']
    assert isinstance(dict_class, model.Class)
    assert dict_class.baseobjects == [None]

def test_nestedconfusion() -> None:
    system = processPackage("nestedconfusion")
    A = system.allobjects['nestedconfusion.mod.nestedconfusion.A']
    assert isinstance(A, model.Class)
    C = system.allobjects['nestedconfusion.mod.C']
    assert A.baseobjects[0] is C

def test_importingfrompackage() -> None:
    system = processPackage("importingfrompackage")
    system.getProcessedModule('importingfrompackage.mod')
    submod = system.allobjects['importingfrompackage.subpack.submod']
    assert isinstance(submod, model.Module)
    assert submod.state is model.ProcessingState.PROCESSED

def test_allgames() -> None:
    """
    Test reparenting of documentables.
    A name which is defined in module 1, but included in __all__ of module 2
    that it is imported into, should end up in the documentation of module 2.
    """

    system = processPackage("allgames")
    mod1 = system.allobjects['allgames.mod1']
    assert isinstance(mod1, model.Module)
    mod2 = system.allobjects['allgames.mod2']
    assert isinstance(mod2, model.Module)
    # InSourceAll is not moved into mod2, but NotInSourceAll is.
    assert 'InSourceAll' in mod1.contents
    assert 'NotInSourceAll' in mod2.contents
    # Source paths must be unaffected by the move, so that error messages
    # point to the right source code.
    moved = mod2.contents['NotInSourceAll']
    assert isinstance(moved, model.Class)
    assert moved.source_path is not None
    assert moved.source_path.parts[-2:] == ('allgames', 'mod1.py')
    assert moved.parentMod is mod2
    assert moved.parentMod.source_path is not None
    assert moved.parentMod.source_path.parts[-2:] == ('allgames', 'mod2.py')

def test_cyclic_imports() -> None:
    """
    Test whether names are resolved correctly when we have import cycles.
    The test package contains module 'a' that defines class 'A' and module 'b'
    that defines class 'B'; each module imports the other. Since the test data
    is symmetrical, we will at some point be importing a module that has not
    been fully processed yet, no matter which module gets processed first.
    """

    system = processPackage('cyclic_imports')
    mod_a = system.allobjects['cyclic_imports.a']
    assert mod_a.expandName('B') == 'cyclic_imports.b.B'
    mod_b = system.allobjects['cyclic_imports.b']
    assert mod_b.expandName('A') == 'cyclic_imports.a.A'
