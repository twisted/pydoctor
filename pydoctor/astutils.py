"""
Various bits of reusable code related to L{ast.AST} node processing.
"""
from __future__ import annotations

import inspect
import sys
from numbers import Number
from typing import Any, Callable, Collection, Iterator, Optional, List, Iterable, Sequence, TYPE_CHECKING, Tuple, Union, cast
from inspect import BoundArguments, Signature
import ast

unparse = ast.unparse

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

    Useful for all the following AST assignments::

        var:int=2
        self.var = target = node.astext()
        ol = ['extensions']

    NOT Useful for the following AST assignments::

        x, y = [1,2]

    Example:

    >>> from pydoctor.astutils import iterassign
    >>> from ast import parse
    >>> node = parse('self.var = target = thing[0] = node.astext()').body[0]
    >>> list(iterassign(node))
    [['self', 'var'], ['target'], None]
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

def node2fullname(expr: Optional[ast.AST], 
                  ctx: model.Documentable | None = None, 
                  *,
                  expandName:Callable[[str], str] | None = None) -> Optional[str]:
    if expandName is None:
        if ctx is None:
            raise TypeError('this function takes exactly two arguments')
        expandName = ctx.expandName
    elif ctx is not None:
        raise TypeError('this function takes exactly two arguments')

    dottedname = node2dottedname(expr)
    if dottedname is None:
        return None
    return expandName('.'.join(dottedname))

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

def get_node_block(node: ast.AST) -> tuple[ast.AST, str]:
    """
    Tell in wich block the given node lives in. 
    
    A block is defined by a tuple: (parent node, fieldname)
    """
    try:
        parent = next(get_parents(node))
    except StopIteration:
        raise ValueError(f'node has no parents: {node}')
    for fieldname, value in ast.iter_fields(parent):
        if value is node or (isinstance(value, (list, tuple)) and node in value):
            break
    else:
        raise ValueError(f"node {node} not found in {parent}")
    return parent, fieldname

def get_assign_docstring_node(assign:ast.Assign | ast.AnnAssign) -> Str | None:
    """
    Get the docstring for a L{ast.Assign} or L{ast.AnnAssign} node.

    This helper function relies on the non-standard C{.parent} attribute on AST nodes
    to navigate upward in the tree and determine this node direct siblings.
    """
    # if this call raises an ValueError it means that we're doing something nasty with the ast...
    parent_node, fieldname = get_node_block(assign)
    statements = getattr(parent_node, fieldname, None)
    
    if isinstance(statements, Sequence):
        # it must be a sequence if it's not None since an assignment 
        # can only be a part of a compound statement.
        assign_index = statements.index(assign)
        try:
            right_sibling = statements[assign_index+1]
        except IndexError:
            return None
        if isinstance(right_sibling, ast.Expr) and \
           get_str_value(right_sibling.value) is not None:
            return cast(Str, right_sibling.value)
    return None

def is_none_literal(node: ast.expr) -> bool:
    """Does this AST node represent the literal constant None?"""
    return isinstance(node, ast.Constant) and node.value is None
    
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
        return ast.copy_location(ast.Subscript(value=value, slice=slice, ctx=node.ctx), node)

    def visit_fast(self, node: ast.expr) -> ast.expr:
        return node
    
    visit_Attribute = visit_Name = visit_fast

    def visit_Constant(self, node: ast.Constant) -> ast.expr:
        value = node.value
        if isinstance(value, str):
            return ast.copy_location(self._parse_string(value), node)
        else:
            const = self.generic_visit(node)
            assert isinstance(const, ast.Constant), const
            return const

def upgrade_annotation(node: ast.expr, ctx: model.Documentable, section:str='annotation') -> ast.expr:
    """
    Transform the annotation to use python 3.10+ syntax. 
    """
    return _UpgradeDeprecatedAnnotations(ctx).visit(node)

class _UpgradeDeprecatedAnnotations(ast.NodeTransformer):
    if TYPE_CHECKING:
        def visit(self, node:ast.AST) -> ast.expr:...

    def __init__(self, ctx: model.Documentable) -> None:
        def _node2fullname(node:ast.expr) -> str | None:
            return node2fullname(node, expandName=ctx.expandAnnotationName)
        self.node2fullname = _node2fullname

    def _union_args_to_bitor(self, args: list[ast.expr], ctxnode:ast.AST) -> ast.BinOp:
        assert len(args) > 1
        *others, right = args
        if len(others) == 1:
            rnode = ast.BinOp(left=others[0], right=right, op=ast.BitOr())
        else:
            rnode = ast.BinOp(left=self._union_args_to_bitor(others, ctxnode), right=right, op=ast.BitOr())
    
        return ast.fix_missing_locations(ast.copy_location(rnode, ctxnode))

    def visit_Name(self, node: ast.Name | ast.Attribute) -> Any:
        fullName = self.node2fullname(node)
        if fullName in DEPRECATED_TYPING_ALIAS_BUILTINS:
            return ast.Name(id=DEPRECATED_TYPING_ALIAS_BUILTINS[fullName], ctx=ast.Load())
        # TODO: Support all deprecated aliases including the ones in the collections.abc module.
        # In order to support that we need to generate the parsed docstring directly and include 
        # custom refmap or transform the ast such that missing imports are added.
        return node

    visit_Attribute = visit_Name

    def visit_Subscript(self, node: ast.Subscript) -> ast.expr:
        node.value = self.visit(node.value)
        node.slice = self.visit(node.slice)
        fullName = self.node2fullname(node.value)
        
        if fullName == 'typing.Union':
            # typing.Union can be used with a single type or a 
            # tuple of types, includea single element tuple, which is the same
            # as the directly using the type: Union[x] == Union[(x,)] == x
            slice_ = node.slice
            if isinstance(slice_, ast.Tuple):
                args = slice_.elts
                if len(args) > 1:
                    return self._union_args_to_bitor(args, node)
                elif len(args) == 1:
                    return args[0]
            elif isinstance(slice_, (ast.Attribute, ast.Name, ast.Subscript, ast.BinOp)):
                return slice_
        
        elif fullName == 'typing.Optional':
            # typing.Optional requires a single type, so we don't process when slice is a tuple.
            slice_ = node.slice
            if isinstance(slice_, (ast.Attribute, ast.Name, ast.Subscript, ast.BinOp)):
                return self._union_args_to_bitor([slice_, ast.Constant(value=None)], node)

        return node
    
DEPRECATED_TYPING_ALIAS_BUILTINS = {
        "typing.Text": 'str',
        "typing.Dict": 'dict',
        "typing.Tuple": 'tuple',
        "typing.Type": 'type',
        "typing.List": 'list',
        "typing.Set": 'set',
        "typing.FrozenSet": 'frozenset',
}

# These do not belong in the deprecated builtins aliases, so we make sure it doesn't happen.
assert 'typing.Union' not in DEPRECATED_TYPING_ALIAS_BUILTINS
assert 'typing.Optional' not in DEPRECATED_TYPING_ALIAS_BUILTINS

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
        "typing.Deque",
        "typing.MappingView",
        "typing.KeysView",
        "typing.ItemsView",
        "typing.ValuesView",
        "typing.ContextManager",
        "typing.AsyncContextManager",
        "typing.DefaultDict",
        "typing.OrderedDict",
        "typing.Counter",
        "typing.ChainMap",
        "typing.Generator",
        "typing.AsyncGenerator",
        "typing.Pattern",
        "typing.Match",
        # Special forms
        "typing.Union",
        "typing.Literal",
        "typing.Optional",
        *DEPRECATED_TYPING_ALIAS_BUILTINS, 
    )

SUBSCRIPTABLE_CLASSES_PEP585 = (
        "tuple",
        "list",
        "dict",
        "set",
        "frozenset",
        "type",
        "builtins.tuple",
        "builtins.list",
        "builtins.dict",
        "builtins.set",
        "builtins.frozenset",
        "builtins.type",
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

def get_docstring_node(node: ast.AST) -> Str | None:
    """
    Return the docstring node for the given class, function or module
    or None if no docstring can be found.
    """
    if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module)) or not node.body:
        return None
    node = node.body[0]
    if isinstance(node, ast.Expr):
        if isinstance(node.value, Str):
            return node.value
    return None

class _StrMeta(type):
    def __instancecheck__(self, instance: object) -> bool:
        if isinstance(instance, ast.expr):
            return get_str_value(instance) is not None
        return False

class Str(ast.expr, metaclass=_StrMeta):
    """
    Wraps ast.Constant/ast.Str for `isinstance` checks and annotations. 
    Ensures that the value is actually a string.
    Do not try to instanciate this class.
    """

    value: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(f'{Str.__qualname__} cannot be instanciated')

def extract_docstring_linenum(node: Str) -> int:
    r"""
    In older CPython versions, the AST only tells us the end line
    number and we must approximate the start line number.
    This approximation is correct if the docstring does not contain
    explicit newlines ('\n') or joined lines ('\' at end of line).

    Leading blank lines are stripped by cleandoc(), so we must
    return the line number of the first non-blank line.
    """
    doc = node.value
    lineno = node.lineno

    # Leading blank lines are stripped by cleandoc(), so we must
    # return the line number of the first non-blank line.
    for ch in doc:
        if ch == '\n':
            lineno += 1
        elif not ch.isspace():
            break
    
    return lineno

def extract_docstring(node: Str) -> Tuple[int, str]:
    """
    Extract docstring information from an ast node that represents the docstring.

    @returns: 
        - The line number of the first non-blank line of the docsring. See L{extract_docstring_linenum}.
        - The docstring to be parsed, cleaned by L{inspect.cleandoc}.
    """
    value = node.value
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
                ann_elem = ast.Tuple(elts=[ann_elem, ann_value], ctx=ast.Load())
        if ann_elem is not None:
            if name == 'tuple':
                ann_elem = ast.Tuple(elts=[ann_elem, ast.Constant(value=...)], ctx=ast.Load())
            return ast.Subscript(value=ast.Name(id=name, ctx=ast.Load()),
                                 slice=ann_elem,
                                 ctx=ast.Load())
    return ast.Name(id=name, ctx=ast.Load())

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
        return ast.Name(id=name, ctx=ast.Load())
    else:
        # Empty sequence or no uniform type.
        return None

      
class Parentage(ast.NodeVisitor):
    """
    Add C{parent} attribute to ast nodes instances.
    """
    def __init__(self) -> None:
        self.current: ast.AST | None = None

    def generic_visit(self, node: ast.AST) -> None:
        current = self.current
        setattr(node, 'parent', current)
        self.current = node
        for child in ast.iter_child_nodes(node):
            self.generic_visit(child)
        self.current = current

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

#Part of the astor library for Python AST manipulation.
#License: 3-clause BSD
#Copyright (c) 2015 Patrick Maupin
_op_data = """
    GeneratorExp                1

          Assign                1
       AnnAssign                1
       AugAssign                0
            Expr                0
           Yield                1
       YieldFrom                0
              If                1
             For                0
        AsyncFor                0
           While                0
          Return                1

           Slice                1
       Subscript                0
           Index                1
        ExtSlice                1
    comprehension_target        1
           Tuple                0
  FormattedValue                0

           Comma                1
       NamedExpr                1
          Assert                0
           Raise                0
    call_one_arg                1

          Lambda                1
           IfExp                0

   comprehension                1
              Or   or           1
             And   and          1
             Not   not          1

              Eq   ==           1
              Gt   >            0
             GtE   >=           0
              In   in           0
              Is   is           0
           NotEq   !=           0
              Lt   <            0
             LtE   <=           0
           NotIn   not in       0
           IsNot   is not       0

           BitOr   |            1
          BitXor   ^            1
          BitAnd   &            1
          LShift   <<           1
          RShift   >>           0
             Add   +            1
             Sub   -            0
            Mult   *            1
             Div   /            0
             Mod   %            0
        FloorDiv   //           0
         MatMult   @            0
          PowRHS                1
          Invert   ~            1
            UAdd   +            0
            USub   -            0
             Pow   **           1
           Await                1
             Num                1
        Constant                1
"""

_op_data = [x.split() for x in _op_data.splitlines()] # type:ignore
_op_data = [[x[0], ' '.join(x[1:-1]), int(x[-1])] for x in _op_data if x] # type:ignore
for _index in range(1, len(_op_data)):
    _op_data[_index][2] *= 2 # type:ignore
    _op_data[_index][2] += _op_data[_index - 1][2] # type:ignore

_deprecated: Collection[str] = ()
if sys.version_info >= (3, 12):
    _deprecated = ('Num', 'Str', 'Bytes', 'Ellipsis', 'NameConstant')
_precedence_data = dict((getattr(ast, x, None), z) for x, y, z in _op_data if x not in _deprecated) # type:ignore
_symbol_data = dict((getattr(ast, x, None), y) for x, y, z in _op_data if x not in _deprecated) # type:ignore

class op_util:
    """
    This class provides data and functions for mapping
    AST nodes to symbols and precedences.
    """
    @classmethod
    def get_op_symbol(cls, obj:ast.operator|ast.boolop|ast.cmpop|ast.unaryop,
                      fmt:str='%s', 
                      symbol_data:dict[type[ast.AST]|None, str]=_symbol_data, 
                      type:Callable[[object], type[Any]]=type) -> str:
        """Given an AST node object, returns a string containing the symbol.
        """
        return fmt % symbol_data[type(obj)]
    @classmethod
    def get_op_precedence(cls, obj:ast.AST, 
                          precedence_data:dict[type[ast.AST]|None, int]=_precedence_data, 
                          type:Callable[[object], type[Any]]=type) -> int:
        """Given an AST node object, returns the precedence.

        @raises KeyError: If the node is not explicitely supported by this function. 
            This is a very legacy piece of code, all calls to L{get_op_precedence} should be
            guarded in a C{try:... except KeyError:...} statement.
        """
        return precedence_data[type(obj)]

    if not TYPE_CHECKING:
        class Precedence(object):
            vars().update((cast(str, x), z) for x, _, z in _op_data)
            highest = max(cast(int, z) for _, _, z in _op_data) + 2
    else:
        Precedence: Any

del _op_data, _index, _precedence_data, _symbol_data, _deprecated
# This was part of the astor library for Python AST manipulation.


class _OldSchoolNamespacePackageVis(ast.NodeVisitor):

    is_namespace_package: bool = False

    def visit_Module(self, node: ast.Module) -> None:
        try:
            self.generic_visit(node)
        except StopIteration:
            pass
    
    def visit_skip(self, node: ast.AST) -> None:
        pass
    
    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_skip
    visit_AugAssign = visit_skip
    visit_Return = visit_Raise = visit_Assert = visit_skip
    visit_Pass = visit_Break = visit_Continue = visit_Delete = visit_skip
    visit_Global = visit_Nonlocal = visit_skip
    visit_Import = visit_ImportFrom = visit_skip

    def visit_Expr(self, node: ast.Expr) -> None:
        # Search for ast.Expr nodes that contains a call to a name or attribute 
        # access of "declare_namespace" and a single argument: __name__
        if not isinstance(val:=node.value, ast.Call):
            return
        if not isinstance(func:=val.func, (ast.Name, ast.Attribute)):
            return
        if isinstance(func, ast.Name) and func.id == 'declare_namespace' or \
           isinstance(func, ast.Attribute) and func.attr == 'declare_namespace':
            # checks the arguments are the basic one, not custom
            try:
                arg1, = (*val.args, *(k.value for k in val.keywords))
            except ValueError:
                raise StopIteration
            if not isinstance(arg1, ast.Name) or arg1.id != '__name__':
                raise StopIteration
            
            self.is_namespace_package = True
            raise StopIteration
        
    def visit_Assign(self, node: ast.Assign) -> None:
        # search for assignments nodes that contains a call in the 
        # rhs to name or attribute acess of "extend_path" and two arguments: 
        # __path__ and __name__. 

        if not any(isinstance(t, ast.Name) and t.id == '__path__' for t in node.targets):
            return
        if not isinstance(val:=node.value, ast.Call):
            return
        if not isinstance(func:=val.func, (ast.Name, ast.Attribute)):
            return
        if isinstance(func, ast.Name) and func.id == 'extend_path' or \
           isinstance(func, ast.Attribute) and func.attr == 'extend_path':
            # checks the arguments are the basic one, not custom
            try:
                arg1, arg2 = (*val.args, *(k.value for k in val.keywords))
            except ValueError:
                raise StopIteration
            if (not isinstance(arg1, ast.Name)) or arg1.id != '__path__':
                raise StopIteration
            if (not isinstance(arg2, ast.Name)) or arg2.id != '__name__':
                raise StopIteration

            self.is_namespace_package = True
            raise StopIteration
    
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        setattr(node, 'targets', [node.target])
        try:
            self.visit_Assign(node) # type:ignore[arg-type]
        finally:
            delattr(node, 'targets')
       
def is_old_school_namespace_package(tree: ast.Module) -> bool:
    """
    Returns True if the module is a pre PEP 420 namespace package::
    
        from pkgutil import extend_path
        __path__ = extend_path(__path__, __name__)
        # OR
        import pkg_resources
        pkg_resources.declare_namespace(__name__)
        # OR
        __import__('pkg_resources').declare_namespace(__name__)
        # OR
        import pkg_resources
        pkg_resources.declare_namespace(name=__name__)

    The following code will return False, tho::

        from pkgutil import extend_path
        __path__ = extend_path(__path__, __name__ + '.impl')
    
    """
    v =_OldSchoolNamespacePackageVis()
    v.visit(tree)
    return v.is_namespace_package
