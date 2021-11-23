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
The value of a constant is rendered with syntax highlighting.
Internal and external links are generated to references of classes/functions used inside the constant
"""

A_STIRNG = "L'humour, c'est l'arme blanche des hommes désarmés; c'est une déclaration de supériorité de l'humain sur ce qui lui arrive 😀. Romain GARY."
"""
Strings are always rendered in single quotes, and appropriate escaping is added when required. 

Continuing lines are wrapped with symbol: "↵". Unicode is supported.
"""

A_MULTILINE_STRING = "Dieu se rit des hommes qui déplorent les effets dont ils cherrissent les causes.\n\nJacques-Bénigne BOSSUET."
"""
Multiline strings are always rendered in triple quotes. 
"""

A_LIST = [1,2,[5,6,[(11,22,33),9],10],11]+[99,98,97,96,95]
"""
Nested objects are colorized.
"""

FUNCTION_CALL = list(range(100)+[99,98,97,96,95])
"""
Function calls are colorized.
"""

OPERATORS = (1 << (10 | 1) << 1)
"""Operators are colorized and parenthesis are added when required."""

UNSUPPORTED = lambda x: demo_fields_docstring_arguments(x) // 2
"""
A lot of objects can be colorized: function calls, strings, lists, dicts, sets, frozensets, operators, annotations, names, compiled regular expressions, etc. 
But when dealing with usupported constructs, like lamba functions, it will display the value without colorization.
"""

RE_STR = re.compile("(foo (?P<a>bar) | (?P<boop>baz))")
"""
Regular expressions have special colorizing that add syntax highlight to the regex components.
"""

RE_WITH_UNICODE = re.compile("abc 😀")
"""
Unicode is supported in regular expressions.
"""

RE_INVALID = re.compile("^[")
"""
Ivalid regexes are still displayed on a best effort basis.
"""

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
