from io import BytesIO
from typing import Callable, Union, cast, TYPE_CHECKING
import pytest
import warnings
import sys
import tempfile
import os
from pathlib import Path, PurePath
from pydoctor import model, templatewriter, stanutils
from pydoctor.templatewriter import (FailedToCreateTemplate, StaticTemplate, pages, writer, 
                                     TemplateLookup, Template, 
                                     HtmlTemplate, UnsupportedTemplateVersion, 
                                     OverrideTemplateNotAllowed)
from pydoctor.templatewriter.pages.table import ChildTable
from pydoctor.templatewriter.summary import isClassNodePrivate, isPrivate
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage

if TYPE_CHECKING:
    from twisted.web.template import Flattenable

# Newer APIs from importlib_resources should arrive to stdlib importlib.resources in Python 3.9.
if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from importlib.abc import Traversable
    else:
        Traversable = Path
else:
    Traversable = object

if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from importlib.abc import Traversable
    else:
        Traversable = Path
else:
    Traversable = object

template_dir = importlib_resources.files("pydoctor.themes") / "base"

def filetext(path: Union[Path, Traversable]) -> str:
    with path.open('r', encoding='utf-8') as fobj:
        t = fobj.read()
    return t

def flatten(t: "Flattenable") -> str:
    io = BytesIO()
    writer.flattenToFile(io, t)
    return io.getvalue().decode()


def getHTMLOf(ob: model.Documentable) -> str:
    wr = templatewriter.TemplateWriter(Path(), TemplateLookup(template_dir))
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
    t = ChildTable(pages.DocGetter(), mod, [], ChildTable.lookup_loader(TemplateLookup(template_dir)))
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table() -> None:
    mod = fromText('def f(): pass')
    t = ChildTable(pages.DocGetter(), mod, mod.contents.values(), ChildTable.lookup_loader(TemplateLookup(template_dir)))
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
    w = writer.TemplateWriter(tmp_path, TemplateLookup(template_dir))
    system.options.htmlusesplitlinks = True
    system.options.htmlusesorttable = True
    w.prepOutputDirectory()
    root, = system.rootobjects
    w._writeDocsFor(root)
    w.writeSummaryPages(system)
    for ob in system.allobjects.values():
        url = ob.url
        if '#' in url:
            url = url[:url.find('#')]
        assert (tmp_path / url).is_file()
    with open(tmp_path / 'basic.html', encoding='utf-8') as f:
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
    lookup = TemplateLookup(template_dir)
    for template in lookup._templates.values():
        if isinstance(template, HtmlTemplate) and not len(template.text.strip()) == 0:
            assert template.version >= 1

def test_template_lookup_get_template() -> None:

    lookup = TemplateLookup(template_dir)

    here = Path(__file__).parent

    index = lookup.get_template('index.html')
    assert isinstance(index, HtmlTemplate)
    assert index.text == filetext(template_dir / 'index.html')

    lookup.add_template(HtmlTemplate(name='footer.html', 
                            text=filetext(here / 'testcustomtemplates' / 'faketemplate' / 'footer.html')))

    footer = lookup.get_template('footer.html')
    assert isinstance(footer, HtmlTemplate)
    assert footer.text == filetext(here / 'testcustomtemplates' / 'faketemplate' / 'footer.html')

    index2 = lookup.get_template('index.html')
    assert isinstance(index2, HtmlTemplate)
    assert index2.text == filetext(template_dir / 'index.html')

    lookup = TemplateLookup(template_dir)

    footer = lookup.get_template('footer.html')
    assert isinstance(footer, HtmlTemplate)
    assert footer.text == filetext(template_dir / 'footer.html')

    subheader = lookup.get_template('subheader.html')
    assert isinstance(subheader, HtmlTemplate)
    assert subheader.version == -1

    table = lookup.get_template('table.html')
    assert isinstance(table, HtmlTemplate)
    assert table.version == 1

def test_template_lookup_add_template_warns() -> None:

    lookup = TemplateLookup(template_dir)

    here = Path(__file__).parent

    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'nav.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(HtmlTemplate(text=fobj.read(), name='nav.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Your custom template 'nav.html' is out of date" in str(catch_warnings.pop().message)

    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'table.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(HtmlTemplate(text=fobj.read(), name='table.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Could not read 'table.html' template version" in str(catch_warnings.pop().message)

    with pytest.warns(UserWarning) as catch_warnings:
        with (here / 'testcustomtemplates' / 'faketemplate' / 'summary.html').open('r', encoding='utf-8') as fobj:
            lookup.add_template(HtmlTemplate(text=fobj.read(), name='summary.html'))
    assert len(catch_warnings) == 1, [str(w.message) for w in catch_warnings]
    assert "Could not read 'summary.html' template version" in str(catch_warnings.pop().message)

    with pytest.warns(UserWarning) as catch_warnings:
        lookup.add_templatedir(here / 'testcustomtemplates' / 'faketemplate')
    assert len(catch_warnings) == 2, [str(w.message) for w in catch_warnings]

def test_template_lookup_add_template_allok() -> None:

    here = Path(__file__).parent

    with warnings.catch_warnings(record=True) as catch_warnings:
        warnings.simplefilter("always")
        lookup = TemplateLookup(template_dir)
        lookup.add_templatedir(here / 'testcustomtemplates' / 'allok')
    assert len(catch_warnings) == 0, [str(w.message) for w in catch_warnings]

def test_template_lookup_add_template_raises() -> None:

    here = Path(__file__).parent

    lookup = TemplateLookup(template_dir)

    with pytest.raises(UnsupportedTemplateVersion):
        lookup.add_template(HtmlTemplate(name="nav.html", text="""
        <nav>
            <meta name="pydoctor-template-version" content="2050" />
        </nav>
        """))

    with pytest.raises(ValueError):
        lookup.add_template(HtmlTemplate(name="nav.html", text="<nav></nav><span> Words </span>"))
    
    with pytest.raises(OverrideTemplateNotAllowed):
        lookup.add_template(HtmlTemplate(name="apidocs.css", text="<nav></nav>"))

    with pytest.raises(OverrideTemplateNotAllowed):
        lookup.add_template(StaticTemplate(name="index.html", data=bytes()))

    lookup.add_templatedir(here / 'testcustomtemplates' / 'subfolders')

    with pytest.raises(OverrideTemplateNotAllowed):
        lookup.add_template(StaticTemplate('static', data=bytes()))
    with pytest.raises(OverrideTemplateNotAllowed):
        lookup.add_template(HtmlTemplate('static/fonts', text="<nav></nav>"))
    with pytest.raises(OverrideTemplateNotAllowed):
        lookup.add_template(HtmlTemplate('Static/Fonts', text="<nav></nav>"))
    # Should not fail
    lookup.add_template(StaticTemplate('tatic/fonts', data=bytes()))


def test_template_fromdir_fromfile_failure() -> None:

    here = Path(__file__).parent
    
    with pytest.raises(FailedToCreateTemplate):
        [t for t in Template.fromdir(here / 'testcustomtemplates' / 'thisfolderdonotexist')]
    
    template = Template.fromfile(here / 'testcustomtemplates' / 'subfolders', PurePath())
    assert not template

    template = Template.fromfile(here / 'testcustomtemplates' / 'thisfolderdonotexist', PurePath('whatever'))
    assert not template

def test_template() -> None:

    here = Path(__file__).parent

    js_template = Template.fromfile(here / 'testcustomtemplates' / 'faketemplate', PurePath('pydoctor.js'))
    html_template = Template.fromfile(here / 'testcustomtemplates' / 'faketemplate', PurePath('nav.html'))

    assert isinstance(js_template, StaticTemplate)
    assert isinstance(html_template, HtmlTemplate)

def test_template_subfolders_write(tmp_path: Path) -> None:
    here = Path(__file__).parent
    test_build_dir = tmp_path

    lookup = TemplateLookup(here / 'testcustomtemplates' / 'subfolders')

     # writes only the static template

    for t in lookup.templates:
        if isinstance(t, StaticTemplate):
            t.write(test_build_dir)

    assert test_build_dir.joinpath('static').is_dir()
    assert not test_build_dir.joinpath('atemplate.html').exists()
    assert test_build_dir.joinpath('static/info.svg').is_file()
    assert test_build_dir.joinpath('static/lol.svg').is_file()
    assert test_build_dir.joinpath('static/fonts').is_dir()
    assert test_build_dir.joinpath('static/fonts/bar.svg').is_file()
    assert test_build_dir.joinpath('static/fonts/foo.svg').is_file()

def test_template_subfolders_overrides() -> None:
    here = Path(__file__).parent

    lookup = TemplateLookup(here / 'testcustomtemplates' / 'subfolders')

    atemplate = lookup.get_template('atemplate.html')
    static_info = lookup.get_template('static/info.svg')
    static_lol = lookup.get_template('static/lol.svg')
    static_fonts_bar = lookup.get_template('static/fonts/bar.svg')
    static_fonts_foo = lookup.get_template('static/fonts/foo.svg')

    assert isinstance(atemplate, HtmlTemplate)
    assert isinstance(static_info, StaticTemplate)
    assert isinstance(static_lol, StaticTemplate)
    assert isinstance(static_fonts_bar, StaticTemplate)
    assert isinstance(static_fonts_foo, StaticTemplate)

    assert len(static_fonts_foo.data) == 0

    # Load subfolder contents that will override only one template: static/fonts/foo.svg
    lookup.add_templatedir(here / 'testcustomtemplates' / 'overridesubfolders')

    # test nothing changed
    atemplate = lookup.get_template('atemplate.html')
    static_info = lookup.get_template('static/info.svg')
    static_lol = lookup.get_template('static/lol.svg')
    static_fonts_bar = lookup.get_template('static/fonts/bar.svg')
    static_fonts_foo = lookup.get_template('static/fonts/foo.svg')

    assert isinstance(atemplate, HtmlTemplate)
    assert isinstance(static_info, StaticTemplate)
    assert isinstance(static_lol, StaticTemplate)
    assert isinstance(static_fonts_bar, StaticTemplate)
    assert isinstance(static_fonts_foo, StaticTemplate)

    # Except for the overriden file
    assert len(static_fonts_foo.data) > 0

def test_template_casing() -> None:
    
    here = Path(__file__).parent

    html_template1 = Template.fromfile(here / 'testcustomtemplates' / 'casing', PurePath('test1/nav.HTML'))
    html_template2 = Template.fromfile(here / 'testcustomtemplates' / 'casing', PurePath('test2/nav.Html'))
    html_template3 = Template.fromfile(here / 'testcustomtemplates' / 'casing', PurePath('test3/nav.htmL'))

    assert isinstance(html_template1, HtmlTemplate)
    assert isinstance(html_template2, HtmlTemplate)
    assert isinstance(html_template3, HtmlTemplate)

def test_templatelookup_casing() -> None:
    here = Path(__file__).parent

    lookup = TemplateLookup(here / 'testcustomtemplates' / 'casing' / 'test1')
    lookup.add_templatedir(here / 'testcustomtemplates' / 'casing' / 'test2')
    lookup.add_templatedir(here / 'testcustomtemplates' / 'casing' / 'test3')

    assert len(list(lookup.templates)) == 1

    lookup = TemplateLookup(here / 'testcustomtemplates' / 'subfolders')

    assert lookup.get_template('atemplate.html') == lookup.get_template('ATemplaTe.HTML')
    assert lookup.get_template('static/fonts/bar.svg') == lookup.get_template('StAtic/Fonts/BAr.svg')

    static_fonts_bar = lookup.get_template('static/fonts/bar.svg')
    assert static_fonts_bar.name == 'static/fonts/bar.svg'

    lookup.add_template(StaticTemplate('Static/Fonts/Bar.svg', bytes()))

    static_fonts_bar = lookup.get_template('static/fonts/bar.svg')
    assert static_fonts_bar.name == 'static/fonts/bar.svg' # the Template.name attribute has been changed by add_template()

def is_fs_case_sensitive() -> bool:
    # From https://stackoverflow.com/a/36580834
    with tempfile.NamedTemporaryFile(prefix='TmP') as tmp_file:
        return(not os.path.exists(tmp_file.name.lower()))

@pytest.mark.skipif(not is_fs_case_sensitive(), reason="This test requires a case sensitive file system.")
def test_template_subfolders_write_casing(tmp_path: Path) -> None:

    here = Path(__file__).parent
    test_build_dir = tmp_path

    lookup = TemplateLookup(here / 'testcustomtemplates' / 'subfolders')

    lookup.add_template(StaticTemplate('static/Info.svg', data=bytes()))
    lookup.add_template(StaticTemplate('Static/Fonts/Bar.svg', data=bytes()))

    # writes only the static template

    for t in lookup.templates:
        if isinstance(t, StaticTemplate):
            t.write(test_build_dir)

    assert test_build_dir.joinpath('static/info.svg').is_file()
    assert not test_build_dir.joinpath('static/Info.svg').is_file()

    assert not test_build_dir.joinpath('Static/Fonts').is_dir()
    assert test_build_dir.joinpath('static/fonts/bar.svg').is_file()


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
    assert not func(cast(model.Class, public))
    assert not func(cast(model.Class, public.contents['Inner']))
    private = mod.contents['_Private']
    assert func(cast(model.Class, private))
    assert func(cast(model.Class, private.contents['Inner']))


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
    assert not isClassNodePrivate(cast(model.Class, mod.contents['Public']))
    assert isClassNodePrivate(cast(model.Class, mod.contents['_Private']))
    assert not isClassNodePrivate(cast(model.Class, mod.contents['_BaseForPublic']))
    assert isClassNodePrivate(cast(model.Class, mod.contents['_BaseForPrivate']))

def test_format_signature() -> None:
    """Test C{pages.format_signature}. 
    
    @note: This test will need to be adapted one we include annotations inside signatures.
    """
    mod = fromText(r'''
    def func(a:Union[bytes, str]=_get_func_default(str), b:Any=re.compile(r'foo|bar'), *args:str, **kwargs:Any) -> Iterator[Union[str, bytes]]:
        ...
    ''')
    assert ("""(a=_get_func_default(<wbr></wbr>str), b=re.compile("""
            """r<span class="rst-variable-quote">'</span>foo<span class="rst-re-op">|</span>"""
            """bar<span class="rst-variable-quote">'</span>), *args, **kwargs)""") in flatten(pages.format_signature(cast(model.Function, mod.contents['func'])))

def test_format_decorators() -> None:
    """Test C{pages.format_decorators}"""
    mod = fromText(r'''
    @string_decorator(set('\\/:*?"<>|\f\v\t\r\n'))
    @simple_decorator(max_examples=700, deadline=None, option=range(10))
    def func():
        ...
    ''')
    stan = stanutils.flatten(list(pages.format_decorators(cast(model.Function, mod.contents['func']))))
    assert stan == ("""@string_decorator(<wbr></wbr>set(<wbr></wbr><span class="rst-variable-quote">'</span>"""
                    r"""<span class="rst-variable-string">\\/:*?"&lt;&gt;|\f\v\t\r\n</span>"""
                    """<span class="rst-variable-quote">'</span>))<br />@simple_decorator"""
                    """(<wbr></wbr>max_examples=700, <wbr></wbr>deadline=None, <wbr></wbr>option=range(<wbr></wbr>10))<br />""")
