import ast
from functools import partial
import sys
from textwrap import dedent
from typing import Any, Union
import xml.sax

import pytest

from pydoctor.epydoc.markup._pyval_repr import PyvalColorizer, colorize_inline_pyval
from pydoctor.test import NotFoundLinker
from pydoctor.stanutils import flatten, flatten_text, html2stan
from pydoctor.node2stan import gettext

def color(v: Any, linebreakok:bool=True, maxlines:int=5, linelen:int=40) -> str:
    colorizer = PyvalColorizer(linelen=linelen, linebreakok=linebreakok, maxlines=maxlines)
    parsed_doc = colorizer.colorize(v)
    return parsed_doc.to_node().pformat() #type: ignore

def colorhtml(v: Any, linebreakok:bool=True, maxlines:int=5, linelen:int=40) -> str:
    colorizer = PyvalColorizer(linelen=linelen, linebreakok=linebreakok, maxlines=maxlines)
    parsed_doc = colorizer.colorize(v)
    return flatten(parsed_doc.to_stan(NotFoundLinker()))

def test_simple_types() -> None:
    """
    Integers, floats, None, and complex numbers get printed using str,
    with no syntax highlighting.
    """
    assert color(1) == """<document source="pyval_repr">
    1\n"""
    assert color(0) == """<document source="pyval_repr">
    0\n"""
    assert color(100) == """<document source="pyval_repr">
    100\n"""
    assert color(1./4) == """<document source="pyval_repr">
    0.25\n"""
    assert color(None) == """<document source="pyval_repr">
    <obj_reference refuri="None">
        None\n"""

def test_long_numbers() -> None:
    """
    Long ints will get wrapped if they're big enough.
    """
    assert color(10000000) == """<document source="pyval_repr">
    10000000\n"""
    assert color(10**90) == """<document source="pyval_repr">
    1000000000000000000000000000000000000000
    <inline classes="variable-linewrap">
        ↵
    
    0000000000000000000000000000000000000000
    <inline classes="variable-linewrap">
        ↵
    
    00000000000\n"""

def test_strings() -> None:
    """
    Strings have their quotation marks tagged as 'quote'.  Characters are
    escaped using the 'string-escape' encoding.
    """
    assert color(bytes(range(255)), maxlines=9999) == r"""<document source="pyval_repr">
    b
    <inline classes="variable-quote">
        '''
    <inline classes="variable-string">
        \x00\x01\x02\x03\x04\x05\x06\x07\x08
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        \t
    
    <inline classes="variable-string">
        \x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCD
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        EFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijk
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        lmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xfc\xfd\xfe
    <inline classes="variable-quote">
        '''
"""

def test_non_breaking_spaces() -> None:
    """
    This test might fail in the future, when twisted's XMLString supports XHTML entities (see https://github.com/twisted/twisted/issues/11581). 
    But it will always fail for python 3.6 since twisted dropped support for these versions of python.
    """
    with pytest.raises(xml.sax.SAXParseException):
        colorhtml(ast.parse('"These are non-breaking spaces."').body[0].value) == """""" # type:ignore
    with pytest.raises(xml.sax.SAXParseException):
        assert colorhtml("These are non-breaking spaces.") == """"""
    
def test_strings_quote() -> None:
    """
    Currently, the "'" quote is always used, because that's what the
    'string-escape' encoding expects.
    """
    assert color('Hello') == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        Hello
    <inline classes="variable-quote">
        '
"""

    assert color('"Hello"') == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        "Hello"
    <inline classes="variable-quote">
        '
"""

    assert color("'Hello'") == r"""<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        \'Hello\'
    <inline classes="variable-quote">
        '
"""

def test_strings_special_chars() -> None:
    assert color("'abc \t\r\n\f\v \xff 😀'\x0c\x0b\t\r \\") == r"""<document source="pyval_repr">
    <inline classes="variable-quote">
        '''
    <inline classes="variable-string">
        \'abc \t\r
    
    <inline classes="variable-string">
        \f\v ÿ 😀\'\f\v\t\r \\
    <inline classes="variable-quote">
        '''
"""


def test_strings_multiline() -> None:
    """Strings containing newlines are automatically rendered as multiline
    strings."""

    assert color("This\n  is a multiline\n string!") == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '''
    <inline classes="variable-string">
        This
    
    <inline classes="variable-string">
          is a multiline
    
    <inline classes="variable-string">
         string!
    <inline classes="variable-quote">
        '''\n"""

    # Unless we ask for them not to be:

    assert color("This\n  is a multiline\n string!", linebreakok=False)  == r"""<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        This\n  is a multiline\n string!
    <inline classes="variable-quote">
        '
"""

def test_bytes_multiline() -> None:

    # The same should work also for binary strings (bytes):

    assert color(b"This\n  is a multiline\n string!") == """<document source="pyval_repr">
    b
    <inline classes="variable-quote">
        '''
    <inline classes="variable-string">
        This
    
    <inline classes="variable-string">
          is a multiline
    
    <inline classes="variable-string">
         string!
    <inline classes="variable-quote">
        '''\n"""

    assert color(b"This\n  is a multiline\n string!", linebreakok=False) == r"""<document source="pyval_repr">
    b
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        This\n  is a multiline\n string!
    <inline classes="variable-quote">
        '
"""

def test_unicode_str() -> None:
    """Unicode strings are handled properly.
    """
    assert color("\uaaaa And \ubbbb") == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        ꪪ And 뮻
    <inline classes="variable-quote">
        '\n"""

    assert color("ÉéèÈÜÏïü") == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        ÉéèÈÜÏïü
    <inline classes="variable-quote">
        '\n"""

def test_bytes_str() -> None:
    """
    Binary strings (bytes) are handled properly:"""

    assert color(b"Hello world") == """<document source="pyval_repr">
    b
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        Hello world
    <inline classes="variable-quote">
        '\n"""

    assert color(b"\x00 And \xff") == r"""<document source="pyval_repr">
    b
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        \x00 And \xff
    <inline classes="variable-quote">
        '
"""

def test_inline_list() -> None:
    """Lists, tuples, and sets are all colorized using the same method.  The
    braces and commas are tagged with "op".  If the value can fit on the
    current line, it is displayed on one line.  Otherwise, each value is
    listed on a separate line, indented by the size of the open-bracket."""

    assert color(list(range(10))) == """<document source="pyval_repr">
    [
    <wbr>
    0
    , 
    <wbr>
    1
    , 
    <wbr>
    2
    , 
    <wbr>
    3
    , 
    <wbr>
    4
    , 
    <wbr>
    5
    , 
    <wbr>
    6
    , 
    <wbr>
    7
    , 
    <wbr>
    8
    , 
    <wbr>
    9
    ]\n"""

def test_multiline_list() -> None:

    assert color(list(range(100))) == """<document source="pyval_repr">
    [
    <wbr>
    0
    ,
    
     
    <wbr>
    1
    ,
    
     
    <wbr>
    2
    ,
    
     
    <wbr>
    3
    ,
    
     
    <wbr>
    4
    ,
    
    <inline classes="variable-ellipsis">
        ...\n"""

def test_multiline_list2() -> None:

    assert color([1,2,[5,6,[(11,22,33),9],10],11]+[99,98,97,96,95]) == """<document source="pyval_repr">
    [
    <wbr>
    1
    ,
    
     
    <wbr>
    2
    ,
    
     
    <wbr>
    [
    <wbr>
    5
    , 
    <wbr>
    6
    , 
    <wbr>
    [
    <wbr>
    (
    <wbr>
    11
    , 
    <wbr>
    22
    , 
    <wbr>
    33
    )
    , 
    <wbr>
    9
    ]
    , 
    <wbr>
    10
    ]
    ,
    
     
    <wbr>
    11
    ,
    
     
    <wbr>
    99
    ,
    
    <inline classes="variable-ellipsis">
        ...\n"""
    
def test_multiline_set() -> None:

    assert color(set(range(20))) == """<document source="pyval_repr">
    set([
    <wbr>
    0
    ,
    
         
    <wbr>
    1
    ,
    
         
    <wbr>
    2
    ,
    
         
    <wbr>
    3
    ,
    
         
    <wbr>
    4
    ,
    
    <inline classes="variable-ellipsis">
        ...\n"""

def test_frozenset() -> None:

    assert color(frozenset([1, 2, 3])) == """<document source="pyval_repr">
    frozenset([
    <wbr>
    1
    , 
    <wbr>
    2
    , 
    <wbr>
    3
    ])\n"""

def test_custom_live_object() -> None:
    class Custom:
        def __repr__(self) -> str:
            return '123'
    
    assert color(Custom()) == """<document source="pyval_repr">
    123\n"""

def test_buggy_live_object() -> None:
    class Buggy:
        def __repr__(self) -> str:
            raise NotImplementedError()
    
    assert color(Buggy()) == """<document source="pyval_repr">
    <inline classes="variable-unknown">
        ??\n"""

def test_tuples_one_value() -> None:
    """Tuples that contains only one value need an ending comma."""
    assert color((1,)) == """<document source="pyval_repr">
    (
    <wbr>
    1
    ,)
"""

def extract_expr(_ast: ast.Module) -> ast.AST:
    elem = _ast.body[0]
    assert isinstance(elem, ast.Expr)
    return elem.value

def test_ast_constants() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    'Hello'
    """)))) == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        Hello
    <inline classes="variable-quote">
        '\n"""

def test_ast_unary_op() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    not True
    """)))) == """<document source="pyval_repr">
    not 
    <obj_reference refuri="True">
        True\n"""

    assert color(extract_expr(ast.parse(dedent("""
    +3.0
    """)))) == """<document source="pyval_repr">
    +
    3.0\n"""

    assert color(extract_expr(ast.parse(dedent("""
    -3.0
    """)))) == """<document source="pyval_repr">
    -
    3.0\n"""
    
    assert color(extract_expr(ast.parse(dedent("""
    ~3.0
    """)))) == """<document source="pyval_repr">
    ~
    3.0\n"""

def test_ast_bin_op() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    2.3*6
    """)))) == """<document source="pyval_repr">
    2.3
    *
    6\n"""

    assert color(extract_expr(ast.parse(dedent("""
    (3-6)*2
    """)))) == """<document source="pyval_repr">
    (
    3
    -
    6
    )
    *
    2\n"""

    assert color(extract_expr(ast.parse(dedent("""
    101//4+101%4
    """)))) == """<document source="pyval_repr">
    101
    //
    4
    +
    101
    %
    4\n"""

    assert color(extract_expr(ast.parse(dedent("""
    1 & 0
    """)))) == """<document source="pyval_repr">
    1
    &
    0\n"""

    assert color(extract_expr(ast.parse(dedent("""
    1 | 0
    """)))) == """<document source="pyval_repr">
    1
    |
    0\n"""

    assert color(extract_expr(ast.parse(dedent("""
    1 ^ 0
    """)))) == """<document source="pyval_repr">
    1
    ^
    0\n"""

    assert color(extract_expr(ast.parse(dedent("""
    1 << 0
    """)))) == """<document source="pyval_repr">
    1
    <<
    0\n"""
    
    assert color(extract_expr(ast.parse(dedent("""
    1 >> 0
    """)))) == """<document source="pyval_repr">
    1
    >>
    0\n"""

    assert color(extract_expr(ast.parse(dedent("""
    H @ beta
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="H">
        H
    @
    <obj_reference refuri="beta">
        beta\n"""

def test_operator_precedences() -> None:

    assert color(extract_expr(ast.parse(dedent("""
    (2 ** 3) ** 2
    """)))) == """<document source="pyval_repr">
    (
    2
    **
    3
    )
    **
    2\n"""

    assert color(extract_expr(ast.parse(dedent("""
    2 ** 3 ** 2
    """)))) == """<document source="pyval_repr">
    2
    **
    (
    3
    **
    2
    )\n"""

    assert color(extract_expr(ast.parse(dedent("""
    (1 + 2) * 3 / 4
    """)))) == """<document source="pyval_repr">
    (
    1
    +
    2
    )
    *
    3
    /
    4\n"""

    assert color(extract_expr(ast.parse(dedent("""
    ((1 + 2) * 3) / 4
    """)))) == """<document source="pyval_repr">
    (
    1
    +
    2
    )
    *
    3
    /
    4\n"""

    assert color(extract_expr(ast.parse(dedent("""
    (1 + 2) * 3 / 4
    """)))) == """<document source="pyval_repr">
    (
    1
    +
    2
    )
    *
    3
    /
    4\n"""

    assert color(extract_expr(ast.parse(dedent("""
    1 + 2 * 3 / 4 - 1
    """)))) == """<document source="pyval_repr">
    1
    +
    2
    *
    3
    /
    4
    -
    1\n"""

def test_ast_bool_op() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    True and 9
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="True">
        True
     and 
    9\n"""

    assert color(extract_expr(ast.parse(dedent("""
    1 or 0 and 2 or 3 or 1
    """)))) == """<document source="pyval_repr">
    1
     or 
    0
     and 
    2
     or 
    3
     or 
    1\n"""

def test_ast_list_tuple() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    [1,2,[5,6,[(11,22,33),9],10],11]+[99,98,97,96,95]
    """)))) == """<document source="pyval_repr">
    [
    <wbr>
    1
    ,
    
     
    <wbr>
    2
    ,
    
     
    <wbr>
    [
    <wbr>
    5
    , 
    <wbr>
    6
    , 
    <wbr>
    [
    <wbr>
    (
    <wbr>
    11
    , 
    <wbr>
    22
    , 
    <wbr>
    33
    )
    , 
    <wbr>
    9
    ]
    , 
    <wbr>
    10
    ]
    ,
    
     
    <wbr>
    11
    ]
    +
    [
    <wbr>
    99
    , 
    <wbr>
    98
    , 
    <wbr>
    97
    , 
    <wbr>
    96
    , 
    <wbr>
    95
    ]\n"""
    
    
    assert color(extract_expr(ast.parse(dedent("""
    (('1', 2, 3.14), (4, '5', 6.66))
    """)))) == """<document source="pyval_repr">
    (
    <wbr>
    (
    <wbr>
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        1
    <inline classes="variable-quote">
        '
    , 
    <wbr>
    2
    , 
    <wbr>
    3.14
    )
    , 
    <wbr>
    (
    <wbr>
    4
    , 
    <wbr>
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        5
    <inline classes="variable-quote">
        '
    , 
    <wbr>
    6.66
    )
    )\n"""

def test_ast_dict() -> None:
    """
    Dictionnaries are treated just like lists.
    """
    assert color(extract_expr(ast.parse(dedent("""
    {'1':33, '2':[1,2,3,{7:'oo'*20}]}
    """)))) == """<document source="pyval_repr">
    {
    <wbr>
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        1
    <inline classes="variable-quote">
        '
    : 
    33
    , 
    <wbr>
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        2
    <inline classes="variable-quote">
        '
    : 
    [
    <wbr>
    1
    , 
    <wbr>
    2
    , 
    <wbr>
    3
    , 
    <wbr>
    {
    <wbr>
    7
    : 
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        oo
    <inline classes="variable-quote">
        '
    *
    20
    }
    ]
    }\n"""

def test_ast_annotation() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    bar[typing.Sequence[dict[str, bytes]]]
    """))), linelen=999) == """<document source="pyval_repr">
    <obj_reference refuri="bar">
        bar
    [
    <wbr>
    <obj_reference refuri="typing.Sequence">
        typing.Sequence
    [
    <wbr>
    <obj_reference refuri="dict">
        dict
    [
    <wbr>
    <obj_reference refuri="str">
        str
    , 
    <wbr>
    <obj_reference refuri="bytes">
        bytes
    ]
    ]
    ]\n"""

def test_ast_call() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    list(range(100))
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="list">
        list
    (
    <wbr>
    <obj_reference refuri="range">
        range
    (
    <wbr>
    100
    )
    )\n"""

def test_ast_call_args() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    list(func(1, *two, three=2, **args))
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="list">
        list
    (
    <wbr>
    <obj_reference refuri="func">
        func
    (
    <wbr>
    1
    , 
    <wbr>
    *
    <obj_reference refuri="two">
        two
    , 
    <wbr>
    three
    =
    2
    , 
    <wbr>
    **
    <obj_reference refuri="args">
        args
    )
    )\n"""

def test_ast_ellipsis() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    ...
    """)))) == """<document source="pyval_repr">
    <inline classes="variable-ellipsis">
        ...\n"""

def test_ast_set() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    {1, 2}
    """)))) == """<document source="pyval_repr">
    set([
    <wbr>
    1
    , 
    <wbr>
    2
    ])\n"""

    assert color(extract_expr(ast.parse(dedent("""
    set([1, 2])
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="set">
        set
    (
    <wbr>
    [
    <wbr>
    1
    , 
    <wbr>
    2
    ]
    )\n"""

def test_ast_slice() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    o[x:y]
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="o">
        o
    [
    <wbr>
    x:y
    ]\n"""

    assert color(extract_expr(ast.parse(dedent("""
    o[x:y,z]
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="o">
        o
    [
    <wbr>
    x:y, (z)
    ]\n""" if sys.version_info < (3,9) else """<document source="pyval_repr">
    <obj_reference refuri="o">
        o
    [
    <wbr>
    x:y
    ,
    <wbr>
    <obj_reference refuri="z">
        z
    ]\n"""

def test_ast_attribute() -> None:
    assert color(extract_expr(ast.parse(dedent("""
    mod.attr
    """)))) == ("""<document source="pyval_repr">
    <obj_reference refuri="mod.attr">
        mod.attr\n""")

    # ast.Attribute nodes that contains something else as ast.Name nodes are not handled explicitely.
    assert color(extract_expr(ast.parse(dedent("""
    func().attr
    """)))) == ("""<document source="pyval_repr">
    func().attr\n""")

def test_ast_regex() -> None:
    # invalid arguments
    assert color(extract_expr(ast.parse(dedent(r"""
    re.compile(invalidarg='[A-Za-z0-9]+')
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    <wbr>
    invalidarg
    =
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        [A-Za-z0-9]+
    <inline classes="variable-quote">
        '
    )\n"""

    # invalid arguments 2
    assert color(extract_expr(ast.parse(dedent("""
    re.compile()
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    )\n"""

    # invalid arguments 3
    assert color(extract_expr(ast.parse(dedent("""
    re.compile(None)
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    <wbr>
    <obj_reference refuri="None">
        None
    )\n"""

    # cannot colorize regex, be can't infer value
    assert color(extract_expr(ast.parse(dedent("""
    re.compile(get_re())
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    <wbr>
    <obj_reference refuri="get_re">
        get_re
    (
    )
    )\n"""

    # cannot colorize regex, not a valid regex
    assert color(extract_expr(ast.parse(dedent("""
    re.compile(r"[.*")
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    <wbr>
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        [.*
    <inline classes="variable-quote">
        '
    )\n"""

    # actually colorize regex, with flags
    assert color(extract_expr(ast.parse(dedent("""
    re.compile(r"[A-Za-z0-9]+", re.X)
    """)))) == """<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    r
    <inline classes="variable-quote">
        '
    <inline classes="re-group">
        [
    A
    <inline classes="re-op">
        -
    Z
    a
    <inline classes="re-op">
        -
    z
    0
    <inline classes="re-op">
        -
    9
    <inline classes="re-group">
        ]
    <inline classes="re-op">
        +
    <inline classes="variable-quote">
        '
    ,
    
               
    <obj_reference refuri="re.X">
        re.X
    )\n"""

def color_re(s: Union[bytes, str], 
             check_roundtrip:bool=True) -> str:

    colorizer = PyvalColorizer(linelen=55, maxlines=5)
    val = colorizer.colorize(extract_expr(ast.parse(f"re.compile({repr(s)})")))

    if check_roundtrip:
        raw_text = ''.join(gettext(val.to_node()))
        re_begin = 13
        raw_string = True

        if raw_text[11] != 'r':
            # the regex has failed to be colorized since we can't find the r prefix
            # meaning the string has been rendered as plaintext instead.
            raw_string = False
            re_begin -= 1
        
        if isinstance(s, bytes):
            re_begin += 1
        re_end = -2

        round_trip: Union[bytes, str] = raw_text[re_begin:re_end]
        if isinstance(s, bytes):
            assert isinstance(round_trip, str)
            round_trip = bytes(round_trip, encoding='utf-8')
        
        expected = s
        if not raw_string:
            assert isinstance(expected, str) 
            # we only test invalid regexes with strings currently
            expected = expected.replace('\\', '\\\\')
        
        assert round_trip == expected, "%s != %s" % (repr(round_trip), repr(s))
    
    return flatten(val.to_stan(NotFoundLinker()))[17:-8]


def test_re_literals() -> None:
    # Literal characters
    assert color_re(r'abc \t\r\n\f\v \xff \uffff', False) == r"""r<span class="rst-variable-quote">'</span>abc \t\r\n\f\v \xff \uffff<span class="rst-variable-quote">'</span>"""

    assert color_re(r'\.\^\$\\\*\+\?\{\}\[\]\|\(\)\'') == r"""r<span class="rst-variable-quote">'</span>\.\^\$\\\*\+\?\{\}\[\]\|\(\)\'<span class="rst-variable-quote">'</span>"""

    # Any character & character classes
    assert color_re(r".\d\D\s\S\w\W\A^$\b\B\Z") == r"""r<span class="rst-variable-quote">'</span>.\d\D\s\S\w\W\A^$\b\B\Z<span class="rst-variable-quote">'</span>"""

def test_re_branching() -> None:
    # Branching
    assert color_re(r"foo|bar") == """r<span class="rst-variable-quote">'</span>foo<span class="rst-re-op">|</span>bar<span class="rst-variable-quote">'</span>"""

def test_re_char_classes() -> None:
    # Character classes
    assert color_re(r"[abcd]") == """r<span class="rst-variable-quote">'</span><span class="rst-re-group">[</span>abcd<span class="rst-re-group">]</span><span class="rst-variable-quote">'</span>"""

def test_re_repeats() -> None:
    # Repeats
    assert color_re(r"a*b+c{4,}d{,5}e{3,9}f?") == ("""r<span class="rst-variable-quote">'</span>a<span class="rst-re-op">*</span>"""
                                                   """b<span class="rst-re-op">+</span>c<span class="rst-re-op">{4,}</span>"""
                                                   """d<span class="rst-re-op">{,5}</span>e<span class="rst-re-op">{3,9}</span>"""
                                                   """f<span class="rst-re-op">?</span><span class="rst-variable-quote">'</span>""")

    assert color_re(r"a*?b+?c{4,}?d{,5}?e{3,9}?f??") == ("""r<span class="rst-variable-quote">'</span>a<span class="rst-re-op">*?</span>"""
                                                         """b<span class="rst-re-op">+?</span>c<span class="rst-re-op">{4,}?</span>"""
                                                         """d<span class="rst-re-op">{,5}?</span>e<span class="rst-re-op">{3,9}?</span>"""
                                                         """f<span class="rst-re-op">??</span><span class="rst-variable-quote">'</span>""")

def test_re_subpatterns() -> None:
    # Subpatterns
    assert color_re(r"(foo (bar) | (baz))") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(</span>"""
                                                """foo <span class="rst-re-group">(</span>bar<span class="rst-re-group">)</span> """
                                                """<span class="rst-re-op">|</span> <span class="rst-re-group">(</span>"""
                                                """baz<span class="rst-re-group">)</span><span class="rst-re-group">)</span>"""
                                                """<span class="rst-variable-quote">'</span>""")
    
    
    assert color_re(r"(?:foo (?:bar) | (?:baz))") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(?:</span>"""
                                                        """foo <span class="rst-re-group">(?:</span>bar<span class="rst-re-group">)</span> <span class="rst-re-op">|</span> """
                                                        """<span class="rst-re-group">(?:</span>baz<span class="rst-re-group">)</span><span class="rst-re-group">)</span><span class="rst-variable-quote">'</span>""")

    assert color_re(r"(<)?(\w+@\w+(?:\.\w+)+)") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(</span>&lt;"""
                                                    """<span class="rst-re-group">)</span><span class="rst-re-op">?</span>"""
                                                    r"""<span class="rst-re-group">(</span>\w<span class="rst-re-op">+</span>@\w"""
                                                    r"""<span class="rst-re-op">+</span><span class="rst-re-group">(?:</span>\.\w"""
                                                    """<span class="rst-re-op">+</span><span class="rst-re-group">)</span><span class="rst-re-op">+</span>"""
                                                    """<span class="rst-re-group">)</span><span class="rst-variable-quote">'</span>""")

    assert color_re("(foo (?P<a>bar) | (?P<boop>baz))") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(</span>"""
                                                            """foo <span class="rst-re-group">(?P&lt;</span><span class="rst-re-ref">"""
                                                            """a</span><span class="rst-re-group">&gt;</span>bar<span class="rst-re-group">)</span> """
                                                            """<span class="rst-re-op">|</span> <span class="rst-re-group">(?P&lt;</span>"""
                                                            """<span class="rst-re-ref">boop</span><span class="rst-re-group">&gt;</span>"""
                                                            """baz<span class="rst-re-group">)</span><span class="rst-re-group">)</span>"""
                                                            """<span class="rst-variable-quote">'</span>""")

def test_re_references() -> None:
    # Group References
    assert color_re(r"(...) and (\1)") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(</span>..."""
                                           """<span class="rst-re-group">)</span> and <span class="rst-re-group">(</span>"""
                                           r"""<span class="rst-re-ref">\1</span><span class="rst-re-group">)</span>"""
                                           """<span class="rst-variable-quote">'</span>""")

def test_re_ranges() -> None:
    # Ranges
    assert color_re(r"[a-bp-z]") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">[</span>a"""
                                     """<span class="rst-re-op">-</span>bp<span class="rst-re-op">-</span>z"""
                                     """<span class="rst-re-group">]</span><span class="rst-variable-quote">'</span>""")

    assert color_re(r"[^a-bp-z]") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">[</span>"""
                                      """<span class="rst-re-op">^</span>a<span class="rst-re-op">-</span>bp"""
                                      """<span class="rst-re-op">-</span>z<span class="rst-re-group">]</span>"""
                                      """<span class="rst-variable-quote">'</span>""")

    assert color_re(r"[^abc]") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">[</span>"""
                                   """<span class="rst-re-op">^</span>abc<span class="rst-re-group">]</span>"""
                                   """<span class="rst-variable-quote">'</span>""")

def test_re_lookahead_behinds() -> None:
    # Lookahead/behinds
    assert color_re(r"foo(?=bar)") == ("""r<span class="rst-variable-quote">'</span>foo<span class="rst-re-group">(?=</span>"""
                                       """bar<span class="rst-re-group">)</span><span class="rst-variable-quote">'</span>""")
 
    assert color_re(r"foo(?!bar)") == ("""r<span class="rst-variable-quote">'</span>foo<span class="rst-re-group">(?!</span>"""
                                       """bar<span class="rst-re-group">)</span><span class="rst-variable-quote">'</span>""")
 
    assert color_re(r"(?<=bar)foo") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(?&lt;=</span>"""
                                        """bar<span class="rst-re-group">)</span>foo<span class="rst-variable-quote">'</span>""")
 
    assert color_re(r"(?<!bar)foo") == ("""r<span class="rst-variable-quote">'</span><span class="rst-re-group">(?&lt;!</span>"""
                                        """bar<span class="rst-re-group">)</span>foo<span class="rst-variable-quote">'</span>""")


def test_re_flags() -> None:
    # Flags
    assert color_re(r"(?imu)^Food") == """r<span class="rst-variable-quote">'</span><span class="rst-re-flags">(?imu)</span>^Food<span class="rst-variable-quote">'</span>"""

    assert color_re(b"(?Limsx)^Food") == """rb<span class="rst-variable-quote">'</span><span class="rst-re-flags">(?Limsx)</span>^Food<span class="rst-variable-quote">'</span>"""

    assert color_re(b"(?Limstx)^Food") == """rb<span class="rst-variable-quote">'</span><span class="rst-re-flags">(?Limstx)</span>^Food<span class="rst-variable-quote">'</span>"""
    
    assert color_re(r"(?imstux)^Food") == """r<span class="rst-variable-quote">'</span><span class="rst-re-flags">(?imstux)</span>^Food<span class="rst-variable-quote">'</span>"""
     
    assert color_re(r"(?x)This   is   verbose", False) == """r<span class="rst-variable-quote">'</span><span class="rst-re-flags">(?ux)</span>Thisisverbose<span class="rst-variable-quote">'</span>"""

def test_unsupported_regex_features() -> None:
    """
    Because pydoctor uses the regex engine of python 3.6, it does not support the 
    latest features introduced in python3.11 like atomic groupping and possesive qualifiers.

    But still, we should not crash.
    """
    regexes = ['e*+e',
        '(e?){2,4}+a',
        r"^(\w){1,2}+$",
        # "^x{}+$", this one fails to round-trip :/
        r'a++',
        r'(?:ab)++',
        r'(?:ab){1,3}+',
        r'(?>x++)x',
        r'(?>a{1,3})',
        r'(?>(?:ab){1,3})',
        ]
    for r in regexes:
        color_re(r)

def test_re_not_literal() -> None:

    assert color_re(r"[^0-9]") == """r<span class="rst-variable-quote">'</span><span class="rst-re-group">[</span><span class="rst-re-op">^</span>0<span class="rst-re-op">-</span>9<span class="rst-re-group">]</span><span class="rst-variable-quote">'</span>"""

def test_re_named_groups() -> None:
    # This regex triggers some weird behaviour: it adds the &crarr; element at the end where it should not be...
    # The regex is 42 caracters long, so more than 40, maybe that's why?
    # assert color_re(r'^<(?P<descr>.*) at (?P<addr>0x[0-9a-f]+)>$') == """"""
    
    assert color_re(r'^<(?P<descr>.*)>$') == """r<span class="rst-variable-quote">'</span>^&lt;<span class="rst-re-group">(?P&lt;</span><span class="rst-re-ref">descr</span><span class="rst-re-group">&gt;</span>.<span class="rst-re-op">*</span><span class="rst-re-group">)</span>&gt;$<span class="rst-variable-quote">'</span>"""

def test_re_multiline() -> None:

    assert color(extract_expr(ast.parse(dedent(r'''re.compile(r"""\d +  # the integral part
        \.    # the decimal point
        \d *  # some fractional digits""")''')))) == r"""<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    <inline classes="variable-quote">
        '''
    <inline classes="variable-string">
        \\d +  # the integral part
    
    <inline classes="variable-string">
                \\.    # the decimal point
    
    <inline classes="variable-string">
                \\d *  # some fractional digits
    <inline classes="variable-quote">
        '''
    <inline classes="variable-linewrap">
        ↵
    
    )
"""

    assert color(extract_expr(ast.parse(dedent(r'''re.compile(rb"""\d +  # the integral part
        \.    # the decimal point
        \d *  # some fractional digits""")'''))), linelen=70) == r"""<document source="pyval_repr">
    <obj_reference refuri="re.compile">
        re.compile
    (
    b
    <inline classes="variable-quote">
        '''
    <inline classes="variable-string">
        \\d +  # the integral part
    
    <inline classes="variable-string">
                \\.    # the decimal point
    
    <inline classes="variable-string">
                \\d *  # some fractional digits
    <inline classes="variable-quote">
        '''
    )
"""

def test_line_wrapping() -> None:

    # If a line goes beyond linelen, it is wrapped using the ``&crarr;`` element. 
    # Check that the last line gets a ``&crarr;`` when maxlines is exceeded:

    assert color('x'*1000) == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-string">
        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    <inline classes="variable-linewrap">
        ↵
    
    <inline classes="variable-ellipsis">
        ...\n"""

    # If linebreakok is False, then line wrapping gives an ellipsis instead:

    assert color('x'*100, linebreakok=False) == """<document source="pyval_repr">
    <inline classes="variable-quote">
        '
    <inline classes="variable-string">
        xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    <inline classes="variable-ellipsis">
        ...\n"""

def color2(v: Any, linelen:int=50) -> str:
    """
    Pain text colorize.
    """
    colorizer = PyvalColorizer(linelen=linelen, maxlines=5)
    colorized = colorizer.colorize(v)
    text1 = ''.join(gettext(colorized.to_node()))
    text2 = flatten_text(html2stan(flatten(colorized.to_stan(NotFoundLinker()))))
    assert text1 == text2
    return text2


def test_crash_surrogates_not_allowed() -> None:
    """
    Test that the colorizer does not make the flatten function crash when passing surrogates unicode strings.
    """
    assert color2('surrogates:\udc80\udcff') == "'surrogates:\\udc80\\udcff'"

def test_surrogates_cars_in_re() -> None:
    """
    Regex string are escaped their own way. See https://github.com/twisted/pydoctor/pull/493
    """
    assert color2(extract_expr(ast.parse("re.compile('surrogates:\\udc80\\udcff')"))) == "re.compile(r'surrogates:\\udc80\\udcff')"

def test_repr_text() -> None:
    """Test a few representations, with a plain text version.
    """
    class A: pass

    assert color2('hello') == "'hello'"

    assert color2(["hello", 123]) == "['hello', 123]"

    assert color2(A()) == ('<pydoctor.test.epydoc.test_pyval_repr.test_repr_te↵\n'
                            'xt.<locals>.A object>')

    assert color2([A()]) == ('[<pydoctor.test.epydoc.test_pyval_repr.test_repr_t↵\n'
                             'ext.<locals>.A object>]')

    assert color2([A(),1,2,3,4,5,6,7]) == ('[<pydoctor.test.epydoc.test_pyval_repr.test_repr_t↵\n'
                                            'ext.<locals>.A object>,\n'
                                            ' 1,\n'
                                            ' 2,\n'
                                            ' 3,\n'
                                            '...')

def test_summary() -> None:
    """To generate summary-reprs, use maxlines=1 and linebreakok=False:
    """
    summarizer = PyvalColorizer(linelen=60, maxlines=1, linebreakok=False)
    def summarize(v:Any) -> str:
        return(''.join(gettext(summarizer.colorize(v).to_node())))

    assert summarize(list(range(100))) == "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16..."
    assert summarize('hello\nworld') == r"'hello\nworld'"
    assert summarize('hello\nworld'*100) == r"'hello\nworldhello\nworldhello\nworldhello\nworldhello\nw..."

def test_refmap_explicit() -> None:
    """
    The refmap argument allow to change the target of some links 
    before the linker resolves them.
    """
    
    doc = colorize_inline_pyval(extract_expr(ast.parse('Type[MyInt, str]')), 
        refmap = {
            'Type':'typing.Type', 
            'MyInt': '<mymod>.MyInt'})
    tree = doc.to_node()
    dump = tree.pformat()
    assert '<obj_reference refuri="typing.Type">' in dump
    assert '<obj_reference refuri="<mymod>.MyInt">' in dump
    assert '<obj_reference refuri="str">' in dump

def check_src_roundtrip(src:str, subtests:Any) -> None:
    # from cpython/Lib/test/test_unparse.py
    with subtests.test(msg="round trip", src=src):
        mod = ast.parse(src)
        assert len(mod.body)==1
        expr = mod.body[0]
        assert isinstance(expr, ast.Expr)
        code = color2(expr.value)
        assert code==src

def test_expressions_parens(subtests:Any) -> None:
    check_src = partial(check_src_roundtrip, subtests=subtests)
    check_src("1<<(10|1)<<1")
    check_src("int|float|complex|None")
    check_src("1+1")
    check_src("1+2/3")
    check_src("(1+2)/3")
    check_src("(1+2)*3+4*(5+2)")
    check_src("(1+2)*3+4*(5+2)**2")
    check_src("~x")
    check_src("x and y")
    check_src("x and y and z")
    check_src("x and (y and x)")
    check_src("(x and y) and z")
    # cpython tests expected '(x**y)**z**q', 
    # but too much reasonning is needed to obtain this result,
    # because the power operator is reassociative...
    check_src("(x**y)**(z**q)")
    check_src("((x**y)**z)**q")
    check_src("x>>y")
    check_src("x<<y")
    check_src("x>>y and x>>z")
    check_src("x+y-z*q^t**k")
    
    check_src("flag&(other|foo)")
    
    # with astor (which adds a lot of parenthesis :/)
    if sys.version_info>=(3,8):
        check_src("(a := b)")
    if sys.version_info>=(3,7):
        check_src("(await x)")
    check_src("(x if x else y)")
    check_src("(lambda x: x)")
    check_src("(lambda : int)()")
    check_src("not (x == y)")
    check_src("(x == (not y))")
    check_src("(P * V if P and V else n * R * T)")
    check_src("(lambda P, V, n: P * V == n * R * T)")
    
    check_src("f(**x)")
    check_src("{**x}")

    check_src("(-1)**7")
    check_src("(-1.0)**8")
    check_src("(-1j)**6")
    check_src("not True or False")
    check_src("True or not False")

    check_src("(3).__abs__()")

    check_src("f(**([] or 5))")
    check_src("{**([] or 5)}")
    check_src("{**(~{})}")
    check_src("{**(not {})}")
    check_src("{**({} == {})}")
    check_src("{**{'y': 2}, 'x': 1, None: True}")
    check_src("{**{'y': 2}, **{'x': 1}}")
