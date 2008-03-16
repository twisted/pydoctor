from pydoctor import model

class FakeOptions(object):
    """
    A fake options object as if it came from that stupid optparse thing.
    """
    sourcehref = None



class FakeDocumentable(object):
    """
    A fake of pydoctor.model.Documentable that provides a system and
    sourceHref attribute.
    """
    system = None
    sourceHref = None



def test_setSourceHrefOption():
    """
    Test that the projectbasedirectory option sets the model.sourceHref
    properly.
    """
    viewSourceBase = "http://example.org/trac/browser/trunk"
    projectBaseDir = "/foo/bar/ProjectName"
    moduleRelativePart = "/package/module.py"

    mod = FakeDocumentable()
    mod.filepath = projectBaseDir + moduleRelativePart

    options = FakeOptions()
    options.projectbasedirectory = projectBaseDir

    system = model.System()
    system.sourcebase = viewSourceBase
    system.options = options
    mod.system = system
    system.setSourceHref(mod)

    expected = viewSourceBase + moduleRelativePart
    assert mod.sourceHref == expected
