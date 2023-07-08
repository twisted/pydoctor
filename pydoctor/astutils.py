"""
Various bits of reusable code related to L{ast.AST} node processing.
"""

import enum
import inspect
import platform
import sys
from numbers import Number
from typing import Any, Iterator, Optional, List, Iterable, Sequence, TYPE_CHECKING, Tuple, Union, Type, TypeVar, Generic
from inspect import BoundArguments, Signature, Parameter
import ast

from pydoctor import visitor

if TYPE_CHECKING:
    from pydoctor import model
    from typing import Protocol, Literal, TypeGuard
else:
    Protocol = Literal = TypeGuard = object

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

class _HasDecoratorList(Protocol):
    decorator_list:List[ast.expr]

def iter_decorators(node:_HasDecoratorList, ctx: 'model.Documentable') -> Iterator[Tuple[Optional[str], ast.AST]]:
    """
    Utility function to iterate decorators.
    """

    for decnode in node.decorator_list:
        namenode = decnode
        if isinstance(namenode, ast.Call):
            namenode = namenode.func
        dottedname = node2fullname(namenode, ctx)
        yield dottedname, decnode

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

def dottedname2node(parts:List[str]) -> Union[ast.Name, ast.Attribute]:
    """
    Reverse operation of L{node2dottedname}.
    """
    assert parts, "must not be empty"
    
    if len(parts)==1:
        return ast.Name(parts[0], ast.Load())
    else:
        return ast.Attribute(dottedname2node(parts[:-1]), parts[-1], ast.Load())

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
    return isinstance(node, (ast.Constant, ast.NameConstant)) and node.value is None
    
def unstring_annotation(node: ast.expr, ctx:'model.Documentable') -> ast.expr:
    """Replace all strings in the given expression by parsed versions.
    @return: The unstringed node. If parsing fails, an error is logged
        and the original node is returned.
    """
    try:
        expr = _AnnotationStringParser().visit(node)
    except SyntaxError as ex:
        module = ctx.module
        assert module is not None
        module.report(f'syntax error in annotation: {ex}', lineno_offset=node.lineno)
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


_string_lineno_is_end = sys.version_info < (3,8) \
                    and platform.python_implementation() != 'PyPy'
"""True iff the 'lineno' attribute of an AST string node points to the last
line in the string, rather than the first line.
"""

def extract_docstring_linenum(node: ast.Str) -> int:
    r"""
    In older CPython versions, the AST only tells us the end line
    number and we must approximate the start line number.
    This approximation is correct if the docstring does not contain
    explicit newlines ('\n') or joined lines ('\' at end of line).

    Leading blank lines are stripped by cleandoc(), so we must
    return the line number of the first non-blank line.
    """
    doc = node.s
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

def extract_docstring(node: ast.Str) -> Tuple[int, str]:
    """
    Extract docstring information from an ast node that represents the docstring.

    @returns: 
        - The line number of the first non-blank line of the docsring. See L{extract_docstring_linenum}.
        - The docstring to be parsed, cleaned by L{inspect.cleandoc}.
    """
    lineno = extract_docstring_linenum(node)
    return lineno, inspect.cleandoc(node.s)

def safe_bind_args(sig:Signature, call: ast.AST, ctx: 'model.Module') -> Optional[inspect.BoundArguments]:
    """
    Binds the arguments of a function call to that function's signature.

    When L{bind_args} raises a L{TypeError}, it reports a warning and returns C{None}. 
    """
    if not isinstance(call, ast.Call):
        return None
    try:
        return bind_args(sig, call)
    except TypeError as ex:
        message = str(ex).replace("'", '"')
        call_dottedname = node2dottedname(call.func)
        callable_name = f"{'.'.join(call_dottedname)}()" if call_dottedname else 'callable'
        ctx.report(
            f"Invalid arguments for {callable_name}: {message}",
            lineno_offset=call.lineno
            )
        return None
    
class _V(enum.Enum): 
    NoValue = enum.auto()
_T =  TypeVar('_T', bound=object)
def _get_literal_arg(args:BoundArguments, name:str, 
                     typecheck:'type[_T]|tuple[type[_T],...]') -> Union['Literal[_V.NoValue]', _T]:
    """
    Helper function for L{get_literal_arg}. 

    If the value is not present in the arguments, returns L{_V.NoValue}.
    @raises ValueError: If the passed value is not a literal or if it's not the right type.
    """
    expr = args.arguments.get(name)
    if expr is None:
        return _V.NoValue

    try:
        value = ast.literal_eval(expr)
    except ValueError:
        message = (
            f'Unable to figure out value for {name!r} argument, maybe too complex'
            ).replace("'", '"')
        raise ValueError(message)

    if not isinstance(value, typecheck):
        expected_type = " or ".join(repr(t.__name__) for t in (typecheck if isinstance(typecheck, tuple) else (typecheck,)))
        message = (f'Value for {name!r} argument '
            f'has type "{type(value).__name__}", expected {expected_type}'
            ).replace("'", '"')
        raise ValueError(message)

    return value

def get_literal_arg(args:BoundArguments, name:str, default:_T, 
                          typecheck:'type[_T]|tuple[type[_T],...]', 
                          lineno:int, module: 'model.Module') -> _T:
    """
    Retreive the literal value of an argument from the L{BoundArguments}. 
    Only works with purely literal values (no C{Name} or C{Attribute}).
    
    @param args: The L{BoundArguments} instance.
    @param name: The name of the argument
    @param default: The default value of the argument, this value is returned 
        if the argument is not found.
    @param typecheck: The type of the literal value this argument is expected to have.
    @param lineno: The lineumber of the callsite, used for error reporting.
    @param module: Module that contains the call, used for error reporting.
    @return: The value of the argument if we can infer it, otherwise returns
        the default value.
    """
    try:
        value = _get_literal_arg(args, name, typecheck)
    except ValueError as e:
        module.report(str(e), lineno_offset=lineno)
        return default
    if value is _V.NoValue:
        # default value
        return default
    else:
        return value

_TC =  TypeVar('_TC', bound=object)
_SCOPE_TYPES = (ast.SetComp, ast.DictComp, ast.ListComp, ast.GeneratorExp, 
           ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

class _Collector(ast.NodeVisitor, Generic[_TC]):
    
    def __init__(self, 
                 typecheck:Union[Type[_TC], Tuple[Type[_TC],...]],
                 stop_typecheck: Union[Type[Any], Tuple[Type[Any],...]],
                 ):
        self.collected:List[_TC] = []
        self.typecheck = typecheck
        self.stop_typecheck = stop_typecheck
    
    def _collect(self, node:ast.AST) -> None:
        if isinstance(node, self.typecheck):
            self.collected.append(node)

    def generic_visit(self, node: ast.AST) -> Any:
        self._collect(node)
        if not isinstance(node, self.stop_typecheck):
            return super().generic_visit(node)

def _collect_nodes(node:ast.AST, typecheck:Union[Type[_TC], Tuple[Type[_TC],...]],
                   stop_typecheck:Union[Type[Any], Tuple[Type[Any],...]]=_SCOPE_TYPES) -> Sequence[_TC]:
    visitor:_Collector[_TC] = _Collector(typecheck, stop_typecheck)
    ast.NodeVisitor.generic_visit(visitor, node)
    return visitor.collected

def collect_assigns(node:ast.AST) -> Sequence[Union[ast.Assign, ast.AnnAssign]]:
    """
    Returns a list of L{ast.Assign} or L{ast.AnnAssign} declared in the given scope.
    It does not include assignments in nested scopes.
    """
    return _collect_nodes(node, (ast.Assign, ast.AnnAssign))
