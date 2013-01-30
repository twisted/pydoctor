import os

from pydoctor import model
from pydoctor.test import test_astbuilder

testpackages = os.path.join(os.path.dirname(__file__), 'testpackages')

def processPackage(packname, systemcls=model.System):
    testpackage = os.path.join(testpackages, packname)
    system = systemcls()
    system.packages.append(testpackage)
    system.addPackage(testpackage)
    system.process()
    return system

def test_local_import():
    system = processPackage("localimporttest")
    cls = system.allobjects['localimporttest.mod1.C']
    assert len(system.warnings['local import']) > 0
    assert cls.bases == ['localimporttest.mod2.B']

def test_package_docstring():
    system = processPackage("localimporttest")
    assert (system.allobjects['localimporttest.__init__'].docstring ==
            "DOCSTRING")

def test_modnamedafterbuiltin():
    # well, basically the test is that this doesn't explode:
    system = processPackage("modnamedafterbuiltin")
    # but let's test _something_
    assert system.allobjects['modnamedafterbuiltin.mod.Dict'].baseobjects == [None], \
      system.allobjects['modnamedafterbuiltin.mod.Dict'].baseobjects

def test_nestedconfusion():
    system = processPackage("nestedconfusion")
    A = system.allobjects['nestedconfusion.mod.nestedconfusion.A']
    C = system.allobjects['nestedconfusion.mod.C']
    assert A.baseobjects[0] is C

def test_moresystems():
    system = processPackage("basic")
    system2 = model.System()
    system2.moresystems.append(system)
    mod = test_astbuilder.fromText("""
    from basic import mod
    class E(mod.C):
        pass
    """, system=system2)
    E = mod.contents["E"]
    assert E.baseobjects[0] is not None

def dont_test_importingfrompackage():
    packname = 'importingfrompackage'
    testpackage = os.path.join(testpackages, '..', packname)
    system = model.System()
    system.packages.append(testpackage)
    system.addPackage(testpackage)
    system.getProcessedModule('importingfrompackage.mod')
    submod = system.allobjects['importingfrompackage.subpack.submod']
    assert submod.state == model.PROCESSED

def test_allgames():
    system = processPackage("allgames")
    # InSourceAll is not moved into mod2, but NotInSourceAll is.
    assert 'InSourceAll' in system.allobjects['allgames.mod1'].contents
    assert 'NotInSourceAll' in system.allobjects['allgames.mod2'].contents
