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
    Test that the --html-source-href option sets the model.sourceHref
    properly.
    """
    mod = FakeDocumentable()

    options = FakeOptions()
    options.sourcehref = "http://example.org/trac/browser/trunk"

    system = model.System()
    system.options = options
    mod.system = system
    system.setSourceHref(mod)

    assert mod.sourceHref == "http://example.org/trac/browser/trunk"
