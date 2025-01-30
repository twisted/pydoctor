from __future__ import annotations
from pathlib import Path
from typing import Callable, Sequence
from pydoctor.test import CapSys
import pytest

from pydoctor import model

testpackages = Path(__file__).parent / 'testpackages'

def processPackage(pack: str | Sequence[str], systemcls: Callable[[], model.System] = model.System) -> model.System:
    system = systemcls()
    builderT = system.systemBuilder
    if system.options.prependedpackage:
        builderT = model.prepend_package(builderT, package=system.options.prependedpackage)
    builder = builderT(system)
    if isinstance(pack, str):
        builder.addModule(testpackages / pack)
    else:
        for p in pack:
            builder.addModule(testpackages / p)
    builder.buildModules()
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

def test_just_py_modules(capsys: CapSys) -> None:
    system = processPackage(['basic/mod.py', 'relativeimporttest/mod2.py'])
    assert list(system.allobjects) == ['mod', 'mod2', 'mod.CONSTANT', 'mod.C', 
                                       'mod.C.notreally', 'mod.C.S', 'mod.C.f', 
                                       'mod.C.h', 'mod.C.cls_method', 
                                       'mod.C.static_method', 'mod.D', 
                                       'mod.D.T', 'mod.D.f', 'mod.D.g', 
                                       'mod.D.cls_method2', 'mod.D.static_method2', 
                                       'mod._private', 
                                       
                                       'mod2.B']

def test_namespace_packages() -> None:
    systemcls = lambda: model.System(model.Options.from_args(
        ['--html-viewsource-base=https://github.com/some/repo/tree/master',
         f'--project-base-dir={testpackages / "namespaces"}']))

    system = processPackage(['namespaces/project1/lvl1', 
                             'namespaces/project2/lvl1'], systemcls)
    
    assert list(system.allobjects) == ['lvl1', 'lvl1.lvl2', 'lvl1.lvl2.sub1', 'lvl1.lvl2.sub2', 
                                       'lvl1.lvl2.sub1.f1', 'lvl1.lvl2.sub2.f2']
    
    assert isinstance(root:=system.allobjects['lvl1'], model.Package)
    assert root.kind is model.DocumentableKind.NAMESPACE_PACKAGE

    assert isinstance(nested:=root.contents['lvl2'], model.Package)
    assert nested.kind is model.DocumentableKind.NAMESPACE_PACKAGE

    assert len(root.source_paths) == 2
    assert len(nested.source_paths) == 2

    assert system.allobjects['lvl1.lvl2.sub1'].kind == model.DocumentableKind.PACKAGE
    assert system.allobjects['lvl1.lvl2.sub2'].kind == model.DocumentableKind.PACKAGE

    assert root.source_hrefs == ['https://github.com/some/repo/tree/master/project1/lvl1', 
                                   'https://github.com/some/repo/tree/master/project2/lvl1']
    assert nested.source_hrefs == ['https://github.com/some/repo/tree/master/project1/lvl1/lvl2', 
                                   'https://github.com/some/repo/tree/master/project2/lvl1/lvl2']

def test_namespace_packages_oldschool() -> None:
    systemcls = lambda: model.System(model.Options.from_args(
        ['--html-viewsource-base=https://github.com/some/repo/tree/master',
         f'--project-base-dir={testpackages / "namespaces"}']))

    system = processPackage(['namespaces/project1-oldschool/lvl1', 
                             'namespaces/project2-oldschool/lvl1'], systemcls)
    
    assert list(system.allobjects) == ['lvl1', 'lvl1.lvl2', 'lvl1.lvl2.sub1', 'lvl1.lvl2.sub2', 
                                       'lvl1.lvl2.sub1.f1', 'lvl1.lvl2.sub2.f2']
    
    assert isinstance(root:=system.allobjects['lvl1'], model.Package)
    assert root.kind is model.DocumentableKind.NAMESPACE_PACKAGE

    assert isinstance(nested:=root.contents['lvl2'], model.Package)
    assert nested.kind is model.DocumentableKind.NAMESPACE_PACKAGE

    assert len(root.source_paths) == 2
    assert len(nested.source_paths) == 2

    assert system.allobjects['lvl1.lvl2.sub1'].kind == model.DocumentableKind.PACKAGE
    assert system.allobjects['lvl1.lvl2.sub2'].kind == model.DocumentableKind.PACKAGE

    assert root.source_hrefs == ['https://github.com/some/repo/tree/master/project1-oldschool/lvl1', 
                                   'https://github.com/some/repo/tree/master/project2-oldschool/lvl1']
    assert nested.source_hrefs == ['https://github.com/some/repo/tree/master/project1-oldschool/lvl1/lvl2', 
                                   'https://github.com/some/repo/tree/master/project2-oldschool/lvl1/lvl2']

def test_namespace_packages_nested_under_regular_pack_ignored() -> None:
    system = processPackage(['namespaces/project_regular_pack_contains_ns'],)
    
    assert isinstance(root:=system.allobjects['project_regular_pack_contains_ns'], model.Package)
    assert root.kind is model.DocumentableKind.PACKAGE

    assert isinstance(nested:=root.contents['subpack'], model.Package)
    assert nested.kind is model.DocumentableKind.PACKAGE

    assert list(nested.contents) == []

def test_empty_namespace_package() -> None:
    system = processPackage(['namespaces/project_empty'],)
    assert list(system.allobjects) == ['project_empty']
    assert system.rootobjects[0].kind is model.DocumentableKind.NAMESPACE_PACKAGE

def test_collision_regular_package_with_nspack(capsys: CapSys) -> None:
    
    assert (system:=processPackage(['namespaces/basic', 'basic'])).allobjects['basic'].kind is model.DocumentableKind.NAMESPACE_PACKAGE
    assert "discarding duplicate Package 'basic' because existing namespace package has the same name" in capsys.readouterr().out
    assert list(map(repr, filter(lambda o: isinstance(o, model.Module), system.allobjects.values()))) == ["Namespace Package 'basic'", 
                                                                                                          "Package 'basic.subpack'", 
                                                                                                          "Module 'basic.subpack.mod'",]

    assert (system:=processPackage(['basic', 'namespaces/basic'])).allobjects['basic'].kind is model.DocumentableKind.NAMESPACE_PACKAGE
    assert "discarding existing Package 'basic' because Namespace Package 'basic' overrides it" in capsys.readouterr().out
    assert list(map(repr, filter(lambda o: isinstance(o, model.Module), system.allobjects.values()))) == ["Namespace Package 'basic'", 
                                                                                                          "Package 'basic.subpack'", 
                                                                                                          "Module 'basic.subpack.mod'",]

def test_prepend_package_works_with_namespace_packages() -> None:
    systemcls = lambda: model.System(model.Options.from_args(
        ['--prepend-package=some.package']))

    system = processPackage(['namespaces/project1/lvl1', 
                             'namespaces/project2/lvl1'], systemcls)
    
    assert list(system.allobjects) == ['some', 'some.package', 'some.package.lvl1', 'some.package.lvl1.lvl2', 
                                        'some.package.lvl1.lvl2.sub1', 'some.package.lvl1.lvl2.sub2', 
                                        'some.package.lvl1.lvl2.sub1.f1', 'some.package.lvl1.lvl2.sub2.f2']