#
# doctest.py: Syntax Highlighting for doctest blocks
# Edward Loper
#
# Created [06/28/03 02:52 AM]
#

"""
Syntax highlighting for blocks of Python code.
"""

__docformat__ = 'epytext en'

import builtins
import re
import sys

from twisted.web.template import tags

__all__ = ['colorize_codeblock', 'colorize_doctest']

#: A list of the names of all Python keywords.
_KEYWORDS = [
    'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
    'elif', 'else', 'except', 'finally', 'for', 'from', 'global',
    'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass',
    'raise', 'return', 'try', 'while', 'with', 'yield'
    ]
if sys.version_info.major == 2:
    # These became builtins in Python 3.
    _KEYWORDS += ['exec', 'print']
else:
    _KEYWORDS += ['async', 'await', 'nonlocal']
    # These are technically keywords since Python 3,
    # but we don't want to colorize them as such:
    #_KEYWORDS += ['None', 'True', 'False']

#: A list of all Python builtins.
_BUILTINS = [_BI for _BI in dir(builtins) if not _BI.startswith('__')]

#: A regexp group that matches keywords.
_KEYWORD_GRP = '|'.join(r'\b%s\b' % _KW for _KW in _KEYWORDS)

#: A regexp group that matches Python builtins.
_BUILTIN_GRP = r'(?<!\.)(?:%s)' % '|'.join(r'\b%s\b' % _BI for _BI in _BUILTINS)

#: A regexp group that matches Python strings.
_STRING_GRP = '|'.join(
    [r'("""("""|.*?((?!").)"""))', r'("("|.*?((?!").)"))',
     r"('''('''|.*?[^\\']'''))", r"('('|.*?[^\\']'))"])

#: A regexp group that matches Python comments.
_COMMENT_GRP = '(#.*?$)'

#: A regexp group that matches Python ">>>" prompts.
_PROMPT1_GRP = r'^[ \t]*>>>(?:[ \t]|$)'

#: A regexp group that matches Python "..." prompts.
_PROMPT2_GRP = r'^[ \t]*\.\.\.(?:[ \t]|$)'

#: A regexp group that matches function and class definitions.
_DEFINE_GRP = r'\b(?:def|class)[ \t]+\w+'

#: A regexp that decomposes function definitions.
DEFINE_FUNC_RE = re.compile(r'(?P<def>\w+)(?P<space>\s+)(?P<name>\w+)')

#: A regexp that matches Python prompts
PROMPT_RE = re.compile('(%s|%s)' % (_PROMPT1_GRP, _PROMPT2_GRP),
                       re.MULTILINE | re.DOTALL)

#: A regexp that matches Python "..." prompts.
PROMPT2_RE = re.compile('(%s)' % _PROMPT2_GRP,
                        re.MULTILINE | re.DOTALL)

#: A regexp that matches doctest exception blocks.
EXCEPT_RE = re.compile(r'^[ \t]*Traceback \(most recent call last\):.*',
                       re.DOTALL | re.MULTILINE)

#: A regexp that matches doctest directives.
DOCTEST_DIRECTIVE_RE = re.compile(r'#[ \t]*doctest:.*')

#: A regexp that matches all of the regions of a doctest block
#: that should be colored.
DOCTEST_RE = re.compile(
    '('
        r'(?P<STRING>%s)|(?P<COMMENT>%s)|(?P<DEFINE>%s)|'
        r'(?P<KEYWORD>%s)|(?P<BUILTIN>%s)|'
        r'(?P<PROMPT1>%s)|(?P<PROMPT2>%s)|(?P<EOS>\Z)'
    ')' % (
        _STRING_GRP, _COMMENT_GRP, _DEFINE_GRP, _KEYWORD_GRP, _BUILTIN_GRP,
        _PROMPT1_GRP, _PROMPT2_GRP
        ),
    re.MULTILINE | re.DOTALL)

#: This regular expression is used to find doctest examples in a
#: string.  This is copied from the standard Python doctest.py
#: module (after the refactoring in Python 2.4+).
DOCTEST_EXAMPLE_RE = re.compile(r'''
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

def colorize_codeblock(s):
    """
    Colorize a string containing only Python code.  This method
    differs from L{colorize_doctest} in that it will not search
    for doctest prompts when deciding how to colorize the string.

    This code consists of a C{<pre>} block with class=py-doctest.
    Syntax highlighting is performed using the following CSS classes:

      - C{py-keyword} -- a Python keyword (for, if, etc.)
      - C{py-builtin} -- a Python builtin name (abs, dir, etc.)
      - C{py-string} -- a string literal
      - C{py-comment} -- a comment
      - C{py-except} -- an exception traceback (up to the next >>>)
      - C{py-output} -- the output from a doctest block.
      - C{py-defname} -- the name of a function or class defined by
        a C{def} or C{class} statement.
    """

    return tags.pre('\n', *colorize_codeblock_body(s), class_='py-doctest')

def colorize_doctest(s):
    """
    Perform syntax highlighting on the given doctest string, and
    return the resulting HTML code.

    This code consists of a C{<pre>} block with class=py-doctest.
    Syntax highlighting is performed using the following CSS classes:

      - C{py-prompt} -- the Python PS1 prompt (>>>)
      - C{py-more} -- the Python PS2 prompt (...)
      - the CSS classes output by L{colorize_codeblock}
    """

    return tags.pre('\n', *colorize_doctest_body(s), class_='py-doctest')

def colorize_doctest_body(s):
    idx = 0
    for match in DOCTEST_EXAMPLE_RE.finditer(s):
        # Parse the doctest example:
        pysrc, want = match.group('source', 'want')
        # Pre-example text:
        yield s[idx:match.start()]
        # Example source code:
        yield from colorize_codeblock_body(pysrc)
        # Example output:
        if want:
            style = 'py-except' if EXCEPT_RE.match(want) else 'py-output'
            for line in want.rstrip().split('\n'):
                yield tags.span(line, class_=style)
                yield '\n'
        idx = match.end()
    # Add any remaining post-example text.
    yield s[idx:]

def colorize_codeblock_body(s):
    idx = 0
    for match in DOCTEST_RE.finditer(s):
        start = match.start()
        if idx < start:
            yield s[idx:start]
        yield from subfunc(match)
        idx = match.end()
    # DOCTEST_RE matches end-of-string.
    assert idx == len(s)

def subfunc(match):
    text = match.group(1)
    if match.group('PROMPT1'):
        yield tags.span(text, class_='py-prompt')
    elif match.group('PROMPT2'):
        yield tags.span(text, class_='py-more')
    elif match.group('KEYWORD'):
        yield tags.span(text, class_='py-keyword')
    elif match.group('BUILTIN'):
        yield tags.span(text, class_='py-builtin')
    elif match.group('COMMENT'):
        yield tags.span(text, class_='py-comment')
    elif match.group('STRING'):
        idx = 0
        while True:
            nxt = text.find('\n', idx)
            line = text[idx:] if nxt == -1 else text[idx:nxt]
            m = PROMPT2_RE.match(line)
            if m:
                prompt_end = m.end()
                yield tags.span(line[:prompt_end], class_='py-more')
                line = line[prompt_end:]
            if line:
                yield tags.span(line, class_='py-string')
            if nxt == -1:
                break
            yield '\n'
            idx = nxt + 1
    elif match.group('DEFINE'):
        m = DEFINE_FUNC_RE.match(text)
        yield tags.span(m.group('def'), class_='py-keyword')
        yield m.group('space')
        yield tags.span(m.group('name'), class_='py-defname')
    elif match.group('EOS') is None:
        raise AssertionError('Unexpected match')
