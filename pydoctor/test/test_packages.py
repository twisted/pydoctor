import py
from pydoctor import model, astbuilder

def processPackage(packname, buildercls=astbuilder.ASTBuilder):
    testpackage = py.magic.autopath().dirpath().join(packname)
    system = model.System()
    builder = buildercls(system)
    system.packages.append(testpackage.strpath)
    builder.processDirectory(testpackage.strpath)
    return system

def test_local_import():
    system = processPackage("localimporttest")
    cls = system.allobjects['localimporttest.mod1.C']
    assert len(system.warnings['local import']) > 0
    assert cls.bases == ['localimporttest.mod2.B']

def test_harder_local_imports():
    system = processPackage("localimporttest")
    cls = system.allobjects['localimporttest.sub1.mod.C']
    assert len(system.warnings['local import']) > 0
    assert cls.bases == ['localimporttest.sub2.mod.A',
                         'localimporttest.sub2.mod.B',
                         'localimporttest.mod1.C',
                         'localimporttest.mod2.B']

def test_package_docstring():
    system = processPackage("localimporttest")
    assert (system.allobjects['localimporttest.__init__'].docstring ==
            "DOCSTRING")

def test_modnamedafterbuiltin():
    # well, basically the test is that this doesn't explode:
    system = processPackage("modnamedafterbuiltin")
    # but let's test _something_
    assert system.allobjects['modnamedafterbuiltin.mod.Dict'].baseobjects == [None]

def test_package_docstring():
    system = processPackage("localimporttest")
    assert (system.allobjects['localimporttest.__init__'].docstring ==
            "DOCSTRING")

def test_nestedconfusion():
    system = processPackage("nestedconfusion")
    A = system.allobjects['nestedconfusion.mod.nestedconfusion.A']
    C = system.allobjects['nestedconfusion.mod.C']
    assert A.baseobjects[0] is C
