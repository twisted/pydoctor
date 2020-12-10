from io import BytesIO
from twisted.python.filepath import FilePath
from typing import Callable
import shutil
import pytest
import warnings
from pathlib import Path
from pydoctor import model, templatewriter
from pydoctor.templatewriter import pages, writer
from pydoctor.templatewriter.summary import isClassNodePrivate, isPrivate
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage
from pydoctor.templatewriter.util import TemplateFileLookup


def flatten(t: pages.ChildTable) -> str:
    io = BytesIO()
    writer.flattenToFile(io, t)
    return io.getvalue().decode()


def getHTMLOf(ob: model.Documentable) -> str:
    wr = templatewriter.TemplateWriter('')
    f = BytesIO()
    wr._writeDocsForOne(ob, f)
    return f.getvalue().decode()


def test_simple() -> None:
    src = '''
    def f():
        """This is a docstring."""
    '''
    mod = fromText(src)
    v = getHTMLOf(mod.contents['f'])
    assert 'This is a docstring' in v

def test_empty_table() -> None:
    mod = fromText('')
    t = pages.ChildTable(pages.DocGetter(), mod, [])
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table() -> None:
    mod = fromText('def f(): pass')
    t = pages.ChildTable(pages.DocGetter(), mod, mod.contents.values())
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_rest_support() -> None:
    system = model.System()
    system.options.docformat = 'restructuredtext'
    system.options.verbosity = 4
    src = '''
    def f():
        """This is a docstring for f."""
    '''
    mod = fromText(src, system=system)
    html = getHTMLOf(mod.contents['f'])
    assert "<pre>" not in html

def test_document_code_in_init_module() -> None:
    system = processPackage("codeininit")
    html = getHTMLOf(system.allobjects['codeininit'])
    assert 'functionInInit' in html

def test_basic_package(tmp_path: Path) -> None:
    system = processPackage("basic")
    w = writer.TemplateWriter(str(tmp_path))
    system.options.htmlusesplitlinks = True
    system.options.htmlusesorttable = True
    w.prepOutputDirectory()
    root, = system.rootobjects
    w._writeDocsFor(root, False)
    w.writeModuleIndex(system)
    for ob in system.allobjects.values():
        url = ob.url
        if '#' in url:
            url = url[:url.find('#')]
        assert (tmp_path / url).is_file()
    with open(tmp_path / 'basic.html') as f:
        assert 'Package docstring' in f.read()

def test_hasdocstring() -> None:
    system = processPackage("basic")
    from pydoctor.templatewriter.summary import hasdocstring
    assert not hasdocstring(system.allobjects['basic._private_mod'])
    assert hasdocstring(system.allobjects['basic.mod.C.f'])
    sub_f = system.allobjects['basic.mod.D.f']
    assert hasdocstring(sub_f) and not sub_f.docstring

def test_missing_variable() -> None:
    mod = fromText('''
    """Module docstring.

    @type thisVariableDoesNotExist: Type for non-existent variable.
    """
    ''')
    html = getHTMLOf(mod)
    assert 'thisVariableDoesNotExist' not in html


@pytest.mark.parametrize(
    'className',
    ['NewClassThatMultiplyInherits', 'OldClassThatMultiplyInherits'],
)
def test_multipleInheritanceNewClass(className: str) -> None:
    """
    A class that has multiple bases has all methods in its MRO
    rendered.
    """
    system = processPackage("multipleinheritance")

    cls = next(
        cls
        for cls in system.allobjects.values()
        if cls.name == className
    )

    html = getHTMLOf(cls)

    assert "methodA" in html
    assert "methodB" in html

def test_templatefile_lookup() -> None:
    
    lookup = TemplateFileLookup()

    here:Path = Path(__file__).parent

    assert lookup.get_templatefilepath('index.html').path == str(here.parent / 'templates' / 'index.html' )

    lookup.add_templatedir((here / 'faketemplate'))

    assert lookup.get_templatefilepath('footer.html').path == str(here / 'faketemplate' / 'footer.html' )
    
    assert lookup.get_templatefilepath('header.html').path== str(here / 'faketemplate' / 'header.html' )

    assert lookup.get_templatefilepath('pageHeader.html').path== str(here / 'faketemplate' / 'pageHeader.html' )

    assert lookup.get_templatefilepath('index.html').path== str(here.parent / 'templates' / 'index.html' )

    lookup.clear_templates()

    assert lookup.get_templatefilepath('footer.html').path== str(here.parent / 'templates' / 'footer.html' )
    
    assert lookup.get_templatefilepath('header.html').path== str(here.parent / 'templates' / 'header.html' )

    assert lookup.get_templatefilepath('pageHeader.html').path== str(here.parent / 'templates' / 'pageHeader.html' )

    assert lookup.get_templatefilepath('index.html').path== str(here.parent / 'templates' / 'index.html' )

    assert lookup.get_template_version('footer.html') == None

    assert type(lookup.get_template_version('index.html')) == str

    with warnings.catch_warnings(record=True) as catch_warnings:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always", category=UserWarning)
        # Trigger a warning.
        lookup = TemplateFileLookup()
        lookup.add_templatedir((here / 'faketemplate'))
        wr = templatewriter.TemplateWriter('', templatefile_lookup=lookup)
        wr._checkTemplatesV()
        # Verify some things
        assert len(catch_warnings) == 1
        assert issubclass(catch_warnings[-1].category, UserWarning)
        assert "Your custom template 'nav.html' is out of date" in str(catch_warnings[-1].message)


@pytest.mark.parametrize('func', [isPrivate, isClassNodePrivate])
def test_isPrivate(func: Callable[[model.Class], bool]) -> None:
    """A documentable object is private if it is private itself or
    lives in a private context.
    """
    mod = fromText('''
    class Public:
        class Inner:
            pass
    class _Private:
        class Inner:
            pass
    ''')
    public = mod.contents['Public']
    assert not func(public)
    assert not func(public.contents['Inner'])
    private = mod.contents['_Private']
    assert func(private)
    assert func(private.contents['Inner'])


def test_isClassNodePrivate() -> None:
    """A node for a private class with public subclasses is considered public."""
    mod = fromText('''
    class _BaseForPublic:
        pass
    class _BaseForPrivate:
        pass
    class Public(_BaseForPublic):
        pass
    class _Private(_BaseForPrivate):
        pass
    ''')
    assert not isClassNodePrivate(mod.contents['Public'])
    assert isClassNodePrivate(mod.contents['_Private'])
    assert not isClassNodePrivate(mod.contents['_BaseForPublic'])
    assert isClassNodePrivate(mod.contents['_BaseForPrivate'])
