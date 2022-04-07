from pathlib import Path
from typing import Callable
import pytest

from pydoctor import model

testpackages = Path(__file__).parent / 'testpackages'

def processPackage(packname: str, systemcls: Callable[[], model.System] = model.System) -> model.System:
    system = systemcls()
    system.addPackage(testpackages / packname)
    system.process()
    return system

def test_relative_import() -> None:
    system = processPackage("relativeimporttest")
    cls = system.allobjects['relativeimporttest.mod1.C']
    assert isinstance(cls, model.Class)
    assert cls.bases == ['relativeimporttest.mod2.B']

def test_package_docstring() -> None:
    system = processPackage("relativeimporttest")
    assert system.allobjects['relativeimporttest'].docstring == "DOCSTRING"

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

def test_package_module_name_clash() -> None:
    """
    When a module and a package have the same full name, the package wins.
    """
    system = processPackage('package_module_name_clash')
    pack = system.allobjects['package_module_name_clash.pack']
    assert 'package' == pack.contents.popitem()[0]

def test_reparented_module() -> None:
    """
    A module that is imported in a package as a different name and exported
    in that package under the new name via C{__all__} is presented using the
    new name.
    """
    system = processPackage('reparented_module')

    mod = system.allobjects['reparented_module.module']
    top = system.allobjects['reparented_module']

    assert mod.fullName() == 'reparented_module.module'
    assert top.resolveName('module') is top.contents['module']
    assert top.resolveName('module.f') is mod.contents['f']

    # The module old name is not in allobjects
    assert 'reparented_module.mod' not in system.allobjects
    # But can still be resolved with it's old name
    assert top.resolveName('mod') is top.contents['module']

def test_reparenting_follows_aliases() -> None:
    """
    Test for https://github.com/twisted/pydoctor/issues/505

    Reparenting process follows aliases.
    """

    system = processPackage('reparenting_follows_aliases')

    # reparenting_follows_aliases.main: imports MyClass from ._myotherthing and re-export it in it's __all__ variable.
    # reparenting_follows_aliases._mything: defines class MyClass.
    # reparenting_follows_aliases._myotherthing: imports class MyClass from ._mything, but do not export it.

    # Test that we do not get KeyError
    klass = system.allobjects['reparenting_follows_aliases.main.MyClass']
    
    # Test older names still resolves to reparented object
    top = system.allobjects['reparenting_follows_aliases']

    myotherthing = top.contents['_myotherthing']
    mything = top.contents['_mything']

    assert isinstance(mything, model.Module)
    assert isinstance(myotherthing, model.Module)

    assert mything._localNameToFullName('MyClass') == 'reparenting_follows_aliases.main.MyClass'
    assert myotherthing._localNameToFullName('MyClass') == 'reparenting_follows_aliases._mything.MyClass'

    system.find_object('reparenting_follows_aliases._mything.MyClass') == klass

    # This part of the test cannot pass for now since we don't recursively resolve aliases.
    # See https://github.com/twisted/pydoctor/pull/414 and https://github.com/twisted/pydoctor/issues/430

    try:
        assert system.find_object('reparenting_follows_aliases._myotherthing.MyClass') == klass
        assert myotherthing.resolveName('MyClass') == klass
        assert mything.resolveName('MyClass') == klass
        assert top.resolveName('_myotherthing.MyClass') == klass
        assert top.resolveName('_mything.MyClass') == klass
    except (AssertionError, LookupError):
        return
    else:
        raise AssertionError("Congratulation!")

@pytest.mark.parametrize('modname', ['reparenting_crash','reparenting_crash_alt'])
def test_reparenting_crash(modname: str) -> None:
    """
    Test for https://github.com/twisted/pydoctor/issues/513
    """
    system = processPackage(modname)
    mod = system.allobjects[modname]
    assert isinstance(mod.contents[modname], model.Class)
    assert isinstance(mod.contents['reparented_func'], model.Function)
    assert isinstance(mod.contents[modname].contents['reparented_func'], model.Function)
