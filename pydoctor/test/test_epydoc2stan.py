from pytest import raises

from pydoctor import epydoc2stan, model
from pydoctor.epydoc.markup import flatten
from pydoctor.sphinx import SphinxInventory
from pydoctor.test.test_astbuilder import fromText


def test_multiple_types():
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

def docstring2html(docstring: model.Documentable) -> str:
    stan = epydoc2stan.format_docstring(docstring)
    return flatten(stan).replace('><', '>\n<')

def test_func_arg_and_ret_annotation():
    annotation_mod = fromText('''
    def f(a: List[str]) -> bool:
        """
        @param a: an arg, a the best of args
        @return: the best that we can do
        """
    ''')
    classic_mod = fromText('''
    def f(a):
        """
        @param a: an arg, a the best of args
        @type a: List[str]
        @return: the best that we can do
        @rtype: bool
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert annotation_fmt == classic_fmt

def test_func_arg_and_ret_annotation_with_override():
    annotation_mod = fromText('''
    def f(a: List[str], b: List[str]) -> bool:
        """
        @param a: an arg, a the best of args
        @param b: a param to follow a
        @type b: List[awesome]
        @return: the best that we can do
        """
    ''')
    classic_mod = fromText('''
    def f(a):
        """
        @param a: an arg, a the best of args
        @type a: List[str]
        @param b: a param to follow a
        @type b: List[awesome]
        @return: the best that we can do
        @rtype: bool
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert annotation_fmt == classic_fmt

def test_func_arg_when_doc_missing():
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
        @type a: List[str]
        @type b: int
        @rtype: bool
        """
    ''')
    annotation_fmt = docstring2html(annotation_mod.contents['f'])
    classic_fmt = docstring2html(classic_mod.contents['f'])
    assert annotation_fmt == classic_fmt


def test_func_missing_param_name(capsys):
    """Param and type fields must include the name of the parameter."""
    mod = fromText('''
    def f(a, b):
        """
        @param a: The first parameter.
        @param: The other one.
        @type: L{str}
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    captured = capsys.readouterr().out
    assert captured == (
        '<test>:5: Parameter name missing\n'
        '<test>:6: Parameter name missing\n'
        )


def test_func_missing_exception_type(capsys):
    """Raise fields must include the exception type."""
    mod = fromText('''
    def f(x):
        """
        @raise ValueError: If C{x} is rejected.
        @raise: On a blue moon.
        """
    ''')
    epydoc2stan.format_docstring(mod.contents['f'])
    captured = capsys.readouterr().out
    assert captured == '<test>:5: Exception type missing\n'


def test_func_starargs(capsys):
    """Var-args must be named in fields without asterixes.
    But for compatibility, we warn and strip off the asterixes.
    """
    bad_mod = fromText('''
    def f(*args: int, **kwargs) -> None:
        """
        Do something with var-positional and var-keyword arguments.

        @param *args: var-positional arguments
        @param **kwargs: var-keyword arguments
        @type **kwargs: L{str}
        """
    ''', modname='<bad>')
    good_mod = fromText('''
    def f(*args: int, **kwargs) -> None:
        """
        Do something with var-positional and var-keyword arguments.

        @param args: var-positional arguments
        @param kwargs: var-keyword arguments
        @type kwargs: L{str}
        """
    ''', modname='<good>')
    bad_fmt = docstring2html(bad_mod.contents['f'])
    good_fmt = docstring2html(good_mod.contents['f'])
    assert bad_fmt == good_fmt
    captured = capsys.readouterr().out
    assert captured == (
        '<bad>:6: Parameter name "*args" should not include asterixes\n'
        '<bad>:7: Parameter name "**kwargs" should not include asterixes\n'
        '<bad>:8: Parameter name "**kwargs" should not include asterixes\n'
        )


def test_summary():
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
    def get_summary(func):
        stan = epydoc2stan.format_summary(mod.contents[func])
        assert stan.tagName == 'span', stan
        return flatten(stan.children)
    assert 'Lorem Ipsum' == get_summary('single_line_summary')
    assert 'Foo Bar Baz' == get_summary('three_lines_summary')
    assert 'No summary' == get_summary('no_summary')


def test_missing_field_name(capsys):
    fromText('''
    """
    A test module.

    @ivar: Mystery variable.
    @type: str
    """
    ''', modname='test')
    captured = capsys.readouterr().out
    assert captured == "test:5: Missing field name in @ivar\n" \
                       "test:6: Missing field name in @type\n"


def test_unknown_field_name(capsys):
    mod = fromText('''
    """
    A test module.

    @zap: No such field.
    """
    ''', modname='test')
    epydoc2stan.format_docstring(mod)
    captured = capsys.readouterr().out
    assert captured == 'test:5: unknown field "zap"\n'


def test_EpydocLinker_look_for_intersphinx_no_link():
    """
    Return None if inventory had no link for our markup.
    """
    system = model.System()
    target = model.Module(system, 'ignore-name')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.look_for_intersphinx('base.module')

    assert None is result


def test_EpydocLinker_look_for_intersphinx_hit():
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


def test_EpydocLinker_resolve_identifier_xref_intersphinx_absolute_id():
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

    url = sut.resolve_identifier_xref('base.module.other')

    assert "http://tm.tld/some.html" == url


def test_EpydocLinker_resolve_identifier_xref_intersphinx_relative_id():
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
    url = sut.resolve_identifier_xref('ext_module')

    assert "http://tm.tld/some.html" == url


def test_EpydocLinker_resolve_identifier_xref_intersphinx_link_not_found(capsys):
    """
    A message is sent to stdout when no link could be found for the reference,
    while returning the reference name without an A link tag.
    The message contains the full name under which the reference was resolved.
    FIXME: Use a proper logging system instead of capturing stdout.
           https://github.com/twisted/pydoctor/issues/112
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
    with raises(LookupError):
        sut.resolve_identifier_xref('ext_module')

    captured = capsys.readouterr().out
    expected = (
        "ignore-name:???: invalid ref to 'ext_module' "
        "resolved as 'ext_package.ext_module'\n"
        )
    assert expected == captured


def test_EpydocLinker_resolve_identifier_xref_order(capsys):
    """
    Check that the best match is picked when there are multiple candidates.
    """

    mod = fromText('''
    class C:
        socket = None
    ''')
    linker = epydoc2stan._EpydocLinker(mod)

    url = linker.resolve_identifier_xref('socket.socket')

    assert epydoc2stan.STDLIB_URL + 'socket.html#socket.socket' == url
    assert not capsys.readouterr().out


def test_stdlib_doc_link_for_name():
    """
    Check the URLs returned for names from the standard library.
    """

    base = epydoc2stan.STDLIB_URL
    link = epydoc2stan.stdlib_doc_link_for_name
    assert base + 'exceptions.html#KeyError' == link('KeyError')
    assert base + 'stdtypes.html#str' == link('str')
    assert base + 'functions.html#len' == link('len')
    assert base + 'constants.html#None' == link('None')
    assert base + 'collections.html#collections.defaultdict' == link('collections.defaultdict')
    assert base + 'logging.handlers.html#logging.handlers.SocketHandler' == link('logging.handlers.SocketHandler')
