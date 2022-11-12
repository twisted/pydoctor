"""
Unit tests for model.
"""

import subprocess
import os
from inspect import signature
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast, Optional
import zlib
import pytest

from twisted.web.template import Tag

from pydoctor.options import Options
from pydoctor import model, stanutils
from pydoctor.templatewriter import pages
from pydoctor.utils import parse_privacy_tuple
from pydoctor.sphinx import CacheT
from pydoctor.test import CapSys
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage


class FakeOptions:
    """
    A fake options object as if it came from argparse.
    """
    sourcehref = None
    htmlsourcebase: Optional[str] = None
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
    options.htmlsourcebase = "http://example.org/trac/browser/trunk"
    system = model.System(options) # type:ignore[arg-type]
    mod.system = system
    system.setSourceHref(mod, projectBaseDir / "package" / "module.py")

    assert mod.sourceHref == "http://example.org/trac/browser/trunk/package/module.py"

def test_htmlsourcetemplate_auto_detect() -> None:
    """
    Tests for the recognition of different version control providers
    that uses differents URL templates to point to line numbers.

    Supported templates are::

        Github : {}#L{lineno}
        Bitbucket: {}#lines-{lineno}
        SourceForge : {}#l{lineno}
    """
    cases = [
        ("http://example.org/trac/browser/trunk", 
         "http://example.org/trac/browser/trunk/pydoctor/test/testpackages/basic/mod.py#L7"),

        ("https://sourceforge.net/p/epydoc/code/HEAD/tree/trunk/epydoc", 
         "https://sourceforge.net/p/epydoc/code/HEAD/tree/trunk/epydoc/pydoctor/test/testpackages/basic/mod.py#l7"),
        
        ("https://bitbucket.org/user/scripts/src/master", 
         "https://bitbucket.org/user/scripts/src/master/pydoctor/test/testpackages/basic/mod.py#lines-7"),
    ]
    for base, var_href in cases:
        options = model.Options.from_args([f'--html-viewsource-base={base}', '--project-base-dir=.'])
        system = model.System(options)

        processPackage('basic', systemcls=lambda:system)
        assert system.allobjects['basic.mod.C'].sourceHref == var_href

def test_htmlsourcetemplate_custom() -> None:
    """
    The links to source code web pages can be customized via an CLI argument.
    """
    options = model.Options.from_args([
        '--html-viewsource-base=http://example.org/trac/browser/trunk', 
        '--project-base-dir=.', 
        '--html-viewsource-template={mod_source_href}#n{lineno}'])
    system = model.System(options)

    processPackage('basic', systemcls=lambda:system)
    assert system.allobjects['basic.mod.C'].sourceHref == "http://example.org/trac/browser/trunk/pydoctor/test/testpackages/basic/mod.py#n7"

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
    options = Options.defaults()

    sut = model.System(options=options)

    assert options is sut.options


def test_fetchIntersphinxInventories_empty() -> None:
    """
    Convert option to empty dict.
    """
    options = Options.defaults()
    options.intersphinx = []
    sut = model.System(options=options)

    sut.fetchIntersphinxInventories(cast('CacheT', {}))

    # Use internal state since I don't know how else to
    # check for SphinxInventory state.
    assert {} == sut.intersphinx._links


def test_fetchIntersphinxInventories_content() -> None:
    """
    Download and parse intersphinx inventories for each configured
    intersphix.
    """
    options = Options.defaults()
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
        def close(self) -> None:
            return None
        

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
    C = mod.contents['C']
    assert isinstance(C, model.Class)
    assert C.constructor_params == {}


def test_constructor_params_simple() -> None:
    src = '''
    class C:
        def __init__(self, a: int, b: str):
            pass
    '''
    mod = fromText(src)
    C = mod.contents['C']
    assert isinstance(C, model.Class)
    assert C.constructor_params.keys() == {'self', 'a', 'b'}


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
    C = mod.contents['C']
    assert isinstance(C, model.Class)
    assert C.constructor_params.keys() == {'self', 'a', 'b'}


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


def dummy_function_with_complex_signature(foo: int, bar: float) -> str:
    return "foo"


def test_introspection_python() -> None:
    """Find docstrings from this test using introspection on pure Python."""
    system = model.System()
    system.introspectModule(Path(__file__), __name__, None)
    system.process()

    module = system.objForFullName(__name__)
    assert module is not None
    assert module.docstring == __doc__

    func = module.contents['test_introspection_python']
    assert isinstance(func, model.Function)
    assert func.docstring == "Find docstrings from this test using introspection on pure Python."
    assert func.signature == signature(test_introspection_python)

    method = system.objForFullName(__name__ + '.Dummy.crash')
    assert method is not None
    assert method.docstring == "Mmm"

    func = module.contents['dummy_function_with_complex_signature']
    assert isinstance(func, model.Function)
    assert func.signature == signature(dummy_function_with_complex_signature)

def test_introspection_extension() -> None:
    """Find docstrings from this test using introspection of an extension."""

    try:
        import cython_test_exception_raiser.raiser
    except ImportError:
        pytest.skip("cython_test_exception_raiser not installed")

    system = model.System()
    package = system.introspectModule(
        Path(cython_test_exception_raiser.__file__),
        'cython_test_exception_raiser',
        None)
    assert isinstance(package, model.Package)
    module = system.introspectModule(
        Path(cython_test_exception_raiser.raiser.__file__),
        'raiser',
        package)
    system.process()

    assert not isinstance(module, model.Package)

    assert system.objForFullName('cython_test_exception_raiser') is package
    assert system.objForFullName('cython_test_exception_raiser.raiser') is module

    assert module.docstring is not None
    assert module.docstring.strip().split('\n')[0] == "A trivial extension that just raises an exception."

    cls = module.contents['RaiserException']
    assert cls.docstring is not None
    assert cls.docstring.strip() == "A speficic exception only used to be identified in tests."

    func = module.contents['raiseException']
    assert func.docstring is not None
    assert func.docstring.strip() == "Raise L{RaiserException}."

testpackages = Path(__file__).parent / 'testpackages'

@pytest.mark.skipif("platform.python_implementation() == 'PyPy'")
def test_c_module_text_signature(capsys:CapSys) -> None:
    
    c_module_invalid_text_signature = testpackages / 'c_module_invalid_text_signature'
    package_path = c_module_invalid_text_signature / 'mymod'
    
    # build extension
    try:
        cwd = os.getcwd()
        code, outstr = subprocess.getstatusoutput(f'cd {c_module_invalid_text_signature} && python3 setup.py build_ext --inplace')
        os.chdir(cwd)
        
        assert code==0, outstr

        system = model.System()
        system.options.introspect_c_modules = True

        builder = system.systemBuilder(system)
        builder.addModule(package_path)
        builder.buildModules()
        
        assert "Cannot parse signature of mymod.base.invalid_text_signature" in capsys.readouterr().out
        
        mymod_base = system.allobjects['mymod.base']
        assert isinstance(mymod_base, model.Module)
        func = mymod_base.contents['invalid_text_signature']
        assert isinstance(func, model.Function)
        assert func.signature == None
        valid_func = mymod_base.contents['valid_text_signature']
        assert isinstance(valid_func, model.Function)

        assert "(...)" == pages.format_signature(func)
        assert "(a='r', b=-3.14)" == stanutils.flatten_text(
            cast(Tag, pages.format_signature(valid_func)))

    finally:
        # cleanup
        subprocess.getoutput(f'rm -f {package_path}/*.so')

@pytest.mark.skipif("platform.python_implementation() == 'PyPy'")
def test_c_module_python_module_name_clash(capsys:CapSys) -> None:
    c_module_python_module_name_clash = testpackages / 'c_module_python_module_name_clash'
    package_path = c_module_python_module_name_clash / 'mymod'
    
    # build extension
    try:
        cwd = os.getcwd()
        code, outstr = subprocess.getstatusoutput(f'cd {c_module_python_module_name_clash} && python3 setup.py build_ext --inplace')
        os.chdir(cwd)
        
        assert code==0, outstr
        system = model.System()
        system.options.introspect_c_modules = True

        system.addPackage(package_path, None)
        system.process()

        mod = system.allobjects['mymod.base']
        # there is only one mymod.base module
        assert [mod] == list(system.allobjects['mymod'].contents.values())
        assert len(mod.contents) == 1
        assert 'coming_from_c_module' == mod.contents.popitem()[0]

    finally:
        # cleanup
        subprocess.getoutput(f'rm -f {package_path}/*.so')

def test_resolve_name_subclass(capsys:CapSys) -> None:
    """
    C{Model.resolveName} knows about single inheritance.
    """
    m = fromText(
        """
        class B:
            v=1
        class C(B):
            pass
        """
    )
    assert m.resolveName('C.v') == m.contents['B'].contents['v']

@pytest.mark.parametrize('privacy', [
    (['public:m._public**', 'public:m.tests', 'public:m.tests.helpers', 'private:m._public.private', 'hidden:m._public.hidden', 'hidden:m.tests.*']), 
    (reversed(['private:**private', 'hidden:**hidden', 'public:**_public', 'hidden:m.tests.test**', ])), 
])
def test_privacy_switch(privacy:object) -> None:
    s = model.System()
    s.options.privacy = [parse_privacy_tuple(p, '--privacy') for p in privacy] # type:ignore

    fromText(
        """
        class _public:
            class _still_public:
                ...
            class private:
                ...
            class hidden:
                ...

        class tests(B): # public
            class helpers: # public
                ...
            class test1: # everything else hidden
                ...
            class test2:
                ...
            class test3:
                ...
        """, system=s, modname='m'
    )
    allobjs = s.allobjects

    assert allobjs['m._public'].privacyClass == model.PrivacyClass.PUBLIC
    assert allobjs['m._public._still_public'].privacyClass == model.PrivacyClass.PUBLIC
    assert allobjs['m._public.private'].privacyClass == model.PrivacyClass.PRIVATE
    assert allobjs['m._public.hidden'].privacyClass == model.PrivacyClass.HIDDEN

    assert allobjs['m.tests'].privacyClass == model.PrivacyClass.PUBLIC
    assert allobjs['m.tests.helpers'].privacyClass == model.PrivacyClass.PUBLIC
    assert allobjs['m.tests.test1'].privacyClass == model.PrivacyClass.HIDDEN
    assert allobjs['m.tests.test2'].privacyClass == model.PrivacyClass.HIDDEN
    assert allobjs['m.tests.test3'].privacyClass == model.PrivacyClass.HIDDEN

def test_privacy_reparented() -> None:
    """
    Test that the privacy of an object changes if 
    the name of the object changes (with reparenting).
    """

    system = model.System()

    mod_private = fromText('''
    class _MyClass:
        pass
    ''', modname='private', system=system)

    mod_export = fromText(
        'from private import _MyClass # not needed for the test to pass', 
        modname='public', system=system)

    base = mod_private.contents['_MyClass']
    assert base.privacyClass == model.PrivacyClass.PRIVATE

    # Manually reparent MyClass
    base.reparent(mod_export, 'MyClass')
    assert base.fullName() == 'public.MyClass'
    assert '_MyClass' not in mod_private.contents
    assert mod_export.resolveName("MyClass") == base

    assert base.privacyClass == model.PrivacyClass.PUBLIC
