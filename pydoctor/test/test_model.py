"""
Unit tests for model.
"""
from pydoctor import model
from pydoctor.driver import parse_args
import zlib


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


def test_initialization_default():
    """
    When initialized without options, will use default options and default
    verbosity.
    """
    sut = model.System()

    assert None is sut.options.projectname
    assert 3 == sut.options.verbosity


def test_initialization_options():
    """
    Can be initialized with options.
    """
    options = object()

    sut = model.System(options=options)

    assert options is sut.options


def test_fetchIntersphinxInventories_empty():
    """
    Convert option to empty dict.
    """
    options, _ = parse_args([])
    options.intersphinx = []
    sut = model.System(options=options)

    sut.fetchIntersphinxInventories()

    # Use internal state since I don't know how else to
    # check for SphinxInventory state.
    assert {} == sut.intersphinx._links


def test_fetchIntersphinxInventories_content():
    """
    Download and parse intersphinx inventories for each configured
    intersphix.
    """
    options, _ = parse_args([])
    options.intersphinx = [
        'http://sphinx/objects.inv',
        'file:///twisted/index.inv',
        ]
    url_content = {
        'http://sphinx/objects.inv': zlib.compress(
            'sphinx.module py:module -1 sp.html -'),
        'file:///twisted/index.inv': zlib.compress(
            'twisted.package py:module -1 tm.html -'),
        }
    sut = model.System(options=options)
    log = []
    sut.msg = lambda part, msg: log.append((part, msg))
    # Patch url getter to avoid touching the network.
    sut.intersphinx._getURL = lambda url: url_content[url]

    sut.fetchIntersphinxInventories()

    assert [] == log
    assert (
        'http://sphinx/sp.html' ==
        sut.intersphinx.getLink('sphinx.module')
        )
    assert (
        'file:///twisted/tm.html' ==
        sut.intersphinx.getLink('twisted.package')
        )
