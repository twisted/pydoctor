"""
Lower level builder that turns ASTs into a tree of L{Statement}s, 
indexed by L{Symbol}s name, with limited support for L{Constaint}s.
"""

import ast
import enum

from typing import (Generic, List, 
    Mapping, MutableMapping, MutableSequence, Optional, Sequence, Tuple,
    Type, TypeVar, Union, cast, TYPE_CHECKING
)

import attr
from pydoctor.astutils import (node2dottedname, iterassignfull, dottedname2node, setfield, getfield)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias
else:
    TypeAlias = object


# ----- Better static analysis for pydoctor with an actual symbol table. ------
# Support for match case, loops and assertions is currently missing from design, this is
# because we are not building an actual control flow graph, rather we're building a nested symbol table
# with limited support for constraints. Currently it has no support for parent back links, but it might be added
# later to do more with this new model.

def fetchScopeSymbols(scope: '_ScopeNodeT') -> 'ScopeNode':
    """
    Build a lower level structure that represents code. 
    This stucture has builtint support for duplicate names and constraint gathering.
    """
    return _ScopeTreeBuilder.build(ScopeNode(scope, ()))


_ConstraintNodeT:TypeAlias = 'Union[ast.If, ast.ExceptHandler, ast.While, ast.For, ast.AsyncFor, ast.Match]'
_ScopeNodeT:TypeAlias = 'Union[ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]'
_LeafNodeT:TypeAlias = 'Union[ast.Assign, ast.AnnAssign, ast.AugAssign, ast.arg, ast.Import, ast.ImportFrom, ast.Delete, ast.Global, ast.Nonlocal]'
_SymbolNodeT:TypeAlias = 'Union[_ScopeNodeT, _LeafNodeT]'
_NodeT = TypeVar('_NodeT', bound=_SymbolNodeT)

class BlockType(enum.Enum):
    """
    A L{Constraint}'s block type. It's L{OTHER} for loops and other constructs.
    """
    IF_BLOCK = enum.auto()
    """
    The if condition is satisfied.
    """
    ELSE_BLOCK = enum.auto()
    """
    The if condition is not satisfied.
    """
    EXCEPT_BLOCK = enum.auto()
    """
    One of the exception that is caught by the handler got raised.
    """
    OTHER = enum.auto()
    """
    Some other constraints applies to this statement, but we don't explicitely have support for them.
    """

def _ast_repr(v:Optional[ast.AST]) -> str:
    if isinstance(v, ast.AST):
        return f'<{v.__class__.__name__} at line {v.lineno}>'
    return repr(v)

@attr.s(frozen=True)
class Symbol:
    """
    A symbol has a name and can be composed by multiple statements.
    """

    name: str = attr.ib()
    statements: Sequence['StmtNode[_SymbolNodeT]'] = attr.ib(factory=list, init=False)

    def filterstmt(self, *types:Type[_NodeT]) -> Sequence['StmtNode[_NodeT]']:
        def f(n:StmtNode[_SymbolNodeT]) -> bool: 
            return isinstance(n.node, types)
        return list(filter(f, self.statements)) # type:ignore

@attr.s(frozen=True)
class StmtNode(Generic[_NodeT]):
    node: _NodeT  = attr.ib(repr=_ast_repr)
    """
    The AST node.
    """
    constraints: Tuple['Constraint',...] = attr.ib()
    """
    Constraints applied to the statement.
    """
    
    value: Optional[ast.expr]

@attr.s(frozen=True)
class LeafNode(StmtNode[_LeafNodeT]):
    value: Optional[ast.expr] = attr.ib()
    """
    The expression value that is assigned for this node. It can be None if 
    the statement doesn't assign the name any particular value like in the 
    case of the C{del} statement. It can also be None if we don't have enough
    understanding of the code.

    @note: import names are encoded as L{ast.Attribute} and L{ast.Name} instances.
    """

@attr.s(frozen=True)
class ScopeNode(StmtNode[_ScopeNodeT]):
    """
    A scope node represents a module, class or function.
    """

    symbols: Mapping[str, 'Symbol'] = attr.ib(factory=dict, init=False)
    """
    This scope's symbol table.
    """
    
    value = None
    """
    The value for scope node is always None.
    """

    def __getitem__(self, name:str) -> Sequence[StmtNode[_SymbolNodeT]]:
        """
        Get all statements that declares the given name.
        """
        return self.symbols[name].statements

@attr.s(frozen=True)
class Constraint:
    block: BlockType = attr.ib()
    """
    The block type associated to the node's state.
    """
    node: _ConstraintNodeT = attr.ib(repr=_ast_repr)
    """
    The AST node that generated this constraint.
    """

class _ScopeTreeBuilder(ast.NodeVisitor):

    def __init__(self, scope:ScopeNode) -> None:
        super().__init__()
        self.scope = scope
        self._constraints: List[Constraint] = []
    
    @classmethod
    def build(cls, scope:ScopeNode) -> ScopeNode:
        """
        Walk this node's AST and fill the symbol table with contents.
        """
        # create a link from ast object to this scope 
        setfield(scope.node, 'scope', scope)
        # recursively build the scope
        builder = cls(scope)
        for stmt in ast.iter_child_nodes(scope.node):
            builder.visit(stmt)
        return scope

    # constraint stack functions

    def _push_constaint(self, block:BlockType, node:_ConstraintNodeT) -> None:
        self._constraints.append(Constraint(block, node))

    def _pop_constaint(self, block:BlockType, node:_ConstraintNodeT) -> Constraint:
        c = self._constraints.pop()
        assert c.block is block and c.node is node
        return c
    
    @property
    def constraints(self) -> Tuple[Constraint,...]:
        return tuple(self._constraints)

    # building symbols
    
    def _get_symbol(self, name:str) -> Symbol:
        """
        Get the existing symbol or register a new symbol.
        """
        symbols = cast(MutableMapping[str, Symbol], self.scope.symbols)
        if name not in symbols:
            symbol = Symbol(name)
            symbols[name] = symbol
        else:
            symbol = symbols[name]
        return symbol
    
    def _add_statement(self, name:str, stmt: Union[LeafNode, ScopeNode]) -> None:
        """
        Register a statement to the symbol table.
        """
        symbol = self._get_symbol(name)
        statements = cast(MutableSequence[Union[LeafNode, ScopeNode]], symbol.statements)
        statements.append(stmt)

    # scope symbols: we do recurse on nested scopes

    def visit_Scope(self, node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        statement = ScopeNode(node, self.constraints)
        self._add_statement(node.name, statement)
        # use a new builder, don't propagate constraints to new scope.
        _ScopeTreeBuilder.build(statement)
    
    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_Scope
    
    # symbol gathering

    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign, ast.AugAssign]) -> None:
        value = node.value
        statement = LeafNode(node, self.constraints, value)
        for dottedname, target in iterassignfull(node): 
            if dottedname:
                # easy case
                self._add_statement('.'.join(dottedname), statement)
            
            elif isinstance(node, ast.Assign) and isinstance(target, ast.Tuple):
                values:Union[List[None], List[ast.expr]] = [None] * len(target.elts)
                
                if isinstance(value, ast.Tuple) and len(target.elts)==len(value.elts) \
                   and not any(isinstance(n, ast.Starred) for n in target.elts):
                    # tuples of the same lengh without unpacking, we can handle it, otherwise
                    # it uses None values
                    values = value.elts

                for i, elem in enumerate(target.elts):
                    dottedname = node2dottedname(elem)
                    if dottedname:
                        statement = LeafNode(node, self.constraints, values[i])
                        self._add_statement('.'.join(dottedname), statement)
    
    visit_AnnAssign = visit_AugAssign = visit_Assign

    def visit_arg(self, node:ast.arg) -> None:
        statement = LeafNode(node, self.constraints, None)
        self._add_statement(node.arg, statement)

    # some support for imports 

    def visit_Import(self, node: ast.Import) -> None:
        for al in node.names:
            fullname, asname = al.name, al.asname
            # we encode imports targets into ast Attribute and Name instances.
            statement = LeafNode(node, self.constraints, dottedname2node(fullname))
            self._add_statement(asname or fullname, statement)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # we don't record the value of relative imports here
        modname = node.module if not node.level else None
        for al in node.names:
            orgname, asname = al.name, al.asname
            value = dottedname2node(f'{modname}.{orgname}') if modname else None
            statement = LeafNode(node, self.constraints, value)
            self._add_statement(asname or orgname, statement)
    
    # support for global/nonlocal and del statements 

    def visit_Delete(self, node:Union[ast.Delete, ast.Global, ast.Nonlocal]) -> None:
        names = node.names if not isinstance(node, ast.Delete) else \
            ['.'.join(node2dottedname(n) or ['']) for n in node.targets]
        statement = LeafNode(node, self.constraints, None)
        for name in names:
            if name:
                self._add_statement(name, statement)

    visit_Global = visit_Nonlocal = visit_Delete

    # constraints gathering

    def visit_If(self, node: ast.If) -> None:

        self._push_constaint(BlockType.IF_BLOCK, node)
        for b in node.body: self.visit(b)
        self._pop_constaint(BlockType.IF_BLOCK, node)

        self._push_constaint(BlockType.ELSE_BLOCK, node)
        for b in node.orelse: self.visit(b)
        self._pop_constaint(BlockType.ELSE_BLOCK, node)
    
    def visit_Try(self, node: Union[ast.Try, 'ast.TryStar']) -> None:

        for b in node.body: self.visit(b)

        for h in node.handlers: 
            self._push_constaint(BlockType.EXCEPT_BLOCK, h)
            self.visit(h)
            self._pop_constaint(BlockType.EXCEPT_BLOCK, h)
        
        for b in node.orelse: self.visit(b)
        for b in node.finalbody: self.visit(b)

    visit_TryStar = visit_Try
    
    def visit_Other(self, node:'Union[ast.For, ast.While, ast.AsyncFor, ast.Match]') -> None: # tpe:ignore[name-defined]
        self._push_constaint(BlockType.OTHER, node)
        self.generic_visit(node)
        self._pop_constaint(BlockType.OTHER, node)
    
    visit_For = visit_While = visit_AsyncFor = visit_Match = visit_Other
