"""
Unit tests for model.
"""

from optparse import Values
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast
import zlib

import pytest

from pydoctor import model
from pydoctor.driver import parse_args
from pydoctor.sphinx import CacheT
from pydoctor.test.test_astbuilder import fromText


class FakeOptions:
    """
    A fake options object as if it came from that stupid optparse thing.
    """
    sourcehref = None
    projectbasedirectory: Path
    docformat = 'epytext'


class FakeDocumentable:
    """
    A fake of pydoctor.model.Documentable that provides a system and
    sourceHref attribute.
    """
    system: model.System
    sourceHref = None
    filepath: str



@pytest.mark.parametrize('projectBaseDir', [
    PurePosixPath("/foo/bar/ProjectName"),
    PureWindowsPath("C:\\foo\\bar\\ProjectName")]
)
def test_setSourceHrefOption(projectBaseDir: Path) -> None:
    """
    Test that the projectbasedirectory option sets the model.sourceHref
    properly.
    """

    mod = cast(model.Module, FakeDocumentable())

    options = FakeOptions()
    options.projectbasedirectory = projectBaseDir

    system = model.System()
    system.sourcebase = "http://example.org/trac/browser/trunk"
    system.options = cast(Values, options)
    mod.system = system
    system.setSourceHref(mod, projectBaseDir / "package" / "module.py")

    assert mod.sourceHref == "http://example.org/trac/browser/trunk/package/module.py"


def test_package_sourceHref() -> None:
    """
    A package reports its __init__.py location as its source link.
    """

    project_dir = Path("/foo/bar/ProjectName")

    options = FakeOptions()
    options.projectbasedirectory = project_dir

    system = model.System()
    system.ensurePackage('pkg')
    system.sourcebase = "https://git.example.org/proj/main"
    system.options = cast(Values, options)

    mod_init = fromText('''
    """Docstring."""
    ''', modname='__init__', parent_name='pkg', system=system)
    system.setSourceHref(mod_init, project_dir / 'src' / 'pkg' / '__init__.py')

    package = system.objForFullName('pkg')
    assert isinstance(package, model.Package)
    assert package.sourceHref == "https://git.example.org/proj/main/src/pkg/__init__.py"


def test_initialization_default() -> None:
    """
    When initialized without options, will use default options and default
    verbosity.
    """
    sut = model.System()

    assert None is sut.options.projectname
    assert 3 == sut.options.verbosity


def test_initialization_options() -> None:
    """
    Can be initialized with options.
    """
    options = cast(Values, object())

    sut = model.System(options=options)

    assert options is sut.options


def test_fetchIntersphinxInventories_empty() -> None:
    """
    Convert option to empty dict.
    """
    options, _ = parse_args([])
    options.intersphinx = []
    sut = model.System(options=options)

    sut.fetchIntersphinxInventories({})

    # Use internal state since I don't know how else to
    # check for SphinxInventory state.
    assert {} == sut.intersphinx._links


def test_fetchIntersphinxInventories_content() -> None:
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
            b'sphinx.module py:module -1 sp.html -'),
        'file:///twisted/index.inv': zlib.compress(
            b'twisted.package py:module -1 tm.html -'),
        }
    sut = model.System(options=options)
    log = []
    def log_msg(part: str, msg: str) -> None:
        log.append((part, msg))
    sut.msg = log_msg # type: ignore[assignment]

    class Cache(CacheT):
        """Avoid touching the network."""
        def get(self, url: str) -> bytes:
            return url_content[url]

    sut.fetchIntersphinxInventories(Cache())

    assert [] == log
    assert (
        'http://sphinx/sp.html' ==
        sut.intersphinx.getLink('sphinx.module')
        )
    assert (
        'file:///twisted/tm.html' ==
        sut.intersphinx.getLink('twisted.package')
        )


def test_docsources_class_attribute() -> None:
    src = '''
    class Base:
        attr = False
        """documentation"""
    class Sub(Base):
        attr = True
    '''
    mod = fromText(src)
    base_attr = mod.contents['Base'].contents['attr']
    sub_attr = mod.contents['Sub'].contents['attr']
    assert base_attr in list(sub_attr.docsources())


def test_constructor_params_empty() -> None:
    src = '''
    class C:
        pass
    '''
    mod = fromText(src)
    assert mod.contents['C'].constructor_params == {}


def test_constructor_params_simple() -> None:
    src = '''
    class C:
        def __init__(self, a: int, b: str):
            pass
    '''
    mod = fromText(src)
    assert mod.contents['C'].constructor_params.keys() == {'self', 'a', 'b'}


def test_constructor_params_inherited() -> None:
    src = '''
    class A:
        def __init__(self, a: int, b: str):
            pass
    class B:
        def __init__(self):
            pass
    class C(A, B):
        pass
    '''
    mod = fromText(src)
    assert mod.contents['C'].constructor_params.keys() == {'self', 'a', 'b'}


def test_docstring_lineno() -> None:
    src = '''
    def f():
        """
        This is a long docstring.

        Somewhat long, anyway.
        This should be enough.
        """
    '''
    mod = fromText(src)
    func = mod.contents['f']
    assert func.linenumber == 2
    assert func.docstring_lineno == 4 # first non-blank line


class Dummy:
    def crash(self) -> None:
        """Mmm"""

def test_introspection_python() -> None:
    """Find docstrings from this test using introspection on pure Python."""
    system = model.System()
    system.introspectModule(Path(__file__), __name__)

    module = system.objForFullName(__name__)
    assert module is not None
    assert module.docstring == __doc__

    func = module.contents['test_introspection_python']
    assert func.docstring == "Find docstrings from this test using introspection on pure Python."

    method = system.objForFullName(__name__ + '.Dummy.crash')
    assert method is not None
    assert method.docstring == "Mmm"


def test_introspection_extension() -> None:
    """Find docstrings from this test using introspection of an extension."""

    try:
        import cython_test_exception_raiser.raiser
    except ImportError:
        pytest.skip("cython_test_exception_raiser not installed")

    system = model.System()
    system.introspectModule(
        Path(cython_test_exception_raiser.raiser.__file__),
        'cython_test_exception_raiser.raiser')

    module = system.objForFullName('cython_test_exception_raiser.raiser')
    assert module is not None
    assert module.docstring is not None
    assert module.docstring.strip().split('\n')[0] == "A trivial extension that just raises an exception."

    cls = module.contents['RaiserException']
    assert cls.docstring is not None
    assert cls.docstring.strip() == "A speficic exception only used to be identified in tests."

    func = module.contents['raiseException']
    assert func.docstring is not None
    assert func.docstring.strip() == "Raise L{RaiserException}."
