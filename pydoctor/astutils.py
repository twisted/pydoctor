"""
Various bits of reusable code related to L{ast.AST} node processing.
"""

from typing import Optional, List, TYPE_CHECKING, Union
from inspect import BoundArguments, Signature
import ast

if TYPE_CHECKING:
    from pydoctor.model import Documentable

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

def node2fullname(expr: Optional[Union[ast.expr, str]], ctx: 'Documentable') -> Optional[str]:
    """
    Return L{ctx.expandName(name)} if C{expr} is a valid name, or C{None}.
    """
    dottedname = node2dottedname(expr) if isinstance(expr, ast.expr) else expr
    if dottedname is None:
        return None
    return ctx.expandName('.'.join(dottedname))