"""
Various bits of reusable code related to L{ast.AST} node processing.
"""

import inspect
import platform
import sys
from numbers import Number
from typing import Iterator, Optional, List, Iterable, Sequence, TYPE_CHECKING, Tuple, Union, cast
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
    Generic AST node visitor. This class does not work like L{ast.NodeVisitor}, 
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

_AssingT = Union[ast.Assign, ast.AnnAssign]
def iterassign(node:_AssingT) -> Iterator[Optional[List[str]]]:
    """
    Utility function to iterate assignments targets. 

    Useful for all the following AST assignments:

    >>> var:int=2
    >>> self.var = target = node.astext()
    >>> lol = ['extensions']

    NOT Useful for the following AST assignments:

    >>> x, y = [1,2]

    Example:

    >>> from pydoctor.astutils import iterassign
    >>> from ast import parse
    >>> node = parse('self.var = target = thing[0] = node.astext()').body[0]
    >>> list(iterassign(node))
    
    """
    for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
        dottedname = node2dottedname(target) 
        yield dottedname

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
    # TODO: remove me when python3.7 is not supported anymore
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

def get_int_value(expr: ast.expr) -> Optional[int]:
    num = get_num_value(expr)
    if isinstance(num, int):
        return num # type:ignore[unreachable]
    return None

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

def is_none_literal(node: ast.expr) -> bool:
    """Does this AST node represent the literal constant None?"""
    if sys.version_info >= (3,8):
        # TODO: remove me when python3.7 is not supported anymore
        return isinstance(node, ast.Constant) and node.value is None
    else:
        return isinstance(node, (ast.Constant, ast.NameConstant)) and node.value is None
    
def unstring_annotation(node: ast.expr, ctx:'model.Documentable', section:str='annotation') -> ast.expr:
    """Replace all strings in the given expression by parsed versions.
    @return: The unstringed node. If parsing fails, an error is logged
        and the original node is returned.
    """
    try:
        expr = _AnnotationStringParser().visit(node)
    except SyntaxError as ex:
        module = ctx.module
        assert module is not None
        module.report(f'syntax error in {section}: {ex}', lineno_offset=node.lineno, section=section)
        return node
    else:
        assert isinstance(expr, ast.expr), expr
        return expr

class _AnnotationStringParser(ast.NodeTransformer):
    """Implementation of L{unstring_annotation()}.

    When given an expression, the node returned by L{ast.NodeVisitor.visit()}
    will also be an expression.
    If any string literal contained in the original expression is either
    invalid Python or not a singular expression, L{SyntaxError} is raised.
    """

    def _parse_string(self, value: str) -> ast.expr:
        statements = ast.parse(value).body
        if len(statements) != 1:
            raise SyntaxError("expected expression, found multiple statements")
        stmt, = statements
        if isinstance(stmt, ast.Expr):
            # Expression wrapped in an Expr statement.
            expr = self.visit(stmt.value)
            assert isinstance(expr, ast.expr), expr
            return expr
        else:
            raise SyntaxError("expected expression, found statement")

    def visit_Subscript(self, node: ast.Subscript) -> ast.Subscript:
        value = self.visit(node.value)
        if isinstance(value, ast.Name) and value.id == 'Literal':
            # Literal[...] expression; don't unstring the arguments.
            slice = node.slice
        elif isinstance(value, ast.Attribute) and value.attr == 'Literal':
            # typing.Literal[...] expression; don't unstring the arguments.
            slice = node.slice
        else:
            # Other subscript; unstring the slice.
            slice = self.visit(node.slice)
        return ast.copy_location(ast.Subscript(value, slice, node.ctx), node)

    # For Python >= 3.8:

    def visit_Constant(self, node: ast.Constant) -> ast.expr:
        value = node.value
        if isinstance(value, str):
            return ast.copy_location(self._parse_string(value), node)
        else:
            const = self.generic_visit(node)
            assert isinstance(const, ast.Constant), const
            return const

    # For Python < 3.8:
    if sys.version_info < (3,8):
        # TODO: remove me when python3.7 is not supported anymore
        def visit_Str(self, node: ast.Str) -> ast.expr:
            return ast.copy_location(self._parse_string(node.s), node)

TYPING_ALIAS = (
        "typing.Hashable",
        "typing.Awaitable",
        "typing.Coroutine",
        "typing.AsyncIterable",
        "typing.AsyncIterator",
        "typing.Iterable",
        "typing.Iterator",
        "typing.Reversible",
        "typing.Sized",
        "typing.Container",
        "typing.Collection",
        "typing.Callable",
        "typing.AbstractSet",
        "typing.MutableSet",
        "typing.Mapping",
        "typing.MutableMapping",
        "typing.Sequence",
        "typing.MutableSequence",
        "typing.ByteString",
        "typing.Tuple",
        "typing.List",
        "typing.Deque",
        "typing.Set",
        "typing.FrozenSet",
        "typing.MappingView",
        "typing.KeysView",
        "typing.ItemsView",
        "typing.ValuesView",
        "typing.ContextManager",
        "typing.AsyncContextManager",
        "typing.Dict",
        "typing.DefaultDict",
        "typing.OrderedDict",
        "typing.Counter",
        "typing.ChainMap",
        "typing.Generator",
        "typing.AsyncGenerator",
        "typing.Type",
        "typing.Pattern",
        "typing.Match",
        # Special forms
        "typing.Union",
        "typing.Literal",
        "typing.Optional",
    )

SUBSCRIPTABLE_CLASSES_PEP585 = (
        "tuple",
        "list",
        "dict",
        "set",
        "frozenset",
        "type",
        "collections.deque",
        "collections.defaultdict",
        "collections.OrderedDict",
        "collections.Counter",
        "collections.ChainMap",
        "collections.abc.Awaitable",
        "collections.abc.Coroutine",
        "collections.abc.AsyncIterable",
        "collections.abc.AsyncIterator",
        "collections.abc.AsyncGenerator",
        "collections.abc.Iterable",
        "collections.abc.Iterator",
        "collections.abc.Generator",
        "collections.abc.Reversible",
        "collections.abc.Container",
        "collections.abc.Collection",
        "collections.abc.Callable",
        "collections.abc.Set",
        "collections.abc.MutableSet",
        "collections.abc.Mapping",
        "collections.abc.MutableMapping",
        "collections.abc.Sequence",
        "collections.abc.MutableSequence",
        "collections.abc.ByteString",
        "collections.abc.MappingView",
        "collections.abc.KeysView",
        "collections.abc.ItemsView",
        "collections.abc.ValuesView",
        "contextlib.AbstractContextManager",
        "contextlib.AbstractAsyncContextManager",
        "re.Pattern",
        "re.Match",
    )

def is_typing_annotation(node: ast.AST, ctx: 'model.Documentable') -> bool:
    """
    Whether this annotation node refers to a typing alias.
    """
    return is_using_annotations(node, TYPING_ALIAS, ctx) or \
            is_using_annotations(node, SUBSCRIPTABLE_CLASSES_PEP585, ctx)

def get_docstring_node(node: ast.AST) -> ast.Constant | None:
    """
    Return the docstring node for the given class, function or module
    or None if no docstring can be found.
    """
    if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module)) or not node.body:
        return None
    node = node.body[0]
    if isinstance(node, ast.Expr):
        v = get_str_value(node.value)
        if v is not None:
            return cast('ast.Constant | None', node.value)
    return None

_string_lineno_is_end = sys.version_info < (3,8) \
                    and platform.python_implementation() != 'PyPy'
"""True iff the 'lineno' attribute of an AST string node points to the last
line in the string, rather than the first line.
"""

def extract_docstring_linenum(node: ast.Constant) -> int:
    r"""
    In older CPython versions, the AST only tells us the end line
    number and we must approximate the start line number.
    This approximation is correct if the docstring does not contain
    explicit newlines ('\n') or joined lines ('\' at end of line).

    Leading blank lines are stripped by cleandoc(), so we must
    return the line number of the first non-blank line.
    """
    doc = str(node.value)
    lineno = node.lineno
    if _string_lineno_is_end:
        # In older CPython versions, the AST only tells us the end line
        # number and we must approximate the start line number.
        # This approximation is correct if the docstring does not contain
        # explicit newlines ('\n') or joined lines ('\' at end of line).
        lineno -= doc.count('\n')

    # Leading blank lines are stripped by cleandoc(), so we must
    # return the line number of the first non-blank line.
    for ch in doc:
        if ch == '\n':
            lineno += 1
        elif not ch.isspace():
            break
    
    return lineno

def extract_docstring(node: ast.Constant) -> Tuple[int, str]:
    """
    Extract docstring information from an ast node that represents the docstring.

    @returns: 
        - The line number of the first non-blank line of the docsring. See L{extract_docstring_linenum}.
        - The docstring to be parsed, cleaned by L{inspect.cleandoc}.
    """
    value = get_str_value(node)
    if value is None:
        raise TypeError(f'expected string constant, got {type(node.value)}')
    lineno = extract_docstring_linenum(node)
    return lineno, inspect.cleandoc(value)


def infer_type(expr: ast.expr) -> Optional[ast.expr]:
    """Infer a literal expression's type.
    @param expr: The expression's AST.
    @return: A type annotation, or None if the expression has no obvious type.
    """
    try:
        value: object = ast.literal_eval(expr)
    except (ValueError, TypeError):
        return None
    else:
        ann = _annotation_for_value(value)
        if ann is None:
            return None
        else:
            return ast.fix_missing_locations(ast.copy_location(ann, expr))

def _annotation_for_value(value: object) -> Optional[ast.expr]:
    if value is None:
        return None
    name = type(value).__name__
    if isinstance(value, (dict, list, set, tuple)):
        ann_elem = _annotation_for_elements(value)
        if isinstance(value, dict):
            ann_value = _annotation_for_elements(value.values())
            if ann_value is None:
                ann_elem = None
            elif ann_elem is not None:
                ann_elem = ast.Tuple(elts=[ann_elem, ann_value])
        if ann_elem is not None:
            if name == 'tuple':
                ann_elem = ast.Tuple(elts=[ann_elem, ast.Constant(value=...)])
            return ast.Subscript(value=ast.Name(id=name),
                                 slice=ast.Index(value=ann_elem))
    return ast.Name(id=name)

def _annotation_for_elements(sequence: Iterable[object]) -> Optional[ast.expr]:
    names = set()
    for elem in sequence:
        ann = _annotation_for_value(elem)
        if isinstance(ann, ast.Name):
            names.add(ann.id)
        else:
            # Nested sequences are too complex.
            return None
    if len(names) == 1:
        name = names.pop()
        return ast.Name(id=name)
    else:
        # Empty sequence or no uniform type.
        return None

      
class Parentage(ast.NodeTransformer):
    """
    Add C{parent} attribute to ast nodes instances.
    """
    # stolen from https://stackoverflow.com/a/68845448
    parent: Optional[ast.AST] = None

    def visit(self, node: ast.AST) -> ast.AST:
        setattr(node, 'parent', self.parent)
        self.parent = node
        node = super().visit(node)
        if isinstance(node, ast.AST):
            self.parent = getattr(node, 'parent')
        return node

def get_parents(node:ast.AST) -> Iterator[ast.AST]:
    """
    Once nodes have the C{.parent} attribute with {Parentage}, use this function
    to get a iterator on all parents of the given node up to the root module.
    """
    def _yield_parents(n:Optional[ast.AST]) -> Iterator[ast.AST]:
        if n:
            yield n
            p = cast(ast.AST, getattr(n, 'parent', None))
            yield from _yield_parents(p)
    yield from _yield_parents(getattr(node, 'parent', None))

