from io import BytesIO
from typing import Callable
import pytest
import warnings
from pathlib import Path
from pydoctor import model, templatewriter
from pydoctor.templatewriter import pages, writer, TemplateLookup, Template, _SimpleTemplate, _HtmlTemplate
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.templatewriter.summary import isClassNodePrivate, isPrivate
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage


def flatten(t: ChildTable) -> str:
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
    t = ChildTable(pages.DocGetter(), mod, [], TemplateLookup())
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table() -> None:
    mod = fromText('def f(): pass')
    t = ChildTable(pages.DocGetter(), mod, mod.contents.values(), TemplateLookup())
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
    w._writeDocsFor(root)
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

def test_template_lookup() -> None:
    
    lookup = TemplateLookup()

    here = Path(__file__).parent

    assert str(lookup.get_template('index.html').path) == str(here.parent / 'templates' / 'index.html' )

    lookup.add_templatedir((here / 'testcustomtemplates' / 'faketemplate'))

    assert str(lookup.get_template('footer.html').path) == str(here / 'testcustomtemplates' / 'faketemplate' / 'footer.html' )
    
    assert str(lookup.get_template('header.html').path) == str(here / 'testcustomtemplates' / 'faketemplate' / 'header.html' )

    assert str(lookup.get_template('pageHeader.html').path) == str(here / 'testcustomtemplates' / 'faketemplate' / 'pageHeader.html' )

    assert str(lookup.get_template('index.html').path) == str(here.parent / 'templates' / 'index.html' )

    lookup = TemplateLookup()

    assert str(lookup.get_template('footer.html').path) == str(here.parent / 'templates' / 'footer.html' )
    
    assert str(lookup.get_template('header.html').path) == str(here.parent / 'templates' / 'header.html' )

    assert str(lookup.get_template('pageHeader.html').path) == str(here.parent / 'templates' / 'pageHeader.html' )

    assert str(lookup.get_template('index.html').path) == str(here.parent / 'templates' / 'index.html' )

    assert lookup.get_template('footer.html').version == -1

    assert type(lookup.get_template('index.html').version) == int

    assert lookup.get_template('table.html').version == 1
    
    lookup = TemplateLookup()

    with warnings.catch_warnings(record=True) as catch_warnings:
        warnings.simplefilter("always", )
        
        lookup.add_template(_HtmlTemplate(here / 'testcustomtemplates' / 'faketemplate' / 'nav.html'))
        assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
        assert "Your custom template 'nav.html' is out of date" in str(catch_warnings.pop().message) 

        lookup.add_template(_HtmlTemplate(here / 'testcustomtemplates' / 'faketemplate' / 'table.html'))
        assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
        assert "Could not read 'table.html' template version: can't cast template version to int" in str(catch_warnings.pop().message) 

        lookup.add_template(_HtmlTemplate(here / 'testcustomtemplates' / 'faketemplate' / 'summary.html'))
        assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
        assert "Could not read 'summary.html' template version: can't get meta pydoctor-template-version tag content" in str(catch_warnings.pop().message) 

        lookup.add_template(_HtmlTemplate(here / 'testcustomtemplates' / 'faketemplate' / 'random.html'))
        assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
        assert "Invalid template filename 'random.html'" in str(catch_warnings.pop().message) 

        lookup.add_templatedir((here / 'testcustomtemplates' / 'faketemplate'))
        assert len(catch_warnings) == 4, [str(w.message) for w in catch_warnings]

    lookup = TemplateLookup()

    with warnings.catch_warnings(record=True) as catch_warnings:
        warnings.simplefilter("always", )
        
        lookup.add_templatedir((here / 'testcustomtemplates' / 'allok'))
        assert len(catch_warnings) == 0, [str(w.message) for w in catch_warnings]

    lookup = TemplateLookup()

    try:
        lookup.add_templatedir((here / 'testcustomtemplates' / 'invalid'))

    except RuntimeError as e:
        assert "It appears that your custom template 'nav.html' is designed for a newer version of pydoctor" in str(e)
    else:
        assert False, "Should have failed with a RuntimeError when loading 'testcustomtemplates/invalid'"

def test_template() -> None:

    here = Path(__file__).parent

    js_template = Template.fromfile((here / 'testcustomtemplates' / 'faketemplate' / 'pydoctor.js'))
    html_template = Template.fromfile((here / 'testcustomtemplates' / 'faketemplate' / 'nav.html'))

    assert isinstance(js_template, _SimpleTemplate)
    assert isinstance(html_template, _HtmlTemplate)


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
