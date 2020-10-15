from typing import Type
import os

from pydoctor import model

testpackages = os.path.join(os.path.dirname(__file__), 'testpackages')

def processPackage(packname: str, systemcls: Type[model.System] = model.System) -> model.System:
    testpackage = os.path.join(testpackages, packname)
    system = systemcls()
    system.packages.append(testpackage)
    system.addPackage(testpackage)
    system.process()
    return system

def test_relative_import() -> None:
    system = processPackage("relativeimporttest")
    cls = system.allobjects['relativeimporttest.mod1.C']
    assert cls.bases == ['relativeimporttest.mod2.B']

def test_package_docstring() -> None:
    system = processPackage("relativeimporttest")
    assert (system.allobjects['relativeimporttest.__init__'].docstring ==
            "DOCSTRING")

def test_modnamedafterbuiltin() -> None:
    # well, basically the test is that this doesn't explode:
    system = processPackage("modnamedafterbuiltin")
    # but let's test _something_
    assert system.allobjects['modnamedafterbuiltin.mod.Dict'].baseobjects == [None], \
      system.allobjects['modnamedafterbuiltin.mod.Dict'].baseobjects

def test_nestedconfusion() -> None:
    system = processPackage("nestedconfusion")
    A = system.allobjects['nestedconfusion.mod.nestedconfusion.A']
    C = system.allobjects['nestedconfusion.mod.C']
    assert A.baseobjects[0] is C

def test_importingfrompackage() -> None:
    system = processPackage("importingfrompackage")
    system.getProcessedModule('importingfrompackage.mod')
    submod = system.allobjects['importingfrompackage.subpack.submod']
    assert submod.state is model.ProcessingState.PROCESSED

def test_allgames() -> None:
    system = processPackage("allgames")
    # InSourceAll is not moved into mod2, but NotInSourceAll is.
    assert 'InSourceAll' in system.allobjects['allgames.mod1'].contents
    assert 'NotInSourceAll' in system.allobjects['allgames.mod2'].contents
    moved = system.allobjects['allgames.mod2'].contents['NotInSourceAll']
    assert moved.source_path.endswith('/allgames/mod1.py')
    assert moved.parentMod.source_path.endswith('/allgames/mod2.py')
