"""
Module demonstrating the constant representations.
"""

import re
from .demo_epytext_module import demo_fields_docstring_arguments, _PrivateClass

A_DICT = {'1':33, '2':[1,2,3,{7:'oo'*20}], 
         '3': demo_fields_docstring_arguments, 
         '4': _PrivateClass.method_inside_private, 
         '5': re.compile('^<(?P<descr>.*) at (?P<addr>0x[0-9a-f]+)>$') }
"""
Pydoctor does a pretty good job at analyzing constant values ;-)
"""

A_LIST = [1,2,[5,6,[(11,22,33),9],10],11]+[99,98,97,96,95]

ANOTHER_LIST = list(range(100))

RE_STR = re.compile("(foo (?P<a>bar) | (?P<boop>baz))")

RE_RAW_STR = re.compile(r"abc_raw \t\r\n\f\v \xff \uffff")

RE_WITH_UNICODE = re.compile("abc 😀")

RE_RAW_STR2 = re.compile(r'\.\^\$\\\*\+\?\{\}\[\]\|\(\)\'')

RE_BYTES = re.compile(b"(foo (?P<a>bar \t\r\n\f\v \xff \uffff) | (?P<boop>baz))")
"""
Ivalid regexes are still displayed on a best effort basis.
"""

RE_RAW_BYTES = re.compile(rb"(foo_raw (?P<a>bar \t\r\n\f\v \xff \x1b.*\x07) | (?P<boop>baz))")

RE_MULTILINE = re.compile(r'''
    # Source consists of a PS1 line followed by zero or more PS2 lines.
    (?P<source>
        (?:^(?P<indent> [ ]*) >>>    .*)    # PS1 line
        (?:\n           [ ]*  \.\.\. .*)*   # PS2 lines
        \n?)
    # Want consists of any non-blank lines that do not start with PS1.
    (?P<want> (?:(?![ ]*$)    # Not a blank line
                 (?![ ]*>>>)  # Not a line starting with PS1
                 .*$\n?       # But any other line
              )*)
    ''', re.MULTILINE | re.VERBOSE)
"""
Multiline regex patterns are rendered as string.
"""
