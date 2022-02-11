from typing import List, Optional, cast, TYPE_CHECKING
import re

from pytest import mark, raises
import pytest
from twisted.web.template import Tag, tags

from pydoctor import epydoc2stan, model
from pydoctor.epydoc.markup import DocstringLinker
from pydoctor.stanutils import flatten, flatten_text
from pydoctor.epydoc.markup.epytext import ParsedEpytextDocstring
from pydoctor.sphinx import SphinxInventory
from pydoctor.test.test_astbuilder import fromText, unwrap
from pydoctor.test import CapSys

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
    mod = fromText('''
    """Empty module."""
    ''')
    assert docstring2html(mod) == "<div>Empty module.</div>"


def test_xref_link_not_found() -> None:
    """A linked name that is not found is output as text."""
    mod = fromText('''
    """This link leads L{nowhere}."""
    ''', modname='test')
    html = docstring2html(mod)
    assert '<code>nowhere</code>' in html


def test_xref_link_same_page() -> None:
    """A linked name that is documented on the same page is linked using only
    a fragment as the URL.
    """
    mod = fromText('''
    """The home of L{local_func}."""

    def local_func():
        pass
    ''', modname='test')
    html = docstring2html(mod)
    assert 'href="#local_func"' in html


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
    annotation is not None, include the "Returns" entry in the output.
    """
    mod = fromText('''
    def get_answer() -> int:
        return 42
    ''')
    func = mod.contents['get_answer']
    lines = docstring2html(func).splitlines()
    expected_html = [
        '<div>', '<p class="undocumented">Undocumented</p>',
        '<table class="fieldTable">',
        '<tr class="fieldStart">',
        '<td class="fieldName" colspan="2">Returns</td>',
        '</tr>',
        '<tr>', '<td class="fieldArgContainer">', '<code>int</code>',
        '</td>',
        '<td class="fieldArgDesc">',
        '<span class="undocumented">Undocumented</span>',
        '</td>', '</tr>', '</table>', '</div>'
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

@pytest.mark.xfail
def test_func_arg_when_doc_missing() -> None:
    annotation_mod = fromText('''
    def f(a: List[str], b: int) -> bool:
        """
        Today I will not document details
        """
    ''')
    classic_mod = fromText('''
    def f(a):
        """
        Today I will not document details
        @type a: C{List[str]}
        @type b: C{int}
        @rtype: C{bool}
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert annotation_fmt == classic_fmt

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

def test_func_starargs_no_docstring(capsys: CapSys) -> None:
    """
    Star arguments, even if there are not docstring attached, will be rendered with stars.

    @note: This test might not pass anymore when we include the annotations inside the signatures.
    """

    mod = fromText('''
    def f(args:str, kwargs:str, *a:Any, **kwa:Any) -> None:
        """
        Do something with var-positional and var-keyword arguments.
        """
    ''', modname='<great>')

    mod_fmt = docstring2html(mod.contents['f'])
    
    expected_parts = ['<span class="fieldArg">args:</span>', 
                      '<span class="fieldArg">kwargs:</span>',
                      '<span class="fieldArg">*a:</span>',
                      '<span class="fieldArg">**kwa:</span>',]
    
    for part in expected_parts:
        assert part in mod_fmt, mod_fmt
    
    captured = capsys.readouterr().out
    assert not captured

def test_summary() -> None:
    mod = fromText('''
    def single_line_summary():
        """
        Lorem Ipsum

        Ipsum Lorem
        """
    def no_summary():
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
    assert 'No summary' == summary2html(mod.contents['no_summary'])


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
    assert docstring2html(sub_a) == "<div>sub doc</div>"
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


def test_EpydocLinker_look_for_intersphinx_no_link() -> None:
    """
    Return None if inventory had no link for our markup.
    """
    system = model.System()
    target = model.Module(system, 'ignore-name')
    sut = epydoc2stan._EpydocLinker(target)

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
    sut = epydoc2stan._EpydocLinker(target)

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
    sut = epydoc2stan._EpydocLinker(target)

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
    sut = epydoc2stan._EpydocLinker(target)

    url = sut.resolve_identifier('base.module.other')
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

    sut = epydoc2stan._EpydocLinker(target)

    # This is called for the L{ext_module<Pretty Text>} markup.
    url = sut.resolve_identifier('ext_module')
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
    sut = epydoc2stan._EpydocLinker(target)

    # This is called for the L{ext_module} markup.
    assert sut.resolve_identifier('ext_module') is None
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
    linker = epydoc2stan._EpydocLinker(mod)

    url = linker.resolve_identifier('socket.socket')
    url_xref = linker._resolve_identifier_xref('socket.socket', 0)

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
    sut = epydoc2stan._EpydocLinker(target)

    url = sut.resolve_identifier('internal_module.C')
    xref = sut._resolve_identifier_xref('internal_module.C', 0)

    assert "internal_module.C.html" == url
    assert int_mod.contents['C'] is xref


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
    However, currently the best we can do is report the starting line of the
    docstring instead.
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
    # TODO: Should actually be line 5, but I can't get docutils to fill in
    #       the line number when it calls visit_title_reference().
    #       https://github.com/twisted/pydoctor/issues/237
    assert captured == 'test:3: Cannot find link target for "NoSuchName"\n'


class RecordingAnnotationLinker(DocstringLinker):
    """A DocstringLinker implementation that cannot find any links,
    but does record which identifiers it was asked to link.
    """

    def __init__(self) -> None:
        self.requests: List[str] = []

    def link_to(self, target: str, label: "Flattenable") -> Tag:
        self.resolve_identifier(target)
        return tags.transparent(label)

    def link_xref(self, target: str, label: "Flattenable", lineno: int) -> Tag:
        assert False

    def resolve_identifier(self, identifier: str) -> Optional[str]:
        self.requests.append(identifier)
        return None

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
    system.options.docformat = 'plaintext'

    mod = fromText('''
    """
    Link to pydoctor: U{pydoctor <https://github.com/twisted/pydoctor>}.
    """
    __docformat__ = "epytext"
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

    assert ('Link to pydoctor: <a class="rst-reference external" href="https://github.com/twisted/pydoctor"'
        ' target="_top">pydoctor</a>' in flatten(epytext_output))
    
    assert ('Link to pydoctor: <a class="rst-reference external"'
        ' href="https://github.com/twisted/pydoctor" target="_top">pydoctor</a>' in flatten(restructuredtext_output))

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

def test_insert_break_points_identity() -> None:
    assert epydoc2stan.insert_break_points('test') == 'test'
    assert epydoc2stan.insert_break_points('__test__') == '__test__'
    assert epydoc2stan.insert_break_points('__someverylongname__') == '__someverylongname__'
    assert epydoc2stan.insert_break_points('__SOMEVERYLONGNAME__') == '__SOMEVERYLONGNAME__'

def test_insert_break_points_snake_case() -> None:
    assert epydoc2stan.insert_break_points('__some_very_long_name__') == '__some\u200b_very\u200b_long\u200b_name__'
    assert epydoc2stan.insert_break_points('__SOME_VERY_LONG_NAME__') == '__SOME\u200b_VERY\u200b_LONG\u200b_NAME__'

def test_insert_break_points_camel_case() -> None:
    assert epydoc2stan.insert_break_points('__someVeryLongName__') == '__some\u200bVery\u200bLong\u200bName__'
    assert epydoc2stan.insert_break_points('__einÜberlangerName__') == '__ein\u200bÜberlanger\u200bName__'
