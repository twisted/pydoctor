from typing import List
from textwrap import dedent
from pydoctor.epydoc.markup import ParseError, get_parser_by_name
from pydoctor.test.epydoc.test_restructuredtext import prettify
from pydoctor.test import NotFoundLinker, CapSys
from pydoctor.test.epydoc import parse_docstring
from pydoctor.test.test_epydoc2stan import docstring2html
from pydoctor.test.test_astbuilder import fromText
from pydoctor.stanutils import flatten
from pydoctor.napoleon.docstring import TokenType
from pydoctor.epydoc.markup._types import ParsedTypeDocstring
from pydoctor import model
from twisted.web.template import Tag


def doc2html(doc: str, markup: str) -> str:
    return ''.join(prettify(flatten(parse_docstring(doc, markup).to_stan(NotFoundLinker()))).splitlines())

def test_types_to_node_no_markup() -> None:
    cases = [   
            'rtype: list of int or float or None', 
            "rtype: {'F', 'C', 'N'}, default 'N'",
            "rtype: DataFrame, optional",
            "rtype: List[str] or list(bytes), optional",]

    for s in cases:
        assert doc2html(':'+s, 'restructuredtext') == doc2html('@'+s, 'epytext')

def test_to_node_markup() -> None:
    
    cases = [  ('L{me}', '`me`'),
            ('B{No!}', '**No!**'),
            ('I{here}', '*here*'),
            ('L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}', '`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`')
            ]

    for epystr, rststr in cases:
        assert doc2html(rststr, 'restructuredtext') == doc2html(epystr, 'epytext')

def test_types_corner_cases() -> None:
    ...

def test_parsed_type_convert_obj_tokens_to_stan() -> None:
    
    convert_obj_tokens_cases = [
                ([("list", TokenType.OBJ), ("(", TokenType.DELIMITER), ("int", TokenType.OBJ), (")", TokenType.DELIMITER)], 
                [(Tag('code', children=['list', '(', 'int', ')']), TokenType.OBJ)]),    

                ([("list", TokenType.OBJ), ("(", TokenType.DELIMITER), ("int", TokenType.OBJ), (")", TokenType.DELIMITER), (", ", TokenType.DELIMITER), ("optional", TokenType.CONTROL)], 
                [(Tag('code', children=['list', '(', 'int', ')']), TokenType.OBJ), (", ", TokenType.DELIMITER), ("optional", TokenType.CONTROL)]),
            ] 

    ann = ParsedTypeDocstring("")

    for tokens_types, expected_token_types in convert_obj_tokens_cases:

        assert str(ann._convert_obj_tokens_to_stan(tokens_types, NotFoundLinker()))==str(expected_token_types)


def typespec2htmlvianode(s: str, markup: str) -> str:
    err: List[ParseError] = []
    parsed_doc = get_parser_by_name(markup)(s, err, False)
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

def test_parsed_type() -> None:
    
    parsed_type_cases = [
        ('list of int or float or None', 
        '<code>list</code> of <code>int</code> or <code>float</code> or <code>None</code>'),

        ("{'F', 'C', 'N'}, default 'N'",
        """<span class="literal">{'F', 'C', 'N'}</span>, <em>default</em> <span class="literal">'N'</span>"""),

        ("DataFrame, optional",
        "<code>DataFrame</code>, <em>optional</em>"),

        ("List[str] or list(bytes), optional", 
        "<code>List[str]</code> or <code>list(bytes)</code>, <em>optional</em>"),

        (('`complicated string` or `strIO <twisted.python.compat.NativeStringIO>`', 'L{complicated string} or L{strIO <twisted.python.compat.NativeStringIO>}'),
        '<code>complicated string</code> or <code>strIO</code>'),
    ]

    for string, excepted_html in parsed_type_cases:
        rst_string = ''
        epy_string = ''

        if isinstance(string, tuple):
            rst_string, epy_string = string
        elif isinstance(string, str):
            rst_string = epy_string = string
        
        assert typespec2htmlviastr(rst_string) == excepted_html
        assert typespec2htmlvianode(rst_string, 'restructuredtext') == excepted_html            
        assert typespec2htmlvianode(epy_string, 'epytext') == excepted_html

def test_processtypes(capsys: CapSys) -> None:
    """
    Currently, numpy and google type parsing happens both at the string level with TypeDocstring
    and at the docutils nodes ParsedTypeDocstring for type fields (``type`` and ``rtype``).
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
                "<code>list</code> of <code>int</code> or <code>float</code> or <code>None</code>")

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

                ("<code>complicated string</code> or <code>strIO</code>, optional", 
                "<code>complicated string</code> or <code>strIO</code>, <em>optional</em>")

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
    cases = [("""
              Yields
              ------
              bool:
                  Whether it's working.
              """, 
              "<code>bool</code> - Whether it's working."), 

              ("""
               Returns
               -------
               name: str
                  the name description.
               content: str
                  the content description.
               """, 
               """<ul class="rst-simple">
<li><strong>name</strong>: <code>str</code> - the name description.</li>
<li><strong>content</strong>: <code>str</code> - the content description.</li>
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

    assert "<code>list</code> of <code>int</code> or <code>float</code> or <code>None</code>" == fmt
    

# TODO test processtypes warnings

# TODO: This test should trigger some warnings. 
def test_processtypes_corner_cases(capsys: CapSys) -> None:
    system = model.System()
    system.options.processtypes = True
    mod = fromText('''
    a = None
    """
    @type: default[str]
    """
    ''', modname='test', system=system)
    a = mod.contents['a']
    docstring2html(a)

    assert isinstance(a.parsed_type, ParsedTypeDocstring)
    fmt = flatten(a.parsed_type.to_stan(NotFoundLinker()))

    captured = capsys.readouterr().out
    assert captured == ""

    assert "<em>default</em>[<code>str]</code>" == fmt

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

    expected = """<code>complicated string</code> or <code>strIO</code>, <em>optional</em>"""
    
    # Test epytext
    epy_errors: List[ParseError] = []
    epy_parsed = get_parser_by_name('epytext')(epy_string, epy_errors, True)

    assert len(epy_errors)==1
    assert "Unexpected element in type specification field: element 'doctest_block'" in epy_errors.pop().descr()

    assert flatten(epy_parsed.fields[-1].body().to_stan(NotFoundLinker())).replace('\n', '') == expected
    
    # Test restructuredtext
    rst_errors: List[ParseError] = []
    rst_parsed = get_parser_by_name('restructuredtext')(rst_string, rst_errors, True)

    assert len(rst_errors)==1
    assert "Unexpected element in type specification field: element 'doctest_block'" in rst_errors.pop().descr()

    assert flatten(rst_parsed.fields[-1].body().to_stan(NotFoundLinker())).replace('\n', ' ') == expected
