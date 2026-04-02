# Part of the sphinx.pycode.parser module.
# Copyright 2007-2020 by the Sphinx team, see AUTHORS.
# BSD, see LICENSE for details.
from __future__ import annotations

import ast
import inspect
import re
from token import DEDENT, INDENT, NAME, NEWLINE, NUMBER, OP, STRING
from tokenize import COMMENT, generate_tokens, tok_name
from typing import Any, Sequence

class Token:
    """
    Better token wrapper for tokenize module.
    
    Example usage:
    >>> from token import NAME
    >>> t = Token(NAME, 'foo', (1, 0), (1, 3), 'foo = 1')
    >>> t.kind
    1
    >>> t.value
    'foo'
    >>> t.start
    (1, 0)
    >>> t.end
    (1, 3)
    >>> t.source
    'foo = 1'
    >>> t == NAME
    True
    >>> t == 'foo'
    True
    >>> t == ['foo']  # Not matching kind+value, returns False
    False
    >>> t == None
    False
    >>> t.match(NAME, 'foo')
    True
    >>> repr(t)
    "<Token kind='NAME' value='foo'>"
    >>> t == 3.14
    False
    """

    def __init__(self, kind: int, 
                 value: str, 
                 start: tuple[int, int], 
                 end: tuple[int, int],
                 source: str) -> None:
        self.kind = kind
        self.value = value
        self.start = start
        self.end = end
        self.source = source #: Source line

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Token):
            return (self.kind == other.kind and
                self.value == other.value)
        elif isinstance(other, int):
            return self.kind == other
        elif isinstance(other, str):
            return self.value == other
        elif isinstance(other, list):
            return [self.kind, self.value] == other
        elif isinstance(other, tuple):
            return (self.kind, self.value) == other
        return NotImplemented

    def match(self, *conditions: Any) -> bool:
        return any(self == candidate for candidate in conditions)

    def __repr__(self) -> str:
        return '<Token kind=%r value=%r>' % (tok_name[self.kind],
                                             self.value.strip())

class TokenProcessor:
    r"""
    Processes tokens from source code lines.

    Example usage:
    >>> from token import NAME, OP, NUMBER, STRING
    >>> src = ["foo = 123 # comment\n"]
    >>> tp = TokenProcessor(src)
    >>> isinstance(tp.buffers, list)
    True

    # get_line returns the line at given lineno (1-based)
    >>> tp.get_line(1)
    'foo = 123 # comment\n'

    # fetch_token yields tokens one by one
    >>> t1 = tp.fetch_token()
    >>> t1.kind == NAME
    True
    >>> t2 = tp.fetch_token()
    >>> t2.kind == OP
    True
    >>> t3 = tp.fetch_token()
    >>> t3.kind == NUMBER
    True

    # previous and current attributes
    >>> tp.previous == t2
    True
    >>> tp.current == t3
    True

    # fetch_until collects tokens until matching condition
    >>> tp2 = TokenProcessor(["foo = (1 + 2)\n"])
    >>> tokens = tp2.fetch_until([OP, ')'])
    >>> any(t.value == ')' for t in tokens)
    True
    """

    def __init__(self, buffers: Sequence[str]) -> None:
        lines = iter(buffers)
        self.buffers = buffers
        self.tokens = generate_tokens(lambda: next(lines))
        self.current: Token | None = None
        self.previous: Token | None = None

    def get_line(self, lineno: int) -> str:
        """Returns specified line."""
        return self.buffers[lineno - 1]

    def fetch_token(self) -> Token | None:
        """Fetch a next token from source code.

        Returns ``None`` if sequence finished.
        """
        try:
            self.previous = self.current
            self.current = Token(*next(self.tokens))
        except StopIteration:
            self.current = None

        return self.current

    def fetch_until(self, condition: Any) -> list[Token]:
        """Fetch tokens until specified token appeared.

        .. note:: This also handles parenthesis well.
        """
        tokens = []
        while self.fetch_token():
            assert self.current
            tokens.append(self.current)
            if self.current == condition:
                break
            elif self.current == [OP, '(']:
                tokens += self.fetch_until([OP, ')'])
            elif self.current == [OP, '{']:
                tokens += self.fetch_until([OP, '}'])
            elif self.current == [OP, '[']:
                tokens += self.fetch_until([OP, ']'])

        return tokens


class AfterCommentParser(TokenProcessor):
    """Python source code parser to pick up comment after assignment.

    This parser takes a python code starts with assignment statement,
    and returns the comments for variable if exists.
    """

    def __init__(self, lines: Sequence[str]) -> None:
        super().__init__(lines)
        self.comment: str | None = None 

    def fetch_rvalue(self) -> Sequence[Token]:
        """Fetch right-hand value of assignment."""
        tokens: list[Token] = []
        while self.fetch_token():
            assert self.current
            tokens.append(self.current)
            if self.current == [OP, '(']:
                tokens += self.fetch_until([OP, ')'])
            elif self.current == [OP, '{']:
                tokens += self.fetch_until([OP, '}'])
            elif self.current == [OP, '[']:
                tokens += self.fetch_until([OP, ']'])
            elif self.current == INDENT:
                tokens += self.fetch_until(DEDENT)
            elif self.current == [OP, ';']:
                break
            elif self.current.kind not in (OP, NAME, NUMBER, STRING):
                break

        return tokens

    def parse(self) -> None:
        """Parse the code and obtain comment after assignment."""
        # skip lvalue (or whole of AnnAssign)
        while (current:=self.fetch_token()) and not current.match([OP, '='], NEWLINE, COMMENT):
            assert self.current
            continue

        # skip rvalue (if exists)
        if self.current == [OP, '=']:
            self.fetch_rvalue()

        if self.current == COMMENT:
            assert self.current
            self.comment = self.current.value

comment_re = re.compile('^\\s*#: ?(.*)\r?\n?$')
indent_re = re.compile('^\\s*$')

def extract_doc_comment_after(node: ast.Assign | ast.AnnAssign, lines: Sequence[str]) ->  tuple[int, str] | None:
    """
    Support for doc comment as found in sphinx.

    @param node: the assignment node
    @param lines: the lines of the source code of the module, as generated by
        C{code.splitlines(keepends=True)}.
    @returns: A tuple linenumber, docstring or None if the assignment doesn't have a doc comment.
    """
    # check doc comments after assignment
    current_line = lines[node.lineno - 1]
    parser = AfterCommentParser([current_line[node.col_offset:], *lines[node.lineno:]])
    parser.parse()
    if parser.comment and comment_re.match(parser.comment):
        docstring = comment_re.sub('\\1', parser.comment)
        return node.lineno, docstring

    return None

def extract_doc_comment_before(node: ast.Assign | ast.AnnAssign, lines: Sequence[str]) ->  tuple[int, str] | None:
    """
    Same as L{extract_doc_comment_after} but fetch the comment before the assignment.
    """
    # check doc comments before assignment
    comment_lines = []
    for i in range(node.lineno - 1):
        before_line = lines[node.lineno - 2 - i]
        if comment_re.match(before_line):
            comment_lines.append(comment_re.sub('\\1', before_line))
        else:
            break
    if comment_lines:
        docstring = inspect.cleandoc('\n'.join(reversed(comment_lines)))
        return node.lineno - len(comment_lines), docstring

    return None

# This was part of the sphinx.pycode.parser module.