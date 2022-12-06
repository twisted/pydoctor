"""
Lower level representation of ASTs in a tree of L{Statement}s, 
indexed by L{Symbol}s name, with limited support for L{Constraint}s.
"""

import ast
import enum

from typing import (Generic, Iterable, Iterator, List, 
    Mapping, MutableMapping, MutableSequence, Optional, Sequence, Tuple,
    Type, TypeVar, Union, cast, TYPE_CHECKING
)

import attr
from pydoctor.astutils import (node2dottedname, iterassignfull, setfield)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias, TypeGuard
else:
    TypeAlias = TypeGuard = object


# ----- Better static analysis for pydoctor with an actual symbol table. ------
# Support for match case, loops and assertions is currently missing from design, this is
# because we are not building an actual control flow graph, rather we're building a nested symbol table
# with limited support for constraints. Currently it has no support for parent back links, but it might be added
# later to do more with this new model.

def buildSymbols(scope: '_ScopeT', parent:Optional['Scope']=None) -> 'Scope':
    """
    Build a lower level structure that represents code. 
    This stucture has builtint support for duplicate names and constraint gathering.
    """
    return _SymbolTreeBuilder.build(Scope(scope, parent, ()))


_ConstraintNodeT:TypeAlias = 'Union[ast.If, ast.ExceptHandler, ast.While, ast.For, ast.AsyncFor, ast.Match]'
_ScopeT:TypeAlias = 'Union[ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]'
_ImportNodeT:TypeAlias = 'Union[ast.Import, ast.ImportFrom]'
_AssignNodeT:TypeAlias = 'Union[ast.Assign, ast.AnnAssign]'
_AugAssignNodeT:TypeAlias = ast.AugAssign
_ArgumentsNodeT = ast.arguments
_DeleteNodeT = ast.Delete
_OutterScopeVarRefNodeT: TypeAlias = 'Union[ast.Global, ast.Nonlocal]'
_LeafNodeT:TypeAlias = 'Union[_ImportNodeT, _AssignNodeT, _AugAssignNodeT, _ArgumentsNodeT, _DeleteNodeT, _OutterScopeVarRefNodeT]'
_StmtNodeT:TypeAlias = 'Union[_ScopeT, _LeafNodeT]'
_NodeT = TypeVar('_NodeT', bound=_StmtNodeT)

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
class Statement:
    """
    Base class for all statements in the symbol tree.
    """
    node: _StmtNodeT  = attr.ib(repr=_ast_repr)
    """
    The AST node.
    """
    parent:Optional['Scope'] = attr.ib()
    """
    The scope that contains this statement.
    """
    constraints: Tuple['Constraint',...] = attr.ib()
    """
    Constraints applied to the statement.
    """

_StatementT = TypeVar('_StatementT', bound='StatementNodesT')

@attr.s(frozen=True)
class Symbol:
    """
    The Symbol class is a container for one or multiple statements that affects a given name,
    meaning all statements that should be interpreted to semantically analyze a symbol within the scope.

    A symbol is composed by a name and potentially multiple statements.
    """

    name: str = attr.ib()
    statements: Sequence['StatementNodesT'] = attr.ib(factory=list, init=False)
    # scope: 'Scope' = attr.ib() # is a link to the symbol's scope needed? 

@attr.s(frozen=True)
class Import(Statement):
    """
    Wraps L{ast.Import} and L{ast.ImportFrom} nodes.
    """
    node:_ImportNodeT
    parent:'Scope'
    
    target: Optional[str] = attr.ib()
    """
    The fullname of the imported object.
    """

@attr.s(frozen=True)
class Assignment(Statement):
    """
    Wraps L{ast.Assign}, L{ast.AnnAssign} nodes.
    """
    node:_AssignNodeT
    parent:'Scope'
    
    value: Optional[ast.expr] = attr.ib()
    """
    The expression value that is assigned for this node. It can also be None if we don't have enough
    understanding of the code.
    """

@attr.s(frozen=True)
class AugAssignment(Statement):
    """
    Wraps L{ast.AugAssign} nodes.
    """
    node:_AugAssignNodeT
    parent:'Scope'
    
    value: Optional[ast.expr] = attr.ib()
    
@attr.s(frozen=True)
class Deletion(Statement):
    """
    Wraps an L{ast.Delete} statement.
    """
    node:_DeleteNodeT
    parent:'Scope'

@attr.s(frozen=True)
class OuterScopeVarRef(Statement):
    """
    Wraps a L{ast.Global} or L{ast.Nonlocal} statement.
    """
    node:_OutterScopeVarRefNodeT
    parent:'Scope'

@attr.s(frozen=True)
class Arguments(Statement):
    """
    Wraps an L{ast.arguments} statement.
    """
    node:_ArgumentsNodeT
    parent:'Scope'

@attr.s(frozen=True)
class Scope(Statement):
    """
    Wraps an L{ast.Module}, {ast.ClassDef}, L{ast.FunctionDef} or L{ast.AsyncFunctionDef} statement.
    """

    symbols: Mapping[str, 'Symbol'] = attr.ib(factory=dict, init=False)
    """
    This scope's symbol table.
    """

    node:_ScopeT

    def __getitem__(self, name:str) -> Sequence['StatementNodesT']:
        """
        Get all statements that affects the given name within the scope.
        """
        return self.symbols[name].statements
    
    # def fullName(self) -> str:
    #     parent = self.parent
    #     if parent is None:
    #         return self.node.name
    #     else:
    #         return f'{parent.fullName()}.{self.node.name}'

    # def body(self) -> Sequence['StatementNodesT']:
    #     """
    #     Get all statements within the scope, sorted by linenumber.
    #     """
    #     def all_statements() -> Iterator['StatementNodesT']:
    #         for name in self.symbols:
    #             yield from self[name]
    #     return sort_stmts_by_lineno(all_statements())


StatementNodesT = Union[Import, Assignment, AugAssignment, 
                    Deletion, OuterScopeVarRef, Arguments, Scope]

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

def filter_stmts_by_type(stmts:Iterable['StatementNodesT'], typ:Type[_StatementT])-> Sequence['_StatementT']:
    """
    Filter statements based on the type.
    """
    def f(n:'StatementNodesT') -> 'TypeGuard[_StatementT]':
        return isinstance(n, typ)
    return list(filter(f, stmts))

def sort_stmts_by_lineno(stmts:Iterable['StatementNodesT']) -> Sequence['StatementNodesT']:
    """
    Sort by line number.
    """
    return sorted(stmts, key=lambda stmt:stmt.node.lineno)

def lookup_symbol(ctx:'StatementNodesT', name:str) -> 'Symbol':
    if isinstance(ctx, Arguments):
        ctx = ctx.parent.parent
    ...


##### builder #####


class _SymbolTreeBuilder(ast.NodeVisitor):

    def __init__(self, scope:Scope) -> None:
        super().__init__()
        self.scope = scope
        self._constraints: List[Constraint] = []
    
    @classmethod
    def build(cls, scope:Scope) -> Scope:
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
    def constraints(self) -> Tuple[Constraint, ...]:
        """
        Current constraints applied in the state of the buidler.
        """
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
    
    def _add_statement(self, name:str, stmt: StatementNodesT) -> None:
        """
        Register a statement to the symbol table.
        """
        symbol = self._get_symbol(name)
        statements = cast(MutableSequence[StatementNodesT], symbol.statements)
        statements.append(stmt)

    # scope symbols: recurse on nested scopes

    def visit_Scope(self, node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        statement = Scope(node, self.scope, self.constraints)

        self._add_statement(node.name, statement)
        # use a new builder, don't propagate constraints to new scope.
        _SymbolTreeBuilder.build(statement)
    
    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_Scope
    
    # symbol gathering

    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign]) -> None:
        value = node.value
        statement = Assignment(node, self.scope, self.constraints, value)
        for dottedname, target in iterassignfull(node): 
            if dottedname:
                # easy case: self.a = a
                self._add_statement('.'.join(dottedname), statement)
            
            elif isinstance(node, ast.Assign) and isinstance(target, ast.Tuple):
                values:Union[List[None], List[ast.expr]] = [None] * len(target.elts)
                # self.a,self.b = range(2)
                if isinstance(value, ast.Tuple) and len(target.elts)==len(value.elts) \
                   and not any(isinstance(n, ast.Starred) for n in target.elts + value.elts):
                    # tuples of the same lengh without unpacking, we can handle it, otherwise
                    # it uses None values
                    # self.a,self.b = a,b
                    values = value.elts

                for i, elem in enumerate(target.elts):
                    dottedname = node2dottedname(elem)
                    if dottedname:
                        statement = Assignment(node, self.scope, self.constraints, values[i])
                        self._add_statement('.'.join(dottedname), statement)
    
    visit_AnnAssign = visit_Assign

    def visit_AugAssign(self, node:ast.AugAssign) -> None:
        value = node.value
        dottedname = node2dottedname(node.target)
        if dottedname:
            statement = AugAssignment(node, self.scope, self.constraints, value)
            self._add_statement('.'.join(dottedname), statement)

    def visit_arguments(self, node: ast.arguments) -> None:
        statement = Arguments(node, self.scope, self.constraints)
        for a in getattr(node, 'posonlyargs', []) + node.args + [node.vararg, node.kwarg]:
            if a: self._add_statement(a.arg, statement)

    # some support for imports 

    def visit_Import(self, node: ast.Import) -> None:
        for al in node.names:
            fullname, asname = al.name, al.asname
            # we encode imports targets into ast Attribute and Name instances.
            statement = Import(node, self.scope, self.constraints, fullname)
            self._add_statement(asname or fullname, statement)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # we don't record the value of relative imports here, but we could.
        modname = node.module if not node.level else None
        for al in node.names:
            orgname, asname = al.name, al.asname
            fullname = f'{modname}.{orgname}' if modname else None
            statement = Import(node, self.scope, self.constraints, fullname)
            self._add_statement(asname or orgname, statement)
    
    # support for global/nonlocal and del statements 

    def visit_Delete(self, node:ast.Delete) -> None:
        statement = Deletion(node, self.scope, self.constraints)
        for n in node.targets:
            dottedname = node2dottedname(n)
            if dottedname:
                self._add_statement('.'.join(dottedname), statement)

    def visit_Global(self, node:Union[ast.Global, ast.Nonlocal]) -> None:
        statement = OuterScopeVarRef(node, self.scope, self.constraints)
        for name in node.names:
            self._add_statement(name, statement)

    visit_Nonlocal = visit_Global

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
