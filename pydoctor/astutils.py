"""
Various bits of reusable code related to L{ast.AST} node processing.
"""

import sys
from numbers import Number
from typing import Iterator, Optional, List, Iterable, Sequence, TYPE_CHECKING
from inspect import BoundArguments, Signature
import ast

from pydoctor import visitor

if TYPE_CHECKING:
    from pydoctor import model

# AST visitors

def iter_values(node: ast.AST) -> Iterator[ast.AST]:
    for _, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield item
        elif isinstance(value, ast.AST):
            yield value

class NodeVisitor(visitor.PartialVisitor[ast.AST]):
    """
    Generic AST node visitor. This class does not work like L{ast.NoseVisitor}, 
    it only visits statements directly within a C{B{body}}. Also, visitor methods can't return anything.

    :See: L{visitor} for more informations.
    """
    def generic_visit(self, node: ast.AST) -> None:
        """
        Helper method to visit a node by calling C{visit()} on each child of the node. 
        This is useful because this vistitor only visits statements inside C{.body} attribute. 
        
        So if one wants to visit L{ast.Expr} children with their visitor, they should include::

            def visit_Expr(self, node:ast.Expr):
                self.generic_visit(node)
        """
        for v in iter_values(node):
            self.visit(v)
    
    @classmethod
    def get_children(cls, node: ast.AST) -> Iterable[ast.AST]:
        """
        Returns the nested nodes in the body of a node.
        """
        body: Optional[Sequence[ast.AST]] = getattr(node, 'body', None)
        if body is not None:
            for child in body:
                yield child

class NodeVisitorExt(visitor.VisitorExt[ast.AST]):
    ...

def node2dottedname(node: Optional[ast.AST]) -> Optional[List[str]]:
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

def node2fullname(expr: Optional[ast.AST], ctx: 'model.Documentable') -> Optional[str]:
    dottedname = node2dottedname(expr)
    if dottedname is None:
        return None
    return ctx.expandName('.'.join(dottedname))

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
    def get_str_value(expr:ast.expr) -> Optional[str]:
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return expr.value
        return None
    def get_num_value(expr:ast.expr) -> Optional[Number]:
        if isinstance(expr, ast.Constant) and isinstance(expr.value, Number):
            return expr.value
        return None
    def _is_str_constant(expr: ast.expr, s: str) -> bool:
        return isinstance(expr, ast.Constant) and expr.value == s
else:
    # Before Python 3.8 "foo" was parsed as ast.Str.
    def get_str_value(expr:ast.expr) -> Optional[str]:
        if isinstance(expr, ast.Str):
            return expr.s
        return None
    def get_num_value(expr:ast.expr) -> Optional[Number]:
        if isinstance(expr, ast.Num):
            return expr.n
        return None
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

def is_using_typing_final(expr: Optional[ast.AST], 
                    ctx:'model.Documentable') -> bool:
    return is_using_annotations(expr, ("typing.Final", "typing_extensions.Final"), ctx)

def is_using_typing_classvar(expr: Optional[ast.AST], 
                    ctx:'model.Documentable') -> bool:
    return is_using_annotations(expr, ('typing.ClassVar', "typing_extensions.ClassVar"), ctx)

def is_using_annotations(expr: Optional[ast.AST], 
                            annotations:Sequence[str], 
                            ctx:'model.Documentable') -> bool:
    """
    Detect if this expr is firstly composed by one of the specified annotation(s)' full name.
    """
    full_name = node2fullname(expr, ctx)
    if full_name in annotations:
        return True
    if isinstance(expr, ast.Subscript):
        # Final[...] or typing.Final[...] expressions
        if isinstance(expr.value, (ast.Name, ast.Attribute)):
            value = expr.value
            full_name = node2fullname(value, ctx)
            if full_name in annotations:
                return True
    return False
