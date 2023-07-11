from typing import List, Optional, Type, cast, TYPE_CHECKING
import re

from pytest import mark, raises
import pytest
from twisted.web.template import Tag, tags

from pydoctor import epydoc2stan, model, linker
from pydoctor.epydoc.markup import get_supported_docformats
from pydoctor.stanutils import flatten, flatten_text
from pydoctor.epydoc.markup.epytext import ParsedEpytextDocstring
from pydoctor.sphinx import SphinxInventory
from pydoctor.test.test_astbuilder import fromText, unwrap
from pydoctor.test import CapSys, NotFoundLinker
from pydoctor.templatewriter.search import stem_identifier
from pydoctor.templatewriter.pages import format_signature, format_class_signature

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


def test_multiple_types() -> None:
    mod = fromText('''
    def f(a):
        """
        @param a: it\'s a parameter!
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class C:
        """
        @ivar a: it\'s an instance var
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class D:
        """
        @cvar a: it\'s an instance var
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class E:
        """
        @cvar: missing name
        @type: name still missing
        """
    ''')
    # basically "assert not fail":
    epydoc2stan.format_docstring(mod.contents['f'])
    epydoc2stan.format_docstring(mod.contents['C'])
    epydoc2stan.format_docstring(mod.contents['D'])
    epydoc2stan.format_docstring(mod.contents['E'])


def docstring2html(obj: model.Documentable, docformat: Optional[str] = None) -> str:
    if docformat:
        obj.module.docformat = docformat
    stan = epydoc2stan.format_docstring(obj)
    assert stan.tagName == 'div', stan
    # We strip off break lines for the sake of simplicity.
    return flatten(stan).replace('><', '>\n<').replace('<wbr></wbr>', '').replace('<wbr>\n</wbr>', '')

def summary2html(obj: model.Documentable) -> str:
    stan = epydoc2stan.format_summary(obj)
    if stan.attributes.get('class') == 'undocumented':
        assert stan.tagName == 'span', stan
    else:
        # Summaries are now generated without englobing <span> when we don't need one. 
        assert stan.tagName == '', stan
    return flatten(stan.children)


def test_html_empty_module() -> None:
    # checks the presence of at least one paragraph on all docstrings
    mod = fromText('''
    """Empty module."""
    ''')
    assert docstring2html(mod) == "<div>\n<p>Empty module.</p>\n</div>"

    mod = fromText('''
    """
    Empty module.
    
    Another paragraph.
    """
    ''')
    assert docstring2html(mod) == "<div>\n<p>Empty module.</p>\n<p>Another paragraph.</p>\n</div>"

    mod = fromText('''
    """C{thing}"""
    ''', modname='module')
    assert docstring2html(mod) == '<div>\n<p>\n<tt class="rst-docutils literal">thing</tt>\n</p>\n</div>'

    mod = fromText('''
    """My C{thing}."""
    ''', modname='module')
    assert docstring2html(mod) == '<div>\n<p>My <tt class="rst-docutils literal">thing</tt>.</p>\n</div>'

    mod = fromText('''
    """
    @note: There is no paragraph here. 
    """
    ''')
    assert '<p>' not in docstring2html(mod)

def test_xref_link_not_found() -> None:
    """A linked name that is not found is output as text."""
    mod = fromText('''
    """This link leads L{nowhere}."""
    ''', modname='test')
    html = docstring2html(mod)
    assert '<code>nowhere</code>' in html


def test_xref_link_same_page() -> None:
    """A linked name that is documented on the same page is linked using only
    a fragment as the URL. But that does not happend in summaries. 
    """
    src = '''
    """The home of L{local_func}."""

    def local_func():
        pass
    '''
    mod = fromText(src, modname='test')
    assert mod.page_object.url == 'index.html'
    html = docstring2html(mod)
    assert 'href="#local_func"' in html
    html = summary2html(mod)
    assert 'href="index.html#local_func"' in html
    html = docstring2html(mod)
    assert 'href="#local_func"' in html
    
    mod = fromText(src, modname='test')
    html = summary2html(mod)
    assert 'href="index.html#local_func"' in html
    html = docstring2html(mod)
    assert 'href="#local_func"' in html
    html = summary2html(mod)
    assert 'href="index.html#local_func"' in html



def test_xref_link_other_page() -> None:
    """A linked name that is documented on a different page but within the
    same project is linked using a relative URL.
    """
    mod1 = fromText('''
    def func():
        """This is not L{test2.func}."""
    ''', modname='test1')
    fromText('''
    def func():
        pass
    ''', modname='test2', system=mod1.system)
    html = docstring2html(mod1.contents['func'])
    assert 'href="test2.html#func"' in html


def test_xref_link_intersphinx() -> None:
    """A linked name that is documented in another project is linked using
    an absolute URL (retrieved via Intersphinx).
    """
    mod = fromText('''
    def func():
        """This is a thin wrapper around L{external.func}."""
    ''', modname='test')

    system = mod.system
    inventory = SphinxInventory(system.msg)
    inventory._links['external.func'] = ('https://example.net', 'lib.html#func')
    system.intersphinx = inventory

    html = docstring2html(mod.contents['func'])
    assert 'href="https://example.net/lib.html#func"' in html


def test_func_undocumented_return_nothing() -> None:
    """When the returned value is undocumented (no 'return' field) and its type
    annotation is None, omit the "Returns" entry from the output.
    """
    mod = fromText('''
    def nop() -> None:
        pass
    ''')
    func = mod.contents['nop']
    lines = docstring2html(func).split('\n')
    assert '<td class="fieldName">Returns</td>' not in lines


def test_func_undocumented_return_something() -> None:
    """When the returned value is undocumented (no 'return' field) and its type
    annotation is not None, do not include the "Returns" entry in the field
    table. It will be shown in the signature.
    """
    mod = fromText('''
    def get_answer() -> int:
        return 42
    ''')
    func = mod.contents['get_answer']
    lines = docstring2html(func).splitlines()
    expected_html = [
        '<div>',
        '<p class="undocumented">Undocumented</p>',
        '</div>',
    ]
    assert lines == expected_html, str(lines)

def test_func_only_single_param_doc() -> None:
    """When only a single parameter is documented, all parameters show with
    undocumented parameters marked as such.
    """
    mod = fromText('''
    def f(x, y):
        """
        @param x: Actual documentation.
        """
    ''')
    lines = docstring2html(mod.contents['f']).splitlines()
    expected_html = [
        '<div>', '<table class="fieldTable">',
        '<tr class="fieldStart">',
        '<td class="fieldName" colspan="2">Parameters</td>',
        '</tr>', '<tr>',
        '<td class="fieldArgContainer">',
        '<span class="fieldArg">x</span>',
        '</td>', '<td class="fieldArgDesc">Actual documentation.</td>',
        '</tr>', '<tr>',
        '<td class="fieldArgContainer">',
        '<span class="fieldArg">y</span>',
        '</td>', '<td class="fieldArgDesc">',
        '<span class="undocumented">Undocumented</span>',
        '</td>', '</tr>', '</table>', '</div>',
    ]
    assert lines == expected_html, str(lines)

def test_func_only_return_doc() -> None:
    """When only return is documented but not parameters, only the return
    section is visible.
    """
    mod = fromText('''
    def f(x: str):
        """
        @return: Actual documentation.
        """
    ''')
    lines = docstring2html(mod.contents['f']).splitlines()
    expected_html = [
        '<div>', '<table class="fieldTable">',
        '<tr class="fieldStart">',
        '<td class="fieldName" colspan="2">Returns</td>',
        '</tr>', '<tr>',
        '<td colspan="2">Actual documentation.</td>',
        '</tr>', '</table>', '</div>',
    ]
    assert lines == expected_html, str(lines)

# These 3 tests fails because AnnotationDocstring is not using node2stan() yet.

@pytest.mark.xfail
def test_func_arg_and_ret_annotation() -> None:
    annotation_mod = fromText('''
    def f(a: List[str], b: "List[str]") -> bool:
        """
        @param a: an arg, a the best of args
        @param b: a param to follow a
        @return: the best that we can do
        """
    ''')
    classic_mod = fromText('''
    def f(a, b):
        """
        @param a: an arg, a the best of args
        @type a: C{List[str]}
        @param b: a param to follow a
        @type b: C{List[str]}
        @return: the best that we can do
        @rtype: C{bool}
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert annotation_fmt == classic_fmt

@pytest.mark.xfail
def test_func_arg_and_ret_annotation_with_override() -> None:
    annotation_mod = fromText('''
    def f(a: List[str], b: List[str]) -> bool:
        """
        @param a: an arg, a the best of args
        @param b: a param to follow a
        @type b: C{List[awesome]}
        @return: the best that we can do
        """
    ''')
    classic_mod = fromText('''
    def f(a, b):
        """
        @param a: an arg, a the best of args
        @type a: C{List[str]}
        @param b: a param to follow a
        @type b: C{List[awesome]}
        @return: the best that we can do
        @rtype: C{bool}
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert annotation_fmt == classic_fmt

def test_func_arg_when_doc_missing_ast_types() -> None:
    """
    Type hints are now included in the signature, so no need to 
    docucument them twice in the param table, only if non of them has documentation.
    """
    annotation_mod = fromText('''
    def f(a: List[str], b: int) -> bool:
        """
        Today I will not document details
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    
    assert 'fieldTable' not in annotation_fmt
    assert 'b:' not in annotation_fmt

def _get_test_func_arg_when_doc_missing_docstring_fields_types_cases() -> List[str]:
    case1="""
        @type a: C{List[str]}
        @type b: C{int}
        @rtype: C{bool}"""
    
    case2="""
        Args
        ----
        a: List[str]
        b: int
        
        Returns
        -------
        bool:"""
    return [case1,case2]

@pytest.mark.parametrize('sig', ['(a)', '(a:List[str])', '(a) -> bool', '(a:List[str], b:int) -> bool'])
@pytest.mark.parametrize('doc', _get_test_func_arg_when_doc_missing_docstring_fields_types_cases())
def test_func_arg_when_doc_missing_docstring_fields_types(sig:str, doc:str) -> None:
    """
    When type fields are present (whether they are coming from napoleon extension or epytext), always show the param table.
    """
    
    classic_mod = fromText(f'''
    __docformat__ = "{'epytext' if '@type' in doc else 'numpy'}"
    def f{sig}:
        """
        Today I will not document details
        {doc}
        """
    ''')

    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert 'fieldTable' in classic_fmt
    assert '<span class="fieldArg' in classic_fmt
    assert 'Parameters' in classic_fmt
    assert 'Returns' in classic_fmt

def test_func_param_duplicate(capsys: CapSys) -> None:
    """Warn when the same parameter is documented more than once."""
    mod = fromText('''
    def f(x, y):
        """
        @param x: Actual documentation.
        @param x: Likely typo or copy-paste error.
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    captured = capsys.readouterr().out
    assert captured == '<test>:5: Parameter "x" was already documented\n'

@mark.parametrize('field', ('param', 'type'))
def test_func_no_such_arg(field: str, capsys: CapSys) -> None:
    """Warn about documented parameters that don't exist in the definition."""
    mod = fromText(f'''
    def f():
        """
        This function takes no arguments...

        @{field} x: ...but it does document one.
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    captured = capsys.readouterr().out
    assert captured == '<test>:6: Documented parameter "x" does not exist\n'

def test_func_no_such_arg_warn_once(capsys: CapSys) -> None:
    """Warn exactly once about a param/type combination not existing."""
    mod = fromText('''
    def f():
        """
        @param x: Param first.
        @type x: Param first.
        @type y: Type first.
        @param y: Type first.
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    captured = capsys.readouterr().out
    assert captured == (
        '<test>:4: Documented parameter "x" does not exist\n'
        '<test>:6: Documented parameter "y" does not exist\n'
        )

def test_func_arg_not_inherited(capsys: CapSys) -> None:
    """Do not warn when a subclass method lacks parameters that are documented
    in an inherited docstring.
    """
    mod = fromText('''
    class Base:
        def __init__(self, value):
            """
            @param value: Preciousss.
            @type value: Gold.
            """
    class Sub(Base):
        def __init__(self):
            super().__init__(1)
    ''')
    epydoc2stan.format_docstring(mod.contents['Base'].contents['__init__'])
    assert capsys.readouterr().out == ''
    epydoc2stan.format_docstring(mod.contents['Sub'].contents['__init__'])
    assert capsys.readouterr().out == ''

def test_func_param_as_keyword(capsys: CapSys) -> None:
    """Warn when a parameter is documented as a @keyword."""
    mod = fromText('''
    def f(p, **kwargs):
        """
        @keyword a: Advanced.
        @keyword b: Basic.
        @type b: Type for previously introduced keyword.
        @keyword p: A parameter, not a keyword.
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    assert capsys.readouterr().out == '<test>:7: Parameter "p" is documented as keyword\n'

def test_func_missing_param_name(capsys: CapSys) -> None:
    """Param and type fields must include the name of the parameter."""
    mod = fromText('''
    def f(a, b):
        """
        @param a: The first parameter.
        @param: The other one.
        @type: C{str}
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    captured = capsys.readouterr().out
    assert captured == (
        '<test>:5: Parameter name missing\n'
        '<test>:6: Parameter name missing\n'
        )

def test_missing_param_computed_base(capsys: CapSys) -> None:
    """Do not warn if a parameter might be added by a computed base class."""
    mod = fromText('''
    from twisted.python import components
    import zope.interface
    class IFoo(zope.interface.Interface):
        pass
    class Proxy(components.proxyForInterface(IFoo)):
        """
        @param original: The wrapped instance.
        """
    ''')
    html = ''.join(docstring2html(mod.contents['Proxy']).splitlines())
    assert '<td class="fieldArgDesc">The wrapped instance.</td>' in html
    captured = capsys.readouterr().out
    assert captured == ''

def test_constructor_param_on_class(capsys: CapSys) -> None:
    """Constructor parameters can be documented on the class."""
    mod = fromText('''
    class C:
        """
        @param p: Constructor parameter.
        @param q: Not a constructor parameter.
        """
        def __init__(self, p):
            pass
    ''')
    html = ''.join(docstring2html(mod.contents['C']).splitlines())
    assert '<td class="fieldArgDesc">Constructor parameter.</td>' in html
    # Non-existing parameters should still end up in the output, because:
    # - pydoctor might be wrong about them not existing
    # - the documentation may still be useful, for example if belongs to
    #   an existing parameter but the name in the @param field has a typo
    assert '<td class="fieldArgDesc">Not a constructor parameter.</td>' in html
    captured = capsys.readouterr().out
    assert captured == '<test>:5: Documented parameter "q" does not exist\n'


def test_func_raise_linked() -> None:
    """Raise fields are formatted by linking the exception type."""
    mod = fromText('''
    class SpanishInquisition(Exception):
        pass
    def f():
        """
        @raise SpanishInquisition: If something unexpected happens.
        """
    ''', modname='test')
    html = docstring2html(mod.contents['f']).split('\n')
    assert '<a href="test.SpanishInquisition.html" class="internal-link" title="test.SpanishInquisition">SpanishInquisition</a>' in html


def test_func_raise_missing_exception_type(capsys: CapSys) -> None:
    """When a C{raise} field is missing the exception type, a warning is logged
    and the HTML will list the exception type as unknown.
    """
    mod = fromText('''
    def f(x):
        """
        @raise ValueError: If C{x} is rejected.
        @raise: On a blue moon.
        """
    ''')
    func = mod.contents['f']
    epydoc2stan.format_docstring(func)
    captured = capsys.readouterr().out
    assert captured == '<test>:5: Exception type missing\n'
    html = docstring2html(func).split('\n')
    assert '<span class="undocumented">Unknown exception</span>' in html


def test_unexpected_field_args(capsys: CapSys) -> None:
    """Warn when field arguments that should be empty aren't."""
    mod = fromText('''
    def get_it():
        """
        @return value: The thing you asked for, probably.
        @rtype value: Not a clue.
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['get_it'])
    captured = capsys.readouterr().out
    assert captured == "<test>:4: Unexpected argument in return field\n" \
                       "<test>:5: Unexpected argument in rtype field\n"


def test_func_starargs(capsys: CapSys) -> None:
    """
    Var-args can be named in fields with or without asterixes.
    Constructor parameters can be documented on the class.

    @note: Asterixes need to be escaped with reStructuredText.
    """

    mod_epy_star = fromText('''
    class f:
        """
        Do something with var-positional and var-keyword arguments.

        @param *args: var-positional arguments
        @param **kwargs: var-keyword arguments
        @type **kwargs: str
        """
        def __init__(*args: int, **kwargs) -> None:
            ...
    ''', modname='<great>')

    mod_epy_no_star = fromText('''
    class f:
        """
        Do something with var-positional and var-keyword arguments.

        @param args: var-positional arguments
        @param kwargs: var-keyword arguments
        @type kwargs: str
        """
        def __init__(*args: int, **kwargs) -> None:
            ...
    ''', modname='<good>')

    mod_rst_star = fromText(r'''
    __docformat__='restructuredtext'
    class f:
        r"""
        Do something with var-positional and var-keyword arguments.

        :param \*args: var-positional arguments
        :param \*\*kwargs: var-keyword arguments
        :type \*\*kwargs: str
        """
        def __init__(*args: int, **kwargs) -> None:
            ...
    ''', modname='<great>')

    mod_rst_no_star = fromText('''
    __docformat__='restructuredtext'
    class f:
        """
        Do something with var-positional and var-keyword arguments.

        :param args: var-positional arguments
        :param kwargs: var-keyword arguments
        :type kwargs: str
        """
        def __init__(*args: int, **kwargs) -> None:
            ...
    ''', modname='<great>')

    mod_epy_star_fmt = docstring2html(mod_epy_star.contents['f'])
    mod_epy_no_star_fmt = docstring2html(mod_epy_no_star.contents['f'])
    mod_rst_star_fmt = docstring2html(mod_rst_star.contents['f'])
    mod_rst_no_star_fmt = docstring2html(mod_rst_no_star.contents['f'])
    
    assert mod_rst_star_fmt == mod_rst_no_star_fmt == mod_epy_star_fmt == mod_epy_no_star_fmt

    expected_parts = ['<span class="fieldArg">*args</span>', 
                      '<span class="fieldArg">**kwargs</span>',]
    
    for part in expected_parts:
        assert part in mod_epy_star_fmt

    captured = capsys.readouterr().out
    assert not captured

def test_func_starargs_more(capsys: CapSys) -> None:
    """
    Star arguments, even if there are not named 'args' or 'kwargs', are recognized.
    """

    mod_epy_with_asterixes = fromText('''
    def f(args, kwargs, *a, **kwa) -> None:
        """
        Do something with var-positional and var-keyword arguments.

        @param args: some regular argument
        @param kwargs: some regular argument
        @param *a: var-positional arguments
        @param **kwa: var-keyword arguments
        """
    ''', modname='<great>')

    mod_rst_with_asterixes = fromText(r'''
    def f(args, kwargs, *a, **kwa) -> None:
        r"""
        Do something with var-positional and var-keyword arguments.

        :param args: some regular argument
        :param kwargs: some regular argument
        :param \*a: var-positional arguments
        :param \*\*kwa: var-keyword arguments
        """
    ''', modname='<great>')

    mod_rst_without_asterixes = fromText('''
    def f(args, kwargs, *a, **kwa) -> None:
        """
        Do something with var-positional and var-keyword arguments.

        :param args: some regular argument
        :param kwargs: some regular argument
        :param a: var-positional arguments
        :param kwa: var-keyword arguments
        """
    ''', modname='<great>')

    mod_epy_without_asterixes = fromText('''
    def f(args, kwargs, *a, **kwa) -> None:
        """
        Do something with var-positional and var-keyword arguments.

        @param args: some regular argument
        @param kwargs: some regular argument
        @param a: var-positional arguments
        @param kwa: var-keyword arguments
        """
    ''', modname='<good>')

    epy_with_asterixes_fmt = docstring2html(mod_epy_with_asterixes.contents['f'])
    rst_with_asterixes_fmt = docstring2html(mod_rst_with_asterixes.contents['f'], docformat='restructuredtext')
    rst_without_asterixes_fmt = docstring2html(mod_rst_without_asterixes.contents['f'], docformat='restructuredtext')
    epy_without_asterixes_fmt = docstring2html(mod_epy_without_asterixes.contents['f'])

    assert epy_with_asterixes_fmt == rst_with_asterixes_fmt == rst_without_asterixes_fmt == epy_without_asterixes_fmt
    
    expected_parts = ['<span class="fieldArg">args</span>', 
                      '<span class="fieldArg">kwargs</span>',
                      '<span class="fieldArg">*a</span>',
                      '<span class="fieldArg">**kwa</span>',]
    
    for part in expected_parts:
        assert part in epy_with_asterixes_fmt
    
    captured = capsys.readouterr().out
    assert not captured

def test_func_starargs_hidden_when_keywords_documented(capsys:CapSys) -> None:
    """
    When a function accept variable keywords (**kwargs) and keywords are specifically
    documented and the **kwargs IS NOT documented: entry for **kwargs IS NOT presented at all.

    In other words: They variable keywords argument documentation is optional when specific documentation
    is given for each keyword, and when missing, no warning is raised.
    """
    # tests for issue https://github.com/twisted/pydoctor/issues/697

    mod = fromText('''
    __docformat__='restructuredtext'
    def f(one, two, **kwa) -> None:
        """
        var-keyword arguments are specifically documented. 

        :param one: some regular argument
        :param two: some regular argument
        :keyword something: An argument
        :keyword another: Another
        """
    ''')

    html = docstring2html(mod.contents['f'])
    assert '**kwa' not in html
    assert not capsys.readouterr().out

def test_func_starargs_shown_when_documented(capsys:CapSys) -> None:
    """
    When a function accept variable keywords (**kwargs) and keywords are specifically
    documented and the **kwargs IS documented: entry for **kwargs IS presented AFTER all keywords.

    In other words: When a function has the keywords arguments, the keywords can have dedicated 
    docstring, besides the separate documentation for each keyword.
    """

    mod = fromText('''
    __docformat__='restructuredtext'
    def f(one, two, **kwa) -> None:
        """
       var-keyword arguments are specifically documented as well as other extra keywords.

        :param one: some regular argument
        :param two: some regular argument
        :param kwa: Other keywords are passed to ``parse`` function.
        :keyword something: An argument
        :keyword another: Another
        """
    ''')
    html = docstring2html(mod.contents['f'])
    # **kwa should be presented AFTER all other parameters
    assert re.match('.+one.+two.+something.+another.+kwa', html, flags=re.DOTALL)
    assert not capsys.readouterr().out

def test_func_starargs_shown_when_undocumented(capsys:CapSys) -> None:
    """
    When a function accept variable keywords (**kwargs) and NO keywords are specifically
    documented and the **kwargs IS NOT documented: entry for **kwargs IS presented as undocumented.
    """

    mod = fromText('''
    __docformat__='restructuredtext'
    def f(one, two, **kwa) -> None:
        """
        var-keyword arguments are not specifically documented

        :param one: some regular argument
        :param two: some regular argument
        """
    ''')

    html = docstring2html(mod.contents['f'])
    assert re.match('.+one.+two.+kwa', html, flags=re.DOTALL)
    assert not capsys.readouterr().out

def test_func_starargs_wrongly_documented(capsys: CapSys) -> None:
    numpy_wrong = fromText('''
    __docformat__='numpy'
    def f(one, **kwargs):
        """
        var-keyword arguments are wrongly documented with the "Arguments" section.

        Arguments
        ---------
        kwargs:
            var-keyword arguments
        stuff:
            a var-keyword argument
        """
    ''', modname='numpy_wrong')

    rst_wrong = fromText('''
    __docformat__='restructuredtext'
    def f(one, **kwargs):
        """
        var-keyword arguments are wrongly documented with the "param" field.

        :param kwargs: var-keyword arguments
        :param stuff: a var-keyword argument
        """
    ''', modname='rst_wrong')

    docstring2html(numpy_wrong.contents['f'])
    assert 'Documented parameter "stuff" does not exist, variable keywords should be documented with the "Keyword Arguments" section' in capsys.readouterr().out
    
    docstring2html(rst_wrong.contents['f'])
    assert 'Documented parameter "stuff" does not exist, variable keywords should be documented with the "keyword" field' in capsys.readouterr().out

def test_summary() -> None:
    mod = fromText('''
    def single_line_summary():
        """
        Lorem Ipsum

        Ipsum Lorem
        """
    def still_summary_since_2022():
        """
        Foo
        Bar
        Baz
        Qux
        """
    def three_lines_summary():
        """
        Foo
        Bar
        Baz

        Lorem Ipsum
        """
    ''')
    assert 'Lorem Ipsum' == summary2html(mod.contents['single_line_summary'])
    assert 'Foo Bar Baz' == summary2html(mod.contents['three_lines_summary'])

    # We get a summary based on the first sentences of the first 
    # paragraph until reached maximum number characters or the paragraph ends.
    # So no matter the number of lines the first paragraph is, we'll always get a summary.
    assert 'Foo Bar Baz Qux' == summary2html(mod.contents['still_summary_since_2022']) 


def test_ivar_overriding_attribute() -> None:
    """An 'ivar' field in a subclass overrides a docstring for the same
    attribute set in the base class.

    The 'a' attribute in the test code reproduces a regression introduced
    in pydoctor 20.7.0, where the summary would be constructed from the base
    class documentation instead. The problem was in the fact that a split
    field's docstring is stored in 'parsed_docstring', while format_summary()
    looked there only if no unparsed docstring could be found.

    The 'b' attribute in the test code is there to make sure that in the
    absence of an 'ivar' field, the docstring is inherited.
    """

    mod = fromText('''
    class Base:
        a: str
        """base doc

        details
        """

        b: object
        """not overridden

        details
        """

    class Sub(Base):
        """
        @ivar a: sub doc
        @type b: sub type
        """
    ''')

    base = mod.contents['Base']
    base_a = base.contents['a']
    assert isinstance(base_a, model.Attribute)
    assert summary2html(base_a) == "base doc"
    assert docstring2html(base_a) == "<div>\n<p>base doc</p>\n<p>details</p>\n</div>"
    base_b = base.contents['b']
    assert isinstance(base_b, model.Attribute)
    assert summary2html(base_b) == "not overridden"
    assert docstring2html(base_b) == "<div>\n<p>not overridden</p>\n<p>details</p>\n</div>"

    sub = mod.contents['Sub']
    sub_a = sub.contents['a']
    assert isinstance(sub_a, model.Attribute)
    assert summary2html(sub_a) == 'sub doc'
    assert docstring2html(sub_a) == "<div>\n<p>sub doc</p>\n</div>"
    sub_b = sub.contents['b']
    assert isinstance(sub_b, model.Attribute)
    assert summary2html(sub_b) == 'not overridden'
    assert docstring2html(sub_b) == "<div>\n<p>not overridden</p>\n<p>details</p>\n</div>"


def test_missing_field_name(capsys: CapSys) -> None:
    mod = fromText('''
    """
    A test module.

    @ivar: Mystery variable.
    @type: str
    """
    ''', modname='test')
    epydoc2stan.format_docstring(mod)
    captured = capsys.readouterr().out
    assert captured == "test:5: Missing field name in @ivar\n" \
                       "test:6: Missing field name in @type\n"


def test_unknown_field_name(capsys: CapSys) -> None:
    mod = fromText('''
    """
    A test module.

    @zap: No such field.
    """
    ''', modname='test')
    epydoc2stan.format_docstring(mod)
    captured = capsys.readouterr().out
    assert captured == "test:5: Unknown field 'zap'\n"


def test_inline_field_type(capsys: CapSys) -> None:
    """The C{type} field in a variable docstring updates the C{parsed_type}
    of the Attribute it documents.
    """
    mod = fromText('''
    a = 2
    """
    Variable documented by inline docstring.
    @type: number
    """
    ''', modname='test')
    a = mod.contents['a']
    assert isinstance(a, model.Attribute)
    epydoc2stan.format_docstring(a)
    assert isinstance(a.parsed_type, ParsedEpytextDocstring)
    assert str(unwrap(a.parsed_type)) == 'number'
    assert not capsys.readouterr().out


def test_inline_field_name(capsys: CapSys) -> None:
    """Warn if a name is given for a C{type} field in a variable docstring.
    A variable docstring only documents a single variable, so the name is
    redundant at best and misleading at worst.
    """
    mod = fromText('''
    a = 2
    """
    Variable documented by inline docstring.
    @type a: number
    """
    ''', modname='test')
    a = mod.contents['a']
    assert isinstance(a, model.Attribute)
    epydoc2stan.format_docstring(a)
    captured = capsys.readouterr().out
    assert captured == "test:5: Field in variable docstring should not include a name\n"

@pytest.mark.parametrize('linkercls', [linker._EpydocLinker])
def test_EpydocLinker_switch_context(linkercls:Type[linker._EpydocLinker]) -> None:
    """
    Test for switching the page context of the EpydocLinker.
    """
    mod = fromText('''
    v=0
    class Klass:
        class InnerKlass(Klass):
            def f():...
            Klass = 'not this one!'
            class v: 
                'not this one!'
    ''', modname='test')
    Klass = mod.contents['Klass']
    assert isinstance(Klass, model.Class)
    InnerKlass = Klass.contents['InnerKlass']
    assert isinstance(InnerKlass, model.Class)
    
    # patch with the linkercls
    mod._linker = linkercls(mod)
    Klass._linker = linkercls(Klass)
    InnerKlass._linker = linkercls(InnerKlass)

    # Evaluating the name of the base classes must be done in the upper scope
    # in order to avoid the following to happen:
    assert 'href="#Klass"' in flatten(InnerKlass.docstring_linker.link_to('Klass', 'Klass'))
    
    with Klass.docstring_linker.switch_context(InnerKlass):
        assert 'href="test.Klass.html"' in flatten(Klass.docstring_linker.link_to('Klass', 'Klass'))
    
    assert 'href="#v"' in flatten(mod.docstring_linker.link_to('v', 'v'))
    
    with mod.docstring_linker.switch_context(InnerKlass):
        assert 'href="index.html#v"' in flatten(mod.docstring_linker.link_to('v', 'v'))

@pytest.mark.parametrize('linkercls', [linker._EpydocLinker])
def test_EpydocLinker_switch_context_is_reentrant(linkercls:Type[linker._EpydocLinker], capsys:CapSys) -> None:
    """
    We can nest several calls to switch_context(), and links will still be valid and warnings line will be correct.
    """
    
    mod = fromText('''
    "L{thing.notfound}"
    v=0
    class Klass:
        "L{thing.notfound}"
        ...
    ''', modname='test')
    
    Klass = mod.contents['Klass']
    assert isinstance(Klass, model.Class)
    
    for ob in mod.system.allobjects.values():
        epydoc2stan.ensure_parsed_docstring(ob)
    
    # patch with the linkercls
    mod._linker = linkercls(mod)
    Klass._linker = linkercls(Klass)

    with Klass.docstring_linker.switch_context(mod):
        assert 'href="#v"' in flatten(Klass.docstring_linker.link_to('v', 'v'))
        with Klass.docstring_linker.switch_context(Klass):
            assert 'href="index.html#v"' in flatten(Klass.docstring_linker.link_to('v', 'v'))
    
    assert capsys.readouterr().out == ''

    mod.parsed_docstring.to_stan(mod.docstring_linker) #type:ignore
    mod.parsed_docstring.get_summary().to_stan(mod.docstring_linker) # type:ignore

    warnings = ['test:2: Cannot find link target for "thing.notfound" (you can link to external docs with --intersphinx)']
    if linkercls is linker._EpydocLinker:
        warnings = warnings * 2
    assert capsys.readouterr().out.strip().splitlines() == warnings

    # This is wrong:
    Klass.parsed_docstring.to_stan(mod.docstring_linker) # type:ignore
    Klass.parsed_docstring.get_summary().to_stan(mod.docstring_linker) # type:ignore
    
    # Because the warnings will be reported on line 2
    warnings = ['test:2: Cannot find link target for "thing.notfound" (you can link to external docs with --intersphinx)']
    warnings = warnings * 2
    
    assert capsys.readouterr().out.strip().splitlines() == warnings

    # assert capsys.readouterr().out == ''

    # Reset stan and summary, because they are supposed to be cached.
    Klass.parsed_docstring._stan = None # type:ignore
    Klass.parsed_docstring._summary = None # type:ignore

    # This is better:
    with mod.docstring_linker.switch_context(Klass):
        Klass.parsed_docstring.to_stan(mod.docstring_linker) # type:ignore
        Klass.parsed_docstring.get_summary().to_stan(mod.docstring_linker) # type:ignore

    warnings = ['test:5: Cannot find link target for "thing.notfound" (you can link to external docs with --intersphinx)']
    warnings = warnings * 2
    
    assert capsys.readouterr().out.strip().splitlines() == warnings
    
def test_EpydocLinker_look_for_intersphinx_no_link() -> None:
    """
    Return None if inventory had no link for our markup.
    """
    system = model.System()
    target = model.Module(system, 'ignore-name')
    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)

    result = sut.look_for_intersphinx('base.module')

    assert None is result


def test_EpydocLinker_look_for_intersphinx_hit() -> None:
    """
    Return the link from inventory based on first package name.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)

    result = sut.look_for_intersphinx('base.module.other')

    assert 'http://tm.tld/some.html' == result

def test_EpydocLinker_adds_intersphinx_link_css_class() -> None:
    """
    The EpydocLinker return a link with the CSS class 'intersphinx-link' when it's using intersphinx.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)

    result1 = sut.link_xref('base.module.other', 'base.module.other', 0).children[0] # wrapped in a code tag
    result2 = sut.link_to('base.module.other', 'base.module.other')
    
    res = flatten(result2)
    assert flatten(result1) == res
    assert 'class="intersphinx-link"' in res

def test_EpydocLinker_resolve_identifier_xref_intersphinx_absolute_id() -> None:
    """
    Returns the link from Sphinx inventory based on a cross reference
    ID specified in absolute dotted path and with a custom pretty text for the
    URL.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)

    url = sut.link_to('base.module.other', 'o').attributes['href']
    url_xref = sut._resolve_identifier_xref('base.module.other', 0)

    assert "http://tm.tld/some.html" == url
    assert "http://tm.tld/some.html" == url_xref


def test_EpydocLinker_resolve_identifier_xref_intersphinx_relative_id() -> None:
    """
    Return the link from inventory using short names, by resolving them based
    on the imports done in the module.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['ext_package.ext_module'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    # Here we set up the target module as it would have this import.
    # from ext_package import ext_module
    ext_package = model.Module(system, 'ext_package')
    target.contents['ext_module'] = model.Module(
        system, 'ext_module', parent=ext_package)

    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)

    # This is called for the L{ext_module<Pretty Text>} markup.
    url = sut.link_to('ext_module', 'ext').attributes['href']
    url_xref = sut._resolve_identifier_xref('ext_module', 0)

    assert "http://tm.tld/some.html" == url
    assert "http://tm.tld/some.html" == url_xref


def test_EpydocLinker_resolve_identifier_xref_intersphinx_link_not_found(capsys: CapSys) -> None:
    """
    A message is sent to stdout when no link could be found for the reference,
    while returning the reference name without an A link tag.
    The message contains the full name under which the reference was resolved.
    FIXME: Use a proper logging system instead of capturing stdout. https://github.com/twisted/pydoctor/issues/112
    """
    system = model.System()
    target = model.Module(system, 'ignore-name')
    # Here we set up the target module as it would have this import.
    # from ext_package import ext_module
    ext_package = model.Module(system, 'ext_package')
    target.contents['ext_module'] = model.Module(
        system, 'ext_module', parent=ext_package)
    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)

    # This is called for the L{ext_module} markup.
    assert sut.link_to('ext_module', 'ext').tagName == ''
    assert not capsys.readouterr().out
    with raises(LookupError):
        sut._resolve_identifier_xref('ext_module', 0)

    captured = capsys.readouterr().out
    expected = (
        'ignore-name:???: Cannot find link target for "ext_package.ext_module", '
        'resolved from "ext_module" '
        '(you can link to external docs with --intersphinx)\n'
        )
    assert expected == captured


class InMemoryInventory:
    """
    A simple inventory implementation which has an in-memory API link mapping.
    """

    INVENTORY = {
        'socket.socket': 'https://docs.python.org/3/library/socket.html#socket.socket',
        }

    def getLink(self, name: str) -> Optional[str]:
        return self.INVENTORY.get(name)

def test_EpydocLinker_resolve_identifier_xref_order(capsys: CapSys) -> None:
    """
    Check that the best match is picked when there are multiple candidates.
    """

    mod = fromText('''
    class C:
        socket = None
    ''')
    mod.system.intersphinx = cast(SphinxInventory, InMemoryInventory())
    _linker = mod.docstring_linker
    assert isinstance(_linker, linker._EpydocLinker)

    url = _linker.link_to('socket.socket', 's').attributes['href']
    url_xref = _linker._resolve_identifier_xref('socket.socket', 0)

    assert 'https://docs.python.org/3/library/socket.html#socket.socket' == url
    assert 'https://docs.python.org/3/library/socket.html#socket.socket' == url_xref
    assert not capsys.readouterr().out


def test_EpydocLinker_resolve_identifier_xref_internal_full_name() -> None:
    """Link to an internal object referenced by its full name."""

    # Object we want to link to.
    int_mod = fromText('''
    class C:
        pass
    ''', modname='internal_module')
    system = int_mod.system

    # Dummy module that we want to link from.
    target = model.Module(system, 'ignore-name')
    sut = target.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)
    url = sut.link_to('internal_module.C','C').attributes['href']
    xref = sut._resolve_identifier_xref('internal_module.C', 0)

    assert "internal_module.C.html" == url
    assert int_mod.contents['C'] is xref

def test_EpydocLinker_None_context() -> None:
    """
    The linker will create URLs with only the anchor
    if we're lnking to an object on the same page. 
    
    Otherwise it will always use return a URL with a filename, this is used to generate the summaries.
    """
    mod = fromText('''
    base=1
    class someclass: ...
    ''', modname='module')
    sut = mod.docstring_linker
    assert isinstance(sut, linker._EpydocLinker)
    
    assert sut.page_url == mod.url == cast(linker._EpydocLinker,mod.contents['base'].docstring_linker).page_url
    
    with sut.switch_context(None):
        assert sut.page_url ==''
        
        assert sut.link_to('base','module.base').attributes['href']=='index.html#base'
        assert sut.link_to('base','module.base').children[0]=='module.base'
        
        assert sut.link_to('base','base').attributes['href']=='index.html#base'
        assert sut.link_to('base','base').children[0]=='base'
        
        assert sut.link_to('someclass','some random name').attributes['href']=='module.someclass.html'
        assert sut.link_to('someclass','some random name').children[0]=='some random name'

def test_EpydocLinker_warnings(capsys: CapSys) -> None:
    """
    Warnings should be reported only once per invalid name per line, 
    no matter the number of times we call summary2html() or docstring2html() or the order we call these functions.
    """
    src = '''
    """
    L{base} L{regular text <notfound>} L{notfound} 

    L{regular text <base>} L{B{look at the base} <base>} L{I{Important class} <notfound>}  L{notfound} 
    """
    base=1
    '''

    mod = fromText(src, modname='module')

    assert 'href="#base"' in docstring2html(mod)
    captured = capsys.readouterr().out

    # The rationale about xref warnings is to warn when the target cannot be found.

    assert captured == ('module:3: Cannot find link target for "notfound"'
                        '\nmodule:3: Cannot find link target for "notfound"'
                        '\nmodule:5: Cannot find link target for "notfound"'
                        '\nmodule:5: Cannot find link target for "notfound"\n')

    assert 'href="index.html#base"' in summary2html(mod)
    summary2html(mod)
    
    captured = capsys.readouterr().out

    # No warnings are logged when generating the summary.
    assert captured == ''

def test_AnnotationLinker_xref(capsys: CapSys) -> None:
    """
    Even if the annotation linker is not designed to resolve xref,
    it will still do the right thing by forwarding any xref requests to
    the initial object's linker.
    """

    mod = fromText('''
    class C:
        var="don't use annotation linker for xref!"
    ''')
    mod.system.intersphinx = cast(SphinxInventory, InMemoryInventory())
    _linker = linker._AnnotationLinker(mod.contents['C'])
    
    url = flatten(_linker.link_xref('socket.socket', 'socket', 0))
    assert 'https://docs.python.org/3/library/socket.html#socket.socket' in url
    assert not capsys.readouterr().out

    url = flatten(_linker.link_xref('var', 'var', 0))
    assert 'href="#var"' in url
    assert not capsys.readouterr().out

def test_xref_not_found_epytext(capsys: CapSys) -> None:
    """
    When a link in an epytext docstring cannot be resolved, the reference
    and the line number of the link should be reported.
    """

    mod = fromText('''
    """
    A test module.

    Link to limbo: L{NoSuchName}.
    """
    ''', modname='test')

    epydoc2stan.format_docstring(mod)

    captured = capsys.readouterr().out
    assert captured == 'test:5: Cannot find link target for "NoSuchName"\n'


def test_xref_not_found_restructured(capsys: CapSys) -> None:
    """
    When a link in an reStructedText docstring cannot be resolved, the reference
    and the line number of the link should be reported.
    """

    system = model.System()
    system.options.docformat = 'restructuredtext'
    mod = fromText('''
    """
    A test module.

    Link to limbo: `NoSuchName`.
    """
    ''', modname='test', system=system)

    epydoc2stan.format_docstring(mod)

    captured = capsys.readouterr().out
    assert captured == 'test:5: Cannot find link target for "NoSuchName"\n'

def test_xref_not_found_restructured_in_para(capsys: CapSys) -> None:
    """
    When an invalid link is in the middle of a paragraph, we still report the right line number.
    """
    system = model.System()
    system.options.docformat = 'restructuredtext'
    mod = fromText('''
    """
    A test module.

    blabla bla blabla bla blabla bla blabla bla
    blabla blablabla blablabla blablabla blablabla bla blabla bla
    blabla blablabla blablabla blablabla blablabla bla
    Link to limbo: `NoSuchName`.
    """
    ''', modname='test', system=system)

    epydoc2stan.format_docstring(mod)
    captured = capsys.readouterr().out
    assert captured == 'test:8: Cannot find link target for "NoSuchName"\n'

    system = model.System()
    system.options.docformat = 'restructuredtext'
    mod = fromText('''
    """
    A test module.

    blabla bla blabla bla blabla bla blabla bla
    blabla blablabla blablabla blablabla blablabla bla blabla bla
    blabla blablabla blablabla blablabla blablabla bla
    Link to limbo: `NoSuchName`.  blabla bla blabla bla blabla bla blabla bla
    blabla blablabla blablabla blablabla blablabla bla blabla bla
    blabla blablabla blablabla blablabla blablabla bla
    """
    ''', modname='test', system=system)

    epydoc2stan.format_docstring(mod)
    captured = capsys.readouterr().out
    assert captured == 'test:8: Cannot find link target for "NoSuchName"\n'

class RecordingAnnotationLinker(NotFoundLinker):
    """A DocstringLinker implementation that cannot find any links,
    but does record which identifiers it was asked to link.
    """

    def __init__(self) -> None:
        self.requests: List[str] = []

    def link_to(self, target: str, label: "Flattenable") -> Tag:
        self.requests.append(target)
        return tags.transparent(label)

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
        assert False

@mark.parametrize('annotation', (
    '<bool>',
    '<NotImplemented>',
    '<typing.Iterable>[<int>]',
    '<Literal>[<True>]',
    '<Mapping>[<str>, <C>]',
    '<Tuple>[<a.b.C>, <int>]',
    '<Tuple>[<a.b.C>, ...]',
    '<Callable>[[<str>, <bool>], <None>]',
    ))
def test_annotation_formatting(annotation: str) -> None:
    """
    Perform two checks on the annotation formatting:

        - all type names in the annotation are passed to the linker
        - the plain text version of the output matches the input

    @note: The annotation formatting is now handled by L{PyvalColorizer}. We use the function C{flatten_text} in order
        to back reproduce the original text annotations. 
    """

    expected_lookups = [found[1:-1] for found in re.findall('<[^>]*>', annotation)]
    expected_text = annotation.replace('<', '').replace('>', '')

    mod = fromText(f'''
    value: {expected_text}
    ''')
    obj = mod.contents['value']
    parsed = epydoc2stan.get_parsed_type(obj)
    assert parsed is not None
    linker = RecordingAnnotationLinker()
    stan = parsed.to_stan(linker)
    assert linker.requests == expected_lookups

    html = flatten(stan)
    assert html.startswith('<code>')
    assert html.endswith('</code>')

    text = flatten_text(stan)
    assert text == expected_text

def test_module_docformat(capsys: CapSys) -> None:
    """
    Test if Module.docformat effectively override System.options.docformat
    """

    system = model.System()
    system.options.docformat = 'epytext'

    mod = fromText('''
    """
    Link to pydoctor: `pydoctor <https://github.com/twisted/pydoctor>`_.
    """
    __docformat__ = "google"
    ''', modname='test_epy', system=system)

    epytext_output = epydoc2stan.format_docstring(mod)

    captured = capsys.readouterr().out
    assert not captured

    mod = fromText('''
    """
    Link to pydoctor: `pydoctor <https://github.com/twisted/pydoctor>`_.
    """
    __docformat__ = "restructuredtext en"
    ''', modname='test_rst', system=system)

    restructuredtext_output = epydoc2stan.format_docstring(mod)

    captured = capsys.readouterr().out
    assert not captured

    assert ('href="https://github.com/twisted/pydoctor"' in flatten(epytext_output))
    assert ('href="https://github.com/twisted/pydoctor"' in flatten(restructuredtext_output))

def test_module_docformat_inheritence(capsys: CapSys) -> None:
    top_src = '''
    def f(a: str, b: int): 
        """
        :param a: string
        :param b: integer
        """
        pass
    '''
    mod_src = '''
    def f(a: str, b: int): 
        """
        @param a: string
        @param b: integer
        """
        pass
    '''
    pkg_src = '''
    __docformat__ = 'epytext'
    '''

    system = model.System()
    system.options.docformat = 'restructuredtext'
    top = fromText(top_src, modname='top', is_package=True, system=system)
    fromText(pkg_src, modname='pkg', parent_name='top', is_package=True,
                   system=system)
    mod = fromText(mod_src, modname='top.pkg.mod', parent_name='top.pkg', system=system)
    
    captured = capsys.readouterr().out
    assert not captured

    assert ''.join(docstring2html(top.contents['f']).splitlines()) == ''.join(docstring2html(mod.contents['f']).splitlines())
    

def test_module_docformat_with_docstring_inheritence(capsys: CapSys) -> None:

    mod_src = '''
    __docformat__ = "restructuredtext"

    class A:
        def f(self, a: str, b: int): 
            """
            .. note:: Note.
            """
    '''

    mod2_src = '''
    from mod import A
    __docformat__ = "epytext"

    class B(A):
        def f(self, a: str, b: int): 
            pass
    '''

    system = model.System()
    system.options.docformat = 'epytext'

    mod = fromText(mod_src, modname='mod', system=system)
    mod2 = fromText(mod2_src, modname='mod2', system=system)
    
    captured = capsys.readouterr().out
    assert not captured

    B_f = mod2.resolveName('B.f')
    A_f = mod.resolveName('A.f')

    assert B_f
    assert A_f

    assert ''.join(docstring2html(B_f).splitlines()) == ''.join(docstring2html(A_f).splitlines())

def test_cli_docformat_plaintext_overrides_module_docformat(capsys: CapSys) -> None:
    """
    When System.options.docformat is set to C{plaintext} it
    overwrites any specific Module.docformat defined for a module.
    
    See https://github.com/twisted/pydoctor/issues/503 for the reason
    of this behavior.
    """

    system = model.System()
    system.options.docformat = 'plaintext'

    mod = fromText('''
    """
    L{unknown} link.
    """
    __docformat__ = "epytext"
    ''', system=system)

    epytext_output = epydoc2stan.format_docstring(mod)

    captured = capsys.readouterr().out
    assert not captured

    assert flatten(epytext_output).startswith('<div><p class="pre">')

def test_constant_values_rst(capsys: CapSys) -> None:
    """
    Test epydoc2stan.format_constant_value().
    """
    mod1 = '''
    def f(a, b): 
        pass
    '''
    mod2 = '''
    from .mod1 import f

    CONST = (f,)
    '''

    system = model.System()
    system.options.docformat = 'restructuredtext'

    fromText("", modname='pack', system=system, is_package=True)
    fromText(mod1, modname='mod1', system=system, parent_name='pack')
    mod = fromText(mod2, modname='mod2', system=system, parent_name='pack')
    
    captured = capsys.readouterr().out
    assert not captured

    expected = ('<table class="valueTable"><tr class="fieldStart">'
                '<td class="fieldName">Value</td></tr><tr><td>'
                '<pre class="constant-value"><code>(<wbr></wbr>'
                '<a href="pack.mod1.html#f" class="internal-link" title="pack.mod1.f">f</a>)</code></pre></td></tr></table>')
    
    attr = mod.contents['CONST']
    assert isinstance(attr, model.Attribute)

    docstring2html(attr)

    assert ''.join(flatten(epydoc2stan.format_constant_value(attr)).splitlines()) == expected

    
def test_warns_field(capsys: CapSys) -> None:
    """Test if the :warns: field is correctly recognized."""
    mod = fromText('''
    def func():
        """
        @warns: If there is an issue.
        """
        pass
    ''')
    html = ''.join(docstring2html(mod.contents['func']).splitlines())
    assert ('<div><table class="fieldTable"><tr class="fieldStart">'
            '<td class="fieldName" colspan="2">Warns</td></tr><tr>'
            '<td colspan="2">If there is an issue.</td></tr></table></div>') == html
    captured = capsys.readouterr().out
    assert captured == ''

    mod = fromText('''
    def func():
        """
        @warns RuntimeWarning: If there is an issue.
        """
        pass
    ''')
    html = ''.join(docstring2html(mod.contents['func']).splitlines())
    assert ('<div><table class="fieldTable"><tr class="fieldStart">'
            '<td class="fieldName" colspan="2">Warns</td></tr><tr>'
            '<td class="fieldArgContainer">RuntimeWarning</td>'
            '<td class="fieldArgDesc">If there is an issue.</td></tr></table></div>') == html
    captured = capsys.readouterr().out
    assert captured == ''

def test_yields_field(capsys: CapSys) -> None:
    """Test if the :warns: field is correctly recognized."""
    mod = fromText('''
    def func():
        """
        @yields: Each member of the sequence.
        @ytype: str
        """
        pass
    ''')
    html = ''.join(docstring2html(mod.contents['func']).splitlines())
    assert html == ('<div><table class="fieldTable"><tr class="fieldStart">'
                    '<td class="fieldName" colspan="2">Yields</td></tr><tr>'
                    '<td class="fieldArgContainer">str</td>'
                    '<td class="fieldArgDesc">Each member of the sequence.'
                    '</td></tr></table></div>')
    captured = capsys.readouterr().out
    assert captured == ''

def insert_break_points(t:str) -> str:
    return flatten(epydoc2stan.insert_break_points(t))

def test_insert_break_points_identity() -> None:
    """
    No break points are introduced for values containing a single world.
    """
    assert insert_break_points('test') == 'test'
    assert insert_break_points('_test') == '_test'
    assert insert_break_points('_test_') == '_test_'
    assert insert_break_points('') == ''
    assert insert_break_points('____') == '____'
    assert insert_break_points('__test__') == '__test__'
    assert insert_break_points('__someverylongname__') == '__someverylongname__'
    assert insert_break_points('__SOMEVERYLONGNAME__') == '__SOMEVERYLONGNAME__'

def test_insert_break_points_snake_case() -> None:
    assert insert_break_points('__some_very_long_name__') == '__some<wbr></wbr>_very<wbr></wbr>_long<wbr></wbr>_name__'
    assert insert_break_points('__SOME_VERY_LONG_NAME__') == '__SOME<wbr></wbr>_VERY<wbr></wbr>_LONG<wbr></wbr>_NAME__'

def test_insert_break_points_camel_case() -> None:
    assert insert_break_points('__someVeryLongName__') == '__some<wbr></wbr>Very<wbr></wbr>Long<wbr></wbr>Name__'
    assert insert_break_points('__einÜberlangerName__') == '__ein<wbr></wbr>Überlanger<wbr></wbr>Name__'

def test_insert_break_points_dotted_name() -> None:
    assert insert_break_points('mod.__some_very_long_name__') == 'mod<wbr></wbr>.__some<wbr></wbr>_very<wbr></wbr>_long<wbr></wbr>_name__'
    assert insert_break_points('_mod.__SOME_VERY_LONG_NAME__') == '_mod<wbr></wbr>.__SOME<wbr></wbr>_VERY<wbr></wbr>_LONG<wbr></wbr>_NAME__'
    assert insert_break_points('pack.mod.__someVeryLongName__') == 'pack<wbr></wbr>.mod<wbr></wbr>.__some<wbr></wbr>Very<wbr></wbr>Long<wbr></wbr>Name__'
    assert insert_break_points('pack._mod_.__einÜberlangerName__') == 'pack<wbr></wbr>._mod_<wbr></wbr>.__ein<wbr></wbr>Überlanger<wbr></wbr>Name__'

def test_stem_identifier() -> None:
    assert list(stem_identifier('__some_very_long_name__')) == list(stem_identifier('__some_very_very_long_name__')) == [
        'some', 'very', 'long', 'name',]
    
    assert list(stem_identifier('transitivity_maximum')) == [
        'transitivity', 'maximum',]
    
    assert list(stem_identifier('ForEach')) == [
        'For', 'Each',]

    assert list(stem_identifier('__someVeryLongName__')) == [
        'some', 'Very', 'Long', 'Name', ]
    
    assert list(stem_identifier('_name')) == ['name']
    assert list(stem_identifier('name')) == ['name']
    assert list(stem_identifier('processModuleAST')) == ['process', 'Module', 'AST']

def test_self_cls_in_function_params(capsys: CapSys) -> None:
    """
    'self' and 'cls' in parameter table of regular function should appear because 
    we don't know if it's a badly named argument OR it's actually assigned to a legit
    class/instance method outside of the class scope: https://github.com/twisted/pydoctor/issues/13

    Until issue #13 is fixed (which is not so easy), the safe side is to show them.
    """
    src = '''
    __docformat__ = "google"

    def foo(cls, var, bar):
        """
        'cls' SHOULD shown in parameter table. 

        Args:
            var: the thing
            bar: the other thing
        """

    def bar(self, cls, var):
        """
        'self' SHOULD shown in parameter table. 

        Args:
            var: the thing
        """

    class Spectator:
        
        @staticmethod
        def watch(self, what):
            """
            'self' SHOULD shown in parameter table. 

            Args:
                what: the thing
            """
        
        def leave(cls, t):
            """
            'cls' SHOULD shown in parameter table. 

            Args:
                t: thing
            """
        
        @classmethod
        def which(cls, t):
            """
            'cls' SHOULD NOT shown in parameter table, because it's a legit class method.

            Args:
                t: the object
            """
        
        def __init__(self, team):
            """
            'self' SHOULD NOT shown in parameter table, because it's a legit instance method.

            Args:
                team: the team
            """
        
        def __bool__(self, other):
            """
            'self' SHOULD shown in parameter table, because it's explicitely documented.

            Args:
                self: the self
                other: the other
            """
    '''
    mod = fromText(src, modname='mod')

    html_foo = docstring2html(mod.contents['foo'])
    html_bar = docstring2html(mod.contents['bar'])
    html_watch = docstring2html(mod.contents['Spectator'].contents['watch'])
    html_leave = docstring2html(mod.contents['Spectator'].contents['leave'])
    html_which = docstring2html(mod.contents['Spectator'].contents['which'])
    html_init = docstring2html(mod.contents['Spectator'].contents['__init__'])
    html_bool = docstring2html(mod.contents['Spectator'].contents['__bool__'])

    assert not capsys.readouterr().out

    assert '<span class="fieldArg">cls</span>' in html_foo
    assert '<span class="fieldArg">self</span>' in html_bar
    assert '<span class="fieldArg">self</span>' in html_watch
    assert '<span class="fieldArg">cls</span>' in html_leave

    assert '<span class="fieldArg">cls</span>' not in html_which
    assert '<span class="fieldArg">self</span>' not in html_init
    assert '<span class="fieldArg">self</span>' in html_bool


# tests for issue https://github.com/twisted/pydoctor/issues/661
def test_dup_names_resolves_function_signature() -> None:
    """
    Annotations should always be resolved in the context of the module scope.
    
    For function signature, it's handled by having a special value formatter class for annotations. 
    For the parameter table it's handled by the field handler.

    Annotation are currently rendered twice, which is suboptimal and can cause inconsistencies.
    """

    src = '''\
    class System:
        dup = Union[str, bytes]
        default = 3
        def Attribute(self, t:'dup'=default) -> Type['Attribute']:
            """
            @param t: do not confuse with L{the class level one <dup>}.
            @returns: stuff
            """
        
    Attribute = 'thing'
    dup = Union[str, bytes] # yes this one
    default = 'not this one'
    '''

    mod = fromText(src, modname='model')

    def_Attribute = mod.contents['System'].contents['Attribute']
    assert isinstance(def_Attribute, model.Function)

    sig = flatten(format_signature(def_Attribute))
    assert 'href="index.html#Attribute"' in sig
    assert 'href="index.html#dup"' in sig
    assert 'href="#default"' in sig
    
    docstr = docstring2html(def_Attribute)
    assert '<a href="index.html#dup" class="internal-link" title="model.dup">dup</a>' in docstr
    assert '<a href="#dup" class="internal-link" title="model.System.dup">the class level one</a>' in docstr
    assert 'href="index.html#Attribute"' in docstr

def test_dup_names_resolves_annotation() -> None:
    """
    Annotations should always be resolved in the context of the module scope.

    PEP-563 says: Annotations can only use names present in the module scope as 
        postponed evaluation using local names is not reliable.

    For Attributes, this is handled by the type2stan() function, because name linking is 
        done at the stan tree generation step.
    """

    src = '''\
    class System:
        Attribute: typing.TypeAlias = 'str'
        class Inner:
            @property
            def Attribute(self) -> Type['Attribute']:...
        
    Attribute = Union[str, int]
    '''

    mod = fromText(src, modname='model')

    property_Attribute = mod.contents['System'].contents['Inner'].contents['Attribute']
    assert isinstance(property_Attribute, model.Attribute)
    stan = epydoc2stan.type2stan(property_Attribute)
    assert stan is not None
    assert 'href="index.html#Attribute"' in flatten(stan)

    src = '''\
    class System:
        Attribute: Type['Attribute']
        
    Attribute = Union[str, int]
    '''

    mod = fromText(src, modname='model')

    property_Attribute = mod.contents['System'].contents['Attribute']
    assert isinstance(property_Attribute, model.Attribute)
    stan = epydoc2stan.type2stan(property_Attribute)
    assert stan is not None
    assert 'href="index.html#Attribute"' in flatten(stan)

# tests for issue https://github.com/twisted/pydoctor/issues/662
def test_dup_names_resolves_base_class() -> None:
    """
    The class signature does not get confused when duplicate names are used.
    """

    src1 = '''\
    from model import System, Generic
    class System(System):
        ...
    class Generic(Generic[object]):
        ...
    '''
    src2 = '''\

    class System:
        ...
    class Generic:
        ...    
    '''
    system = model.System()
    builder = system.systemBuilder(system)
    builder.addModuleString(src1, modname='custom')
    builder.addModuleString(src2, modname='model')
    builder.buildModules()

    custommod,_ = system.rootobjects

    systemClass = custommod.contents['System']
    genericClass = custommod.contents['Generic']

    assert isinstance(systemClass, model.Class) and isinstance(genericClass, model.Class)

    assert 'href="model.System.html"' in flatten(format_class_signature(systemClass))
    assert 'href="model.Generic.html"' in flatten(format_class_signature(genericClass))

def test_class_level_type_alias() -> None:
    src = '''
    class C:
        typ = int|str
        def f(self, x:typ) -> typ:
            ...
        var: typ
    '''
    mod = fromText(src, modname='m')
    C = mod.system.allobjects['m.C']
    f = mod.system.allobjects['m.C.f']
    var = mod.system.allobjects['m.C.var']

    assert C.isNameDefined('typ')

    assert isinstance(f, model.Function)
    assert f.signature
    assert "href" in repr(f.signature.parameters['x'].annotation)
    assert "href" in repr(f.signature.return_annotation)

    assert isinstance(var, model.Attribute)
    assert "href" in flatten(epydoc2stan.type2stan(var) or '')

def test_top_level_type_alias_wins_over_class_level(capsys:CapSys) -> None:
    """
    Pydoctor resolves annotations like pyright when 
    "from __future__ import annotations" is enable, even if 
    it's not actually enabled.
    """
    
    src = '''
    typ = str|bytes # <- this IS the one
    class C:
        typ = int|str # <- This is NOT the one.
        def f(self, x:typ) -> typ:
            ...
        var: typ
    '''
    system = model.System()
    system.options.verbosity = 1
    mod = fromText(src, modname='m', system=system)
    f = mod.system.allobjects['m.C.f']
    var = mod.system.allobjects['m.C.var']

    assert isinstance(f, model.Function)
    assert f.signature
    assert 'href="index.html#typ"' in repr(f.signature.parameters['x'].annotation)
    assert 'href="index.html#typ"' in repr(f.signature.return_annotation)

    assert isinstance(var, model.Attribute)
    assert 'href="index.html#typ"' in flatten(epydoc2stan.type2stan(var) or '')

    assert capsys.readouterr().out == """\
m:5: ambiguous annotation 'typ', could be interpreted as 'm.C.typ' instead of 'm.typ'
m:5: ambiguous annotation 'typ', could be interpreted as 'm.C.typ' instead of 'm.typ'
m:7: ambiguous annotation 'typ', could be interpreted as 'm.C.typ' instead of 'm.typ'
"""

def test_not_found_annotation_does_not_create_link() -> None:
    """
    The docstring linker cache does not create empty <a> tags.
    """

    
    from pydoctor.test.test_templatewriter import getHTMLOf

    src = '''\
    __docformat__ = 'numpy'

    def link_to(identifier, label: NotFound):
        """
        :param label: the lable of the link.
        :type identifier: Union[str, NotFound]
        """

    '''

    mod = fromText(src)

    html = getHTMLOf(mod)

    assert '<a>NotFound</a>' not in html


def test_docformat_skip_processtypes() -> None:
    assert all([d in get_supported_docformats() for d in epydoc2stan._docformat_skip_processtypes])

def test_returns_undocumented_still_show_up_if_params_documented() -> None:
    """
    The returns section will show up if any of the 
    parameter are documented and the fucntion has a return annotation.
    """
    src = '''
    def f(c:int) -> bool:
        """
        @param c: stuff
        """
    def g(c) -> bool:
        """
        @type c: int
        """
    def h(c):
        """
        @param c: stuff
        """
    def i(c) -> None:
        """
        @param c: stuff
        """
    '''

    mod = fromText(src)

    html_f = docstring2html(mod.contents['f'])
    html_g = docstring2html(mod.contents['g'])
    html_h = docstring2html(mod.contents['h'])
    html_i = docstring2html(mod.contents['i'])

    assert 'Returns</td>' in html_f
    assert 'Returns</td>' in html_g

    assert 'Returns</td>' not in html_h
    assert 'Returns</td>' not in html_i

def test_invalid_epytext_renders_as_plaintext(capsys: CapSys) -> None:
    """
    An invalid epytext docstring will be rederered as plaintext.
    """

    mod = fromText(''' 
    def func():
        """
            Title
            ~~~~~
            

            Hello
            ~~~~~
        """
        pass
    
    ''', modname='invalid')

    expected = """<div>
<p class="pre">Title
~~~~~


Hello
~~~~~</p>
</div>"""
    
    actual = docstring2html(mod.contents['func'])
    captured = capsys.readouterr().out
    assert captured == ('invalid:4: bad docstring: Wrong underline character for heading.\n'
                        'invalid:8: bad docstring: Wrong underline character for heading.\n')
    assert actual  == expected

    assert docstring2html(mod.contents['func'], docformat='plaintext') == expected
    captured = capsys.readouterr().out
    assert captured == ''

def test_parsed_names_partially_resolved_early() -> None:
    """
    Test for issue #295

    Annotations are first locally resolved when we reach the end of the module, 
    then again when we actually resolve the name when generating the stan for the annotation.
    """
    typing = '''\
    List = ClassVar = TypeVar = object()
    '''

    base = '''\
    import ast
    class Vis(ast.NodeVisitor):
        ...
    '''
    src = '''\
    from typing import List
    import typing as t

    from .base import Vis
    
    class Cls(Vis, t.Generic['_T']):
        """
        L{Cls}
        """
        clsvar:List[str]
        clsvar2:t.ClassVar[List[str]]

        def __init__(self, a:'_T'):
            self._a:'_T' = a
    
    C = Cls
    _T = t.TypeVar('_T')
    unknow: i|None|list
    ann:Cls
    '''

    top = '''\
    # the order matters here
    from .src import C, Cls, Vis
    __all__ = ['Cls', 'C', 'Vis']
    '''

    system = model.System()
    builder = system.systemBuilder(system)
    builder.addModuleString(top, 'top', is_package=True)
    builder.addModuleString(base, 'base', 'top')
    builder.addModuleString(src, 'src', 'top')
    builder.addModuleString(typing, 'typing')
    builder.buildModules()

    Cls = system.allobjects['top.Cls']
    clsvar = Cls.contents['clsvar']
    clsvar2 = Cls.contents['clsvar2']
    a = Cls.contents['_a']
    assert clsvar.expandName('typing.List')=='typing.List'
    assert '<obj_reference refuri="typing.List">' in clsvar.parsed_type.to_node().pformat()
    assert 'href="typing.html#List"' in flatten(clsvar.parsed_type.to_stan(clsvar.docstring_linker))
    assert 'href="typing.html#ClassVar"' in flatten(clsvar2.parsed_type.to_stan(clsvar2.docstring_linker))
    assert 'href="top.src.html#_T"' in flatten(a.parsed_type.to_stan(clsvar.docstring_linker))

    # the reparenting/alias issue
    ann = system.allobjects['top.src.ann']
    assert 'href="top.Cls.html"' in  flatten(ann.parsed_type.to_stan(ann.docstring_linker))
    assert 'href="top.Cls.html"' in flatten(Cls.parsed_docstring.to_stan(Cls.docstring_linker))
    
    unknow = system.allobjects['top.src.unknow']
    assert flatten_text(unknow.parsed_type.to_stan(unknow.docstring_linker)) == 'i|None|list'

    

    # TODO: test the __init__ signature and the class bases

    # TODO: Fix two new twisted warnings:
    # twisted/internet/_sslverify.py:330: Cannot find link target for "twisted.internet.ssl.DN", resolved from "twisted.internet._sslverify.DistinguishedName"
    # twisted/internet/_sslverify.py:347: Cannot find link target for "twisted.internet.ssl.DN", resolved from "twisted.internet._sslverify.DistinguishedName"