"""
Various bits of reusable code related to L{ast.AST} node processing.
"""

import sys
from typing import Optional, List
from inspect import BoundArguments, Signature
import ast

def node2dottedname(node: Optional[ast.expr]) -> Optional[List[str]]:
    """
    Resove expression composed by L{ast.Attribute} and L{ast.Name} nodes to a list of names. 
    """
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    else:
        return None
    parts.reverse()
    return parts

def bind_args(sig: Signature, call: ast.Call) -> BoundArguments:
    """
    Binds the arguments of a function call to that function's signature.
    @raise TypeError: If the arguments do not match the signature.
    """
    kwargs = {
        kw.arg: kw.value
        for kw in call.keywords
        # When keywords are passed using '**kwargs', the 'arg' field will
        # be None. We don't currently support keywords passed that way.
        if kw.arg is not None
        }
    return sig.bind(*call.args, **kwargs)


if sys.version_info[:2] >= (3, 8):
    # Since Python 3.8 "foo" is parsed as ast.Constant.
    def _is_str_constant(expr: ast.expr, s: str) -> bool:
        return isinstance(expr, ast.Constant) and expr.value == s
else:
    # Before Python 3.8 "foo" was parsed as ast.Str.
    def _is_str_constant(expr: ast.expr, s: str) -> bool:
        return isinstance(expr, ast.Str) and expr.s == s

def is__name__equals__main__(cmp: ast.Compare) -> bool:
    """
    Returns whether or not the given L{ast.Compare} is equal to C{__name__ == '__main__'}.
    """
    return isinstance(cmp.left, ast.Name) \
    and cmp.left.id == '__name__' \
    and len(cmp.ops) == 1 \
    and isinstance(cmp.ops[0], ast.Eq) \
    and len(cmp.comparators) == 1 \
    and _is_str_constant(cmp.comparators[0], '__main__')
