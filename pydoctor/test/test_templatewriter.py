from io import BytesIO
from typing import Callable
import pytest
import warnings
from pathlib import Path
from pydoctor import model, templatewriter
from pydoctor.templatewriter import pages, writer, TemplateLookup, Template, _StaticTemplate, _HtmlTemplate, UnsupportedTemplateVersion
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.templatewriter.summary import isClassNodePrivate, isPrivate
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage

def filetext(path: Path) -> str:
    with path.open('r', encoding='utf-8') as fobj:
        t = fobj.read()
    return t

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
    t = ChildTable(pages.DocGetter(), mod, [], ChildTable.lookup_loader(TemplateLookup()))
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table() -> None:
    mod = fromText('def f(): pass')
    t = ChildTable(pages.DocGetter(), mod, mod.contents.values(), ChildTable.lookup_loader(TemplateLookup()))
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

def test_html_template_version() -> None:
    lookup = TemplateLookup()
    for template in lookup._templates.values():
        if isinstance(template, _HtmlTemplate) and not template.is_empty():
            assert template.version >= 1

def test_template_lookup_get_template() -> None:
    
    lookup = TemplateLookup()

    here = Path(__file__).parent

    assert lookup.get_template('index.html').text == filetext(here.parent / 'templates' / 'index.html')

    lookup.add_template(_HtmlTemplate(name='footer.html', text=filetext(here / 'testcustomtemplates' / 'faketemplate' / 'footer.html')))

    assert lookup.get_template('footer.html').text == filetext(here / 'testcustomtemplates' / 'faketemplate' / 'footer.html')

    assert lookup.get_template('index.html').text == filetext(here.parent / 'templates' / 'index.html')

    lookup = TemplateLookup()

    assert lookup.get_template('footer.html').text == filetext(here.parent / 'templates' / 'footer.html')

    assert lookup.get_template('footer.html').version == -1

    assert lookup.get_template('table.html').version == 1

def test_template_lookup_add_template_warns() -> None:

    lookup = TemplateLookup()

    here = Path(__file__).parent

    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'nav.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(_HtmlTemplate(text=fobj.read(), name='nav.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Your custom template 'nav.html' is out of date" in str(catch_warnings.pop().message) 
    
    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'table.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(_HtmlTemplate(text=fobj.read(), name='table.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Could not read 'table.html' template version" in str(catch_warnings.pop().message) 

    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'summary.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(_HtmlTemplate(text=fobj.read(), name='summary.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Could not read 'summary.html' template version" in str(catch_warnings.pop().message) 

    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'random.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(_HtmlTemplate(text=fobj.read(), name='random.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Invalid template filename 'random.html'" in str(catch_warnings.pop().message) 

    with pytest.warns(UserWarning) as catch_warnings:
        lookup.add_templatedir(here / 'testcustomtemplates' / 'faketemplate')
    assert len(catch_warnings) == 4, [str(w.message) for w in catch_warnings]

def test_template_lookup_add_template_allok() -> None:
    
    here = Path(__file__).parent

    with warnings.catch_warnings(record=True) as catch_warnings:
        warnings.simplefilter("always", )
        lookup = TemplateLookup()
        lookup.add_templatedir(here / 'testcustomtemplates' / 'allok')
    assert len(catch_warnings) == 0, [str(w.message) for w in catch_warnings]

def test_template_lookup_add_template_raises() -> None:

    lookup = TemplateLookup()

    with pytest.raises(UnsupportedTemplateVersion):
        lookup.add_template(_HtmlTemplate(name="nav.html", text="""
        <nav class="navbar navbar-default" xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
            <meta name="pydoctor-template-version" content="2050" />
            <div class="container"> </div>
        </nav>
        """))

    with pytest.raises(ValueError):
        lookup.add_template(_HtmlTemplate(name="nav.html", text="""
        <nav class="navbar navbar-default" xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
            <meta name="pydoctor-template-version" content="1" />
            <div class="container"> </div>
        </nav>
        <span> Words </span>
        """))

def test_template() -> None:

    here = Path(__file__).parent

    js_template = Template.fromfile(here / 'testcustomtemplates' / 'faketemplate' / 'pydoctor.js')
    html_template = Template.fromfile(here / 'testcustomtemplates' / 'faketemplate' / 'nav.html')

    assert isinstance(js_template, _StaticTemplate)
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
