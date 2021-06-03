
from typing import Any, Optional, Union
from requests.structures import CaseInsensitiveDict
from pydoctor.epydoc.markup._pyval_repr import PyvalColorizer
from pydoctor.test import NotFoundLinker
from pydoctor.epydoc.markup import flatten
import re

colorizer = PyvalColorizer(linelen=40)
def color(v: Any, linebreakok:bool=True, maxlines:int=5):
    colorizer = PyvalColorizer(linelen=40, linebreakok=linebreakok, maxlines=maxlines)
    parsed_doc = colorizer.colorize(v, None)
    s = flatten(parsed_doc.to_stan(NotFoundLinker()))
    s = s.encode('ascii', 'xmlcharrefreplace').decode('ascii')
    return s

def test_simple_types() -> None:
    """
    Integers, floats, None, and complex numbers get printed using str,
    with no syntax highlighting.
    """
    assert color(10) == "10"
    assert color(1./4) == "0.25"
    assert color(None) == "None"
    assert color(100) == "100"

def test_long_numbers() -> None:
    """
    Long ints will get wrapped if they're big enough.
    """
    assert color(10000000) == "10000000"
    assert color(10**90) == ("1000000000000000000000000000000000000000&#8629;\n"
        "0000000000000000000000000000000000000000&#8629;\n"
        "00000000000")

def test_strings() -> None:
    """
    Strings have their quotation marks tagged as 'quote'.  Characters are
    escaped using the 'string-escape' encoding.
    """
    assert color(bytes(range(255)), maxlines=9999) == r"""<code>b'''</code><code>\x00\x01\x02\x03\x04\x05\x06\x07\x08</code>&#8629;
<code>\t</code>
<code>\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x</code>&#8629;
<code>15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x</code>&#8629;
<code>1f !"#$%&amp;\'()*+,-./0123456789:;&lt;=&gt;?@ABCD</code>&#8629;
<code>EFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijk</code>&#8629;
<code>lmnopqrstuvwxyz{|}~\x7f\x80\x81\x82\x83\</code>&#8629;
<code>x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\</code>&#8629;
<code>x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\</code>&#8629;
<code>x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\</code>&#8629;
<code>xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\</code>&#8629;
<code>xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\</code>&#8629;
<code>xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\</code>&#8629;
<code>xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\</code>&#8629;
<code>xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\</code>&#8629;
<code>xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\</code>&#8629;
<code>xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\</code>&#8629;
<code>xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\</code>&#8629;
<code>xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\</code>&#8629;
<code>xfc\xfd\xfe</code><code>'''</code>"""

def test_strings_quote() -> None:
    """
    Currently, the "'" quote is always used, because that's what the
    'string-escape' encoding expects.
    """
    assert color('Hello') == "<code>'</code><code>Hello</code><code>'</code>"
    assert color('"Hello"') == """<code>'</code><code>"Hello"</code><code>'</code>"""
    assert color("'Hello'") == r"""<code>'</code><code>\'Hello\'</code><code>'</code>"""

def test_strings_multiline() -> None:
    """Strings containing newlines are automatically rendered as multiline
    strings."""

    assert color("This\n  is a multiline\n string!") == """<code>'''</code><code>This</code>
<code>  is a multiline</code>
<code> string!</code><code>'''</code>"""

    # Unless we ask for them not to be:

    assert color("This\n  is a multiline\n string!", linebreakok=False)  == r"<code>'</code><code>This\n  is a multiline\n string!</code><code>'</code>"

def test_bytes_multiline() -> None:

    # The same should work also for binary strings (bytes):

    assert color(b"This\n  is a multiline\n string!") == """<code>b'''</code><code>This</code>
<code>  is a multiline</code>
<code> string!</code><code>'''</code>"""

    assert color(b"This\n  is a multiline\n string!", linebreakok=False) == r"<code>b'</code><code>This\n  is a multiline\n string!</code><code>'</code>"

def test_unicode_str() -> None:
    """Unicode strings are handled properly.
    """
    assert color("\uaaaa And \ubbbb") == "<code>'</code><code>&#43690; And &#48059;</code><code>'</code>"

def test_bytes_str() -> None:
    """
    Binary strings (bytes) are handled properly:"""

    assert color(b"Hello world") == "<code>b'</code><code>Hello world</code><code>'</code>"
    assert color(b"\x00 And \xff") == r"<code>b'</code><code>\x00 And \xff</code><code>'</code>"

def test_list_tuples_etc() -> None:
    """Lists, tuples, and sets are all colorized using the same method.  The
    braces and commas are tagged with "op".  If the value can fit on the
    current line, it is displayed on one line.  Otherwise, each value is
    listed on a separate line, indented by the size of the open-bracket."""

    assert color(list(range(10))) == "<code>[</code>0<code>, </code>1<code>, </code>2<code>, </code>3<code>, </code>4<code>, </code>5<code>, </code>6<code>, </code>7<code>, </code>8<code>, </code>9<code>]</code>"
    
    assert color(list(range(100))) == """<code>[</code>0<code>,</code>
 1<code>,</code>
 2<code>,</code>
 3<code>,</code>
 4<code>,</code>
<code>...</code>"""
    
    assert color([1,2,[5,6,[(11,22,33),9],10],11]+[99,98,97,96,95]) == """<code>[</code>1<code>,</code>
 2<code>,</code>
 <code>[</code>5<code>, </code>6<code>, </code><code>[</code><code>(</code>11<code>, </code>22<code>, </code>33<code>)</code><code>, </code>9<code>]</code><code>, </code>10<code>]</code><code>,</code>
 11<code>,</code>
 99<code>,</code>
<code>...</code>"""
    
    assert color(set(range(20))) == """<code>set([</code>0<code>,</code>
     1<code>,</code>
     2<code>,</code>
     3<code>,</code>
     4<code>,</code>
<code>...</code>"""

def test_dictionaries() -> None:
    """Dicts are treated just like lists, except that the ":" is also tagged as
    "op"."""

    assert color({'1':33, '2':[1,2,3,{7:'oo'*20}]}) == """<code>{</code><code>'</code><code>1</code><code>'</code><code>: </code>33<code>,</code>
 <code>'</code><code>2</code><code>'</code><code>: </code><code>[</code>1<code>,</code>
       2<code>,</code>
       3<code>,</code>
       <code>{</code>7<code>: </code><code>'</code><code>oooooooooooooooooooooooooooo</code>&#8629;
<code>...</code>"""


def textcontent(elt):
    if isinstance(elt, (str, bytes)): return elt
    else: return ''.join([textcontent(c) for c in elt.children])

def color_re(s: Union[bytes, str], pre:Optional[str]=None, 
             check_roundtrip:bool=False) -> str:

    # Currently, we never set check_roundtrip to True
    # It does not pass the test currently because it initially relied on "val.to_plaintext()".
    # A method that has been removed from the ParsedDocstring interface.
    # I've replaced it with "textcontent(val._tree)", so that's the issue I guess. 

    colorizer = PyvalColorizer(linelen=55)
    val = colorizer.colorize(re.compile(s))
    
    if check_roundtrip:
        if pre is None:
            pre = '(?u)' if isinstance(s, str) else ''

        if isinstance(s, bytes):
            s = str(s, 'utf-8')
        p = re.compile(r"^(\(\?\w+\)|)")
        s = re.sub(p, pre, s)

        tc = textcontent(val._tree)[13:-2]
        assert tc == s, "%s != %s" % (repr(tc), repr(s))

    return flatten(val.to_stan(NotFoundLinker()))[13:-2]
    # return s.strip()[13:-2]
    # print(s.rstrip())

def test_re_literals() -> None:
    # Literal characters
    assert color_re(u'abc \t\r\n\f\v \xff \uffff', None, False) == r"<code>(?u)</code>abc \t\r\n\f\v \xff \uffff"

    assert color_re(r'\.\^\$\\\*\+\?\{\}\[\]\|\(\)\'') == r"<code>(?u)</code>\.\^\$\\\*\+\?\{\}\[\]\|\(\)\'"

    # Any character & character classes
    assert color_re(r".\d\D\s\S\w\W\A^$\b\B\Z") == r"<code>(?u)</code>.\d\D\s\S\w\W\A^$\b\B\Z"
    # 

def test_re_branching() -> None:
    # Branching
    assert color_re(r"foo|bar") == """<code>(?u)</code>foo<code>|</code>bar"""

# THIS TESTS NEEDS TO BE PORTED TO NEW VERSION OF THE COLORIZER
'''

def test_re_char_classes() -> None:
    # Character classes
    assert color_re(r"[abcd]") == ""
    # <code class="re-flags">(?u)</code><code class="re-group">[</code>abcd<code class="re-group">]</code>

def test_re_repeats() -> None:
    # Repeats
    assert color_re(r"a*b+c{4,}d{,5}e{3,9}f?") == ""
    # <code class="re-flags">(?u)</code>a<code class="re-op">*</code>b<code class="re-op">+</code>c<code class="re-op">{4,}</code>d<code class="re-op">{,5}</code>e<code class="re-op">{3,9}</code>f<code class="re-op">?</code>
    assert color_re(r"a*?b+?c{4,}?d{,5}?e{3,9}?f??") == ""
    # <code class="re-flags">(?u)</code>a<code class="re-op">*?</code>b<code class="re-op">+?</code>c<code class="re-op">{4,}?</code>d<code class="re-op">{,5}?</code>e<code class="re-op">{3,9}?</code>f<code class="re-op">??</code>

def test_re_subpatterns() -> None:
    # Subpatterns
    assert color_re(r"(foo (bar) | (baz))") == """<code class="re-flags">(?u)</code><code class="re-group">(</code>foo <code class="re-group">(</code>bar<code class="re-group">)</code> <code class="re-op">|</code> <code class="re-group">(</code>baz<code class="re-group">)</code><code class="re-group">)</code>"""
    # 
    assert color_re(r"(?:foo (?:bar) | (?:baz))") == """<code class="re-flags">(?u)</code><code class="re-group">(?:</code>foo <code class="re-group">(?:</code>bar<code class="re-group">)</code> <code class="re-op">|</code> <code class="re-group">(?:</code>baz<code class="re-group">)</code><code class="re-group">)</code>"""
    # 
    assert color_re("(foo (?P<a>bar) | (?P<boop>baz))") == """<code class="re-flags">(?u)</code><code class="re-group">(</code>foo <code class="re-group">(?P&lt;</code><code class="re-ref">a</code><code class="re-group">&gt;</code>bar<code class="re-group">)</code> <code class="re-op">|</code> <code class="re-group">(?P&lt;</code><code class="re-ref">boop</code><code class="re-group">&gt;</code>baz<code class="re-group">)</code><code class="re-group">)</code>"""
    # 

def test_re_references() -> None:
    # Group References
    assert color_re(r"(...) and (\1)") == """<code class="re-flags">(?u)</code><code class="re-group">(</code>...<code class="re-group">)</code> and <code class="re-group">(</code><code class="re-ref">\1</code><code class="re-group">)</code>"""
    # 

def test_re_ranges() -> None:
    # Ranges
    assert color_re(r"[a-bp-z]") == """<code class="re-flags">(?u)</code><code class="re-group">[</code>a<code class="re-op">-</code>bp<code class="re-op">-</code>z<code class="re-group">]</code>"""
    # 
    assert color_re(r"[^a-bp-z]") == """<code class="re-flags">(?u)</code><code class="re-group">[</code><code class="re-op">^</code>a<code class="re-op">-</code>bp<code class="re-op">-</code>z<code class="re-group">]</code>"""
    # 
    assert color_re(r"[^abc]") == """<code class="re-flags">(?u)</code><code class="re-group">[</code><code class="re-op">^</code>abc<code class="re-group">]</code>"""
    # 

def test_re_lookahead_behinds() -> None:
    # Lookahead/behinds
    assert color_re(r"foo(?=bar)") == """<code class="re-flags">(?u)</code>foo<code class="re-group">(?=</code>bar<code class="re-group">)</code>"""
 
    assert color_re(r"foo(?!bar)") == """<code class="re-flags">(?u)</code>foo<code class="re-group">(?!</code>bar<code class="re-group">)</code>"""
 
    assert color_re(r"(?<=bar)foo") == """<code class="re-flags">(?u)</code><code class="re-group">(?&lt;=</code>bar<code class="re-group">)</code>foo"""
 
    assert color_re(r"(?<!bar)foo") == """<code class="re-flags">(?u)</code><code class="re-group">(?&lt;!</code>bar<code class="re-group">)</code>foo"""

'''

def test_re_subpatterns() -> None:
    # Flags
    assert color_re(r"(?im)^Food", '(?imu)') == "<code>(?imu)</code>^Food"

    assert color_re(b"(?Limsx)^Food", '(?Limsx)') == "<code>(?Limsx)</code>^Food"

    assert color_re(b"(?Limstx)^Food", '(?Limstx)') == "<code>(?Limstx)</code>^Food"
    
    assert color_re(r"(?imstux)^Food", '(?imstux)') == "<code>(?imstux)</code>^Food"
     
    assert color_re(r"(?x)This   is   verbose", '(?ux)', False) == "<code>(?ux)</code>Thisisverbose"
     

def test_line_wrapping() -> None:

    # If a line goes beyond linelen, it is wrapped using the ``&crarr;`` element. 
    # Check that the last line gets a ``&crarr;`` when maxlines is exceeded:

    assert color('x'*1000) == """<code>'</code><code>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>&#8629;
<code>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>&#8629;
<code>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>&#8629;
<code>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>&#8629;
<code>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>&#8629;
<code>...</code>"""

    # If linebreakok is False, then line wrapping gives an ellipsis instead:

    assert color('x'*100, linebreakok=False) == "<code>'</code><code>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code><code>...</code>"

def color2(v):
    colorizer = PyvalColorizer(linelen=50)
    pds = colorizer.colorize(v)
    text = textcontent(pds._tree)
    score = pds.score
    is_ok = pds.score>0
    return text, score, is_ok

def test_repr_score() -> None:
    """When colorized representations are built, a score is computed
    evaluating how helpful the repr is.  E.g., unhelpful values like ``<Foo
    instance at 0x12345>`` get low scores.  Currently, the scoring
    algorithm is:

    - [+1] for each object colorized.  When the colorizer recurses into
    a structure, this will add one for each element contained.
    - [-5] when repr(obj) looks like <xyz instance at ...>, for any
    colorized object (including objects in structures).
    - [-100] if repr(obj) raises an exception, for any colorized object
    (including objects in structures).

    The ``min_score`` arg to colorize can be used to set a cutoff-point for
    scores; if the score is too low, then `PyvalColorizer.colorize` will use UNKNOWN_REPR instead.
    """
    class A: pass

    assert color2('hello') == ("'hello'", 1, True)

    assert color2(["hello", 123]) == ("['hello', 123]", 3, True)

    assert color2(A()) == ('<pydoctor.test.epydoc.test_pyval_repr.test_repr_sccrarr\n'
                            'ore.<locals>.A object>', -4, False)

    assert color2([A()]) == ('[<pydoctor.test.epydoc.test_pyval_repr.test_repr_scrarr\n'
                             'core.<locals>.A object>]', -3, False)

    assert color2([A(),1,2,3,4,5,6,7]) == ('[<pydoctor.test.epydoc.test_pyval_repr.test_repr_scrarr\n'
                                            'core.<locals>.A object>,\n'
                                            ' 1,\n'
                                            ' 2,\n'
                                            ' 3,\n'
                                            '...',
                                            0,
                                            False,)

def test_summary() -> None:
    """To generate summary-reprs, use maxlines=1 and linebreakok=False:
    """
    summarizer = PyvalColorizer(linelen=60, maxlines=1, linebreakok=False)
    def summarize(v:str) -> str:
        return(textcontent(summarizer.colorize(v)._tree))

    assert summarize(list(range(100))) == "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16..."
    assert summarize('hello\nworld') == r"'hello\nworld'"
    assert summarize('hello\nworld'*100) == r"'hello\nworldhello\nworldhello\nworldhello\nworldhello\nw..."
