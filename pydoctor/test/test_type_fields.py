from typing import Any, List
from textwrap import dedent
from pydoctor.epydoc.markup import ParseError, get_parser_by_name
from pydoctor.test.epydoc.test_restructuredtext import prettify
from pydoctor.test.test_templatewriter import getHTMLOfAttribute
from pydoctor.test import NotFoundLinker, CapSys
from pydoctor.test.epydoc import parse_docstring
from pydoctor.test.test_epydoc2stan import docstring2html
from pydoctor.test.test_astbuilder import fromText
from pydoctor.stanutils import flatten
from pydoctor.napoleon.docstring import TokenType
from pydoctor.epydoc.markup._types import ParsedTypeDocstring
import pydoctor.epydoc.markup
from pydoctor import model


def doc2html(doc: str, markup: str, processtypes: bool = False) -> str:
    return ''.join(prettify(flatten(parse_docstring(doc, markup, processtypes).to_stan(NotFoundLinker()))).splitlines())

def test_types_to_node_no_markup() -> None:
    cases = [   
            'rtype: list of int or float or None', 
            "rtype: {'F', 'C', 'N'}, default 'N'",
            "rtype: DataFrame, optional",
            "rtype: List[str] or list(bytes), optional",]

    for s in cases:
        assert doc2html(':'+s, 'restructuredtext', False) == doc2html('@'+s, 'epytext')
        assert doc2html(':'+s, 'restructuredtext', True) == doc2html('@'+s, 'epytext')

def test_to_node_markup() -> None:
    
    cases = [  ('L{me}', '`me`'),
            ('B{No!}', '**No!**'),
            ('I{here}', '*here*'),
            ('L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}', '`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`')
            ]

    for epystr, rststr in cases:
        assert doc2html(rststr, 'restructuredtext') == doc2html(epystr, 'epytext')

def typespec2htmlvianode(s: str, markup: str) -> str:
    err: List[ParseError] = []
    parsed_doc = get_parser_by_name(markup)(s, err)
    assert not err
    ann = ParsedTypeDocstring(parsed_doc.to_node(), warns_on_unknown_tokens=True)
    html = flatten(ann.to_stan(NotFoundLinker()))
    assert not ann.warnings
    return html

def typespec2htmlviastr(s: str) -> str:
    ann = ParsedTypeDocstring(s, warns_on_unknown_tokens=True)
    html = flatten(ann.to_stan(NotFoundLinker()))
    assert not ann.warnings
    return html

def test_parsed_type(subtests: Any) -> None:
    
    parsed_type_cases = [
        ('list of int or float or None', 
        '<span class="rst-literal"><a>list</a> of <a>int</a> or <a>float</a> or <a>None</a></span>'),

        ("{'F', 'C', 'N'}, default 'N'",
        """<span class="rst-literal"><span class="rst-variable-string">{'F', 'C', 'N'}</span>, <em>default</em> <span class="rst-variable-string">'N'</span></span>"""),

        ("DataFrame, optional",
        """<span class="rst-literal"><a>DataFrame</a>, <em>optional</em></span>"""),

        ("List[str] or list(bytes), optional", 
        """<span class="rst-literal"><a>List</a>[<a>str</a>] or <a>list</a>(<a>bytes</a>), <em>optional</em></span>"""),

        (('`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`', 'L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}'),
        '<span class="rst-literal"><a>complicated string</a> or <a>strIO</a></span>'),
    ]

    for string, excepted_html in parsed_type_cases:
        rst_string = ''
        epy_string = ''

        if isinstance(string, tuple):
            rst_string, epy_string = string
        elif isinstance(string, str):
            rst_string = epy_string = string

        with subtests.test('parse type', rst=rst_string, epy=epy_string):
        
            assert typespec2htmlviastr(rst_string) == excepted_html
            assert typespec2htmlvianode(rst_string, 'restructuredtext') == excepted_html            
            assert typespec2htmlvianode(epy_string, 'epytext') == excepted_html

def test_processtypes(capsys: CapSys) -> None:
    """
    Currently, numpy and google type parsing happens both at the string level with L{pydoctor.napoleon.docstring.TypeDocstring}
    and at the docutils nodes L{ParsedTypeDocstring} for type fields (``type`` and ``rtype``).
    """

    cases = [
        (
            (   
                """
                @param arg: A param.
                @type arg: list of int or float or None
                """,

                """
                :param arg: A param.
                :type arg: list of int or float or None
                """,

                """
                Args:
                    arg (list of int or float or None): A param.
                """,

                """
                Args
                ----
                arg: list of int or float or None
                    A param.
                """,
            ), 

                ("list of int or float or None", 
                '<span class="rst-literal"><a>list</a> of <a>int</a> or <a>float</a> or <a>None</a></span>')

        ),

        (
            (   
                """
                @param arg: A param.
                @type arg: L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}, optional
                """,

                """
                :param arg: A param.
                :type arg: `complicated string` or `strIO <twisted.python.compat.NativeStringIO>`, optional
                """,

                """
                Args:
                    arg (`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`, optional): A param.
                """,

                """
                Args
                ----
                arg: `complicated string` or `strIO <twisted.python.compat.NativeStringIO>`, optional
                    A param.
                """,
            ), 

                ("<code><a>complicated string</a></code> or <code><a>strIO</a></code>, optional", 
                '<span class="rst-literal"><a>complicated string</a> or <a>strIO</a>, <em>optional</em></span>')

        ),

    ]

    for strings, excepted_html in cases:
        epy_string, rst_string, goo_string, numpy_string = strings

        excepted_html_no_process_types, excepted_html_type_processed = excepted_html

        assert flatten(parse_docstring(epy_string, 'epytext').fields[-1].body().to_stan(NotFoundLinker())) == excepted_html_no_process_types
        assert flatten(parse_docstring(rst_string, 'restructuredtext').fields[-1].body().to_stan(NotFoundLinker())) == excepted_html_no_process_types

        assert flatten(parse_docstring(dedent(goo_string), 'google').fields[-1].body().to_stan(NotFoundLinker())) == excepted_html_type_processed
        assert flatten(parse_docstring(dedent(numpy_string), 'numpy').fields[-1].body().to_stan(NotFoundLinker())) == excepted_html_type_processed

        assert flatten(parse_docstring(epy_string, 'epytext', processtypes=True).fields[-1].body().to_stan(NotFoundLinker())) == excepted_html_type_processed
        assert flatten(parse_docstring(rst_string, 'restructuredtext', processtypes=True).fields[-1].body().to_stan(NotFoundLinker())) == excepted_html_type_processed

def test_processtypes_more() -> None:
    # Using numpy style-only because it suffice.
    cases = [
        ("""
              Yields
              ------
              working: bool
                  Whether it's working.
              not_working: bool
                  Whether it's not working.
              """, 
              """<ul class="rst-simple">
<li><strong>working</strong>: <code><a>bool</a></code> - Whether it's working.</li>
<li><strong>not_working</strong>: <code><a>bool</a></code> - Whether it's not working.</li>
</ul>"""), 

              ("""
               Returns
               -------
               name: str
                  the name description.
               content: str
                  the content description.
               """, 
               """<ul class="rst-simple">
<li><strong>name</strong>: <code><a>str</a></code> - the name description.</li>
<li><strong>content</strong>: <code><a>str</a></code> - the content description.</li>
</ul>"""),
              ]
    
    for string, excepted_html in cases:
        assert flatten(parse_docstring(dedent(string), 'numpy').fields[-1].body().to_stan(NotFoundLinker())).strip() == excepted_html

def test_processtypes_with_system(capsys: CapSys) -> None:
    system = model.System()
    system.options.processtypes = True
    
    mod = fromText('''
    a = None
    """
    Variable documented by inline docstring.
    @type: list of int or float or None
    """
    ''', modname='test', system=system)
    a = mod.contents['a']
    
    docstring2html(a)
    assert isinstance(a.parsed_type, ParsedTypeDocstring)
    fmt = flatten(a.parsed_type.to_stan(NotFoundLinker()))

    captured = capsys.readouterr().out
    assert not captured

    assert '<span class="rst-literal"><a>list</a> of <a>int</a> or <a>float</a> or <a>None</a></span>' == fmt
    

def test_processtypes_corner_cases(capsys: CapSys, subtests: Any) -> None:
    """
    The corner cases does not trigger any warnings because they are still valid types.
    
    Warnings should be triggered in L{pydoctor.napoleon.docstring.TypeDocstring._trigger_warnings}, 
    we should be careful with triggering warnings because whether the type spec triggers warnings is used
    to check is a string is a valid type or not.  
    """
    def _process(typestr: str) -> str:
        system = model.System()
        system.options.processtypes = True
        mod = fromText(f'''
        a = None
        """
        @type: {typestr}
        """
        ''', modname='test', system=system)
        a = mod.contents['a']
        docstring2html(a)

        assert isinstance(a.parsed_type, ParsedTypeDocstring)
        fmt = flatten(a.parsed_type.to_stan(NotFoundLinker()))
        assert fmt.startswith('<span class="rst-literal">')
        assert fmt.endswith('</span>')
        fmt = fmt[26:-7]
        
        captured = capsys.readouterr().out
        assert not captured

        return fmt

    def process(input:str, expected:str) -> None:
        with subtests.test(msg="processtypes", input=input):
            actual = _process(input)
            assert actual == expected

    process('default[str]',                       "<em>default</em>[<a>str</a>]")
    process('[str]',                              "[<a>str</a>]")
    process('[,]',                                "[, ]")
    process('[[]]',                               "[[]]")
    process(', [str]',                            ", [<a>str</a>]")
    process(' of [str]',                          "of[<a>str</a>]")
    process(' or [str]',                          "or[<a>str</a>]")
    process(': [str]',                            ': [<a>str</a>]')
    process("'hello'[str]",                      "<span class=\"rst-variable-string\">'hello'</span>[<a>str</a>]")
    process('"hello"[str]',                       "<span class=\"rst-variable-string\">\"hello\"</span>[<a>str</a>]")
    process('`hello`[str]',                       "<a>hello</a>[<a>str</a>]")
    process('`hello <https://github.com>`_[str]', """<a class="rst-external rst-reference" href="https://github.com" target="_top">hello</a>[<a>str</a>]""")
    process('**hello**[str]',                     "<strong>hello</strong>[<a>str</a>]")
    process('["hello" or str, default: 2]',       """[<span class="rst-variable-string">"hello"</span> or <a>str</a>, <em>default</em>: <span class="rst-variable-string">2</span>]""")

    # HTML ids for problematic elements changed in docutils 0.18.0, and again in 0.19.0, so we're not testing for the exact content anymore.
    with subtests.test(msg="processtypes", input='Union[`hello <>`_[str]]'):
        problematic = _process('Union[`hello <>`_[str]]')
        assert "`hello &lt;&gt;`_" in problematic
        assert "<a>str</a>" in problematic
 
def test_processtypes_warning_unexpected_element(capsys: CapSys) -> None:
    

    epy_string = """
    @param arg: A param.
    @type arg: L{complicated string} or 
        L{strIO <twisted.python.compat.NativeStringIO>}, optional
        
        >>> print('example')
    """

    rst_string = """
    :param arg: A param.
    :type arg: `complicated string` or 
        `strIO <twisted.python.compat.NativeStringIO>`, optional
        
        >>> print('example')
    """

    expected = """<span class="rst-literal"><a>complicated string</a> or <a>strIO</a>, <em>optional</em></span>"""
    
    # Test epytext
    epy_errors: List[ParseError] = []
    epy_parsed = pydoctor.epydoc.markup.processtypes(get_parser_by_name('epytext'))(epy_string, epy_errors)

    assert len(epy_errors)==1
    assert "Unexpected element in type specification field: element 'doctest_block'" in epy_errors.pop().descr()

    assert flatten(epy_parsed.fields[-1].body().to_stan(NotFoundLinker())).replace('\n', '') == expected
    
    # Test restructuredtext
    rst_errors: List[ParseError] = []
    rst_parsed = pydoctor.epydoc.markup.processtypes(get_parser_by_name('restructuredtext'))(rst_string, rst_errors)

    assert len(rst_errors)==1
    assert "Unexpected element in type specification field: element 'doctest_block'" in rst_errors.pop().descr()

    assert flatten(rst_parsed.fields[-1].body().to_stan(NotFoundLinker())).replace('\n', ' ') == expected

def test_napoleon_types_warnings(capsys: CapSys) -> None:
    """
    This is not the same as test_token_type_invalid() since 
    this checks our integration with pydoctor and validates we **actually** trigger 
    the warnings.
    """
    # from napoleon upstream:
    # unbalanced parenthesis in type expression
    # unbalanced square braces in type expression
    # invalid value set (missing closing brace)
    # invalid value set (missing opening brace)
    # malformed string literal (missing closing quote)
    # malformed string literal (missing opening quote)
    # from our custom napoleon:
    # invalid type: '{before_colon}'. Probably missing colon.
    # from our integration with docutils:
    # Unexpected element in type specification field

    src = '''
    __docformat__ = 'google'
    def foo(**args):
        """
        Keyword Args:
            a (list(str): thing
            b (liststr]): stuff
            c ({1,2,3): num
            d ('1',2,3}): num or str
            e (str, '1', '2): str
            f (str, "1", 2"): str
            docformat
                Can be one of:
                - "numpy"
                - "google"
            h: things
            k: stuff
        
        :type h: stuff

            >>> python
        
        :type k: a paragraph

            another one
        """
    '''

    mod = fromText(src, modname='warns')    
    docstring2html(mod.contents['foo'])

    # Filter docstring linker warnings
    lines = [line for line in capsys.readouterr().out.splitlines() if 'Cannot find link target' not in line]
    
    # Line numbers are off because they are based on the reStructuredText version of the docstring
    # which includes much more lines because of the :type arg: fields. 
    assert '\n'.join(lines) == '''\
warns:13: bad docstring: invalid type: 'docformatCan be one of'. Probably missing colon.
warns:7: bad docstring: unbalanced parenthesis in type expression
warns:9: bad docstring: unbalanced square braces in type expression
warns:11: bad docstring: invalid value set (missing closing brace): {1
warns:13: bad docstring: invalid value set (missing opening brace): 3}
warns:15: bad docstring: malformed string literal (missing closing quote): '2
warns:17: bad docstring: malformed string literal (missing opening quote): 2"
warns:24: bad docstring: Unexpected element in type specification field: element 'doctest_block'. This value should only contain text or inline markup.
warns:28: bad docstring: Unexpected element in type specification field: element 'paragraph'. This value should only contain text or inline markup.'''

def test_process_types_with_consolidated_fields(capsys: CapSys) -> None:
    """
    Test for issue https://github.com/twisted/pydoctor/issues/765
    """
    src = '''
    class V:
        """
        Doc. 

        :CVariables:
            `id` : int
                Classvar doc.
        """
    '''
    system = model.System()

    system.options.processtypes = True
    system.options.docformat = 'restructuredtext'

    mod = fromText(src, modname='do_not_warn_please', system=system)
    attr = mod.contents['V'].contents['id']
    assert isinstance(attr, model.Attribute)
    html = getHTMLOfAttribute(attr)
    # Filter docstring linker warnings
    lines = [line for line in capsys.readouterr().out.splitlines() if 'Cannot find link target' not in line]
    assert not lines
    assert '<span class="rst-literal">int</span>' in html
    