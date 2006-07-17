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
