"""
Provides a modified L{fnmatch} function specialized for python objects fully qualified name pattern matching.

Special patterns are::

    **      matches everything (recursive)
    *       matches everything except "." (one level ony)
    ?       matches any single character
    [seq]   matches any character in seq
    [!seq]  matches any char not in seq
"""
import functools
import re
from typing import Any, Callable

@functools.lru_cache(maxsize=256, typed=True)
def _compile_pattern(pat: str) -> Callable[[str], Any]:
    res = translate(pat)
    return re.compile(res).match

def qnmatch(name:str, pattern:str) -> bool:
    """Test whether C{name} matches C{pattern}.
    """
    match = _compile_pattern(pattern)
    return match(name) is not None

# Barely changed from https://github.com/python/cpython/blob/3.8/Lib/fnmatch.py
# Not using python3.9+ version because implementation is significantly more complex.
def translate(pat:str) -> str:
    """Translate a shell PATTERN to a regular expression.
    There is no way to quote meta-characters.
    """
    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            # Changes begins: understands '**'.
            if i < n and pat[i] == '*':
                res = res + '.*?'
                i = i + 1
            else:
                res = res + r'[^\.]*?'
            # Changes ends.
        elif c == '?':
            res = res + '.'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j]
                # Changes begins: simplifications handling backslashes and hyphens not required for fully qualified names.
                stuff = stuff.replace('\\', r'\\')
                i = j+1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] in ('^', '['):
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
                # Changes ends.
        else:
            res = res + re.escape(c)
    return r'(?s:%s)\Z' % res
