"""
Lower level representation of ASTs in a tree of L{Statement}s, 
indexed by L{Symbol}s name, with limited support for L{Constraint}s.
"""

import ast

from typing import (List, 
    Mapping, MutableMapping, MutableSequence, Optional, Sequence, Tuple,
    Type, TypeVar, Union, cast, TYPE_CHECKING
)

import attr
from pydoctor.astutils import (node2dottedname, iterassignfull, setfield)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias, Protocol
else:
    TypeAlias = Protocol = object


# ----- Better static analysis for pydoctor with an actual symbol table. ------
# Support for match case, loops and assertions is currently missing from design, this is
# because we are not building an actual control flow graph, rather we're building a nested symbol table
# with limited support for constraints.

# This model cannot be used alone to construct a Documentable tree, the AST still needs to be visited.
# More particularly, here the list of differences in between the astbuilder and the symbols builder:
# - The astbuilder understands relative imports.
# - The astbuilder understand wildcard imports.
# - The symbols objects have no support for expanding a dottedname (name with one or more dots) to it's fqn.
# - Unlike the astbuilder, the symbols builder has not special code to understand aliases.
# - The symbols builder handled duplicates names in a safe and correct way.
# - The symbols builder understands tuple assignments better.

# There is some overlap nonetheless, both models offer a way to expand a local name (with no dots) to it's 
# full name. The full name resolver provided in this module is used as fallback resolver when our model has been
# so altered from the reality of the python code (with reparenting for instance) that it can't find the name anymore.
# Since the resolvver is only used as a fallback, it does not implement the full complexity of name resolving,
# but can still covers the 90% of the cases.

def buildSymbols(scope: ast.Module, name:str, parent:Optional['Scope']=None) -> 'Scope':
    """
    Build a lower level structure that represents code. 
    This stucture has builtint support for duplicate names and constraint gathering.
    """
    return _SymbolTreeBuilder.build(Module(scope, parent, (), name=name))


_ScopeT:TypeAlias = 'Union[ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]'
_ImportNodeT:TypeAlias = 'Union[ast.Import, ast.ImportFrom]'
_AssignNodeT:TypeAlias = 'Union[ast.Assign, ast.AnnAssign]'
_AugAssignNodeT:TypeAlias = ast.AugAssign
_ArgumentsNodeT = ast.arguments
_DeleteNodeT = ast.Delete
_OutterScopeVarRefNodeT: TypeAlias = 'Union[ast.Global, ast.Nonlocal]'
_LeafNodeT:TypeAlias = 'Union[_ImportNodeT, _AssignNodeT, _AugAssignNodeT, _ArgumentsNodeT, _DeleteNodeT, _OutterScopeVarRefNodeT]'
_StmtNodeT:TypeAlias = 'Union[_ScopeT, _LeafNodeT]'

@attr.s(frozen=True)
class Statement:
    """
    Base class for all statements in the symbol tree.
    The symbol tree is not an 1-1 representation for AST, some nodes does not exist in this model,
    and some nodes are represented with multiple statements. 

    - Nodes having a 1-1 corespondance: L{ast.ClassDef}, L{ast.FunctionDef}, L{ast.AsyncFunctionDef}, L{ast.Module}.

    - Nodes that may be spiltted in several statements: 
      L{ast.Assign}, L{ast.Import}, L{ast.ImportFrom}, L{ast.Global}, L{ast.Nonlocal}, L{ast.Delete}.

    - Represented by C{Constraint}s: L{ast.If}, L{ast.Try}, L{ast.TryStar}.
    
    - Unsupported nodes for Constraints: L{ast.For}, L{ast.While}, L{ast.AsyncFor}, L{ast.Match}.
    
    - Not present in the statement tree: 
      L{ast.Expr}, L{ast.With}, L{ast.Pass}, L{ast.Break}, L{ast.Continue}, L{ast.Assert}.

    """
    node: _StmtNodeT  = attr.ib()
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

class HasNameAndParent(Protocol):
    """
    Abstract class for something with a L{fullName}.
    """

    @property
    def name(self)-> str:...
    @property
    def parent(self) -> Optional['HasNameAndParent']:...
    def fullName(self) -> str:
        """
        Get the full name of this object.
        """
        parent = self.parent
        if parent is None:
            return self.name
        else:
            return f'{parent.fullName()}.{self.name}'

@attr.s(frozen=True)
class Symbol(HasNameAndParent):
    """
    The Symbol class is a container for one or multiple statements that affects a given name,
    meaning all statements that should be interpreted to semantically analyze a symbol within the scope.

    A symbol is composed by a name and potentially multiple statements.
    """

    name: str = attr.ib()
    parent: 'Scope' = attr.ib()
    statements: Sequence['StatementNodesT'] = attr.ib(factory=list, init=False)

@attr.s(frozen=True)
class Import(Statement):
    """
    Wraps L{ast.Import} and L{ast.ImportFrom} nodes.
    
    @note: One L{Import} instance is created for each 
        name present in the C{import} statement.
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

    @note: One L{Assignment} instance is created for each 
        name present in the assignment targets. 
        Limited support for tuple assignments is included.
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

    @note: One L{Deletion} instance is created for each 
        name present in the C{del} targets.
    """
    node:_DeleteNodeT
    parent:'Scope'

@attr.s(frozen=True)
class OuterScopeRef(Statement):
    """
    Wraps a L{ast.Global} or L{ast.Nonlocal} statement.

    @note: One L{OuterScopeRef} instance is created for each 
        name present in the C{global} or C{nonlocal} statement.
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
class Scope(Statement, HasNameAndParent):
    """
    Wraps an L{ast.Module}, {ast.ClassDef}, L{ast.FunctionDef} or L{ast.AsyncFunctionDef} statement.
    """
    
    name:str = attr.ib()
    """
    The name of this scope.
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
    
    # def body(self) -> Sequence['StatementNodesT']:
    #     """
    #     Get all statements within the scope, sorted by linenumber.
    #     """
    #     def all_statements() -> Iterator['StatementNodesT']:
    #         for name in self.symbols:
    #             yield from self[name]
    #     return sort_stmts_by_lineno(all_statements())

@attr.s(frozen=True)
class Class(Scope):
    ...

@attr.s(frozen=True)
class Function(Scope):
    ...

@attr.s(frozen=True)
class Module(Scope):
    ...


StatementNodesT = Union[Import, Assignment, AugAssignment, 
                    Deletion, OuterScopeRef, Arguments, Scope]

@attr.s(frozen=True)
class Constraint:
    """
    Encapsulate a constraint information for statements.
    Only constraints accumulated from if/else and except branches are supported.
    """

@attr.s(frozen=True)
class IfConstraint(Constraint):
    """
    The test condition is satisfied.
    """
    test: ast.expr = attr.ib()

@attr.s(frozen=True)
class ElseConstraint(Constraint):
    """
    The test condition is not satisfied.
    """
    test: ast.expr = attr.ib()

@attr.s(frozen=True)
class ExceptHandlerConstraint(Constraint):
    """
    One of the exception types that is caught by the handler got raised.
    """
    types: Optional[Sequence[Optional[str]]] = attr.ib()

@attr.s(frozen=True)
class UnsupportedConstraint(Constraint):
    """
    Some other constraints applies to this statement, but we don't explicitely have support for them.
    """

def _first_non_class_parent(scope:Scope) -> Union[Module, Function]:
    assert not isinstance(scope, Module)
    parent_scope = scope.parent
    if isinstance(parent_scope, (Module, Function)):
        return parent_scope
    else:
        # only modules might have a None parent.
        assert parent_scope is not None
        return _first_non_class_parent(parent_scope)

def _lookup(ctx:Scope, statement:'StatementNodesT', name:str) -> Symbol:
    if '.' in name:
        raise LookupError("dotted names not supported")

    scope = ctx
    if name in scope.symbols:
        return scope.symbols[name]
       
    # The lookup happens in the curent module only.
    if isinstance(scope, Module):
        raise LookupError(f"can't find name {name!r}")

    # here, the scope can't be a module
    # nested scopes: since class names do not extend to nested
    # scopes (e.g., methods), we find the next enclosing non-class scope
    upper_level_scope = _first_non_class_parent(scope)
    return _lookup(upper_level_scope, statement, name)

def localNameToFullName(ctx:Scope, statement:'StatementNodesT', name:str) -> str:
    """
    Caller should always catch L{LookupError} exceptions.
    """
    symbol = _lookup(ctx, statement, name)
    full_name = symbol.fullName()

    # take the last unconstrained statement, otherwise the first statement.
    # TODO: should we filter statements based on statement's location?
    try:
        stmt = next(stmt for stmt in reversed(symbol.statements) if not stmt.constraints)
    except StopIteration:
        stmt = symbol.statements[0]
    
    if isinstance(stmt, Import):
        if stmt.target is None:
            # relative imports are not handled in this model
            raise LookupError("does not support relative imports")

        full_name = stmt.target
    return full_name

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

    def _push_constaint(self, c:Constraint) -> None:
        self._constraints.append(c)

    def _pop_constaint(self, t:Type[Constraint]) -> Constraint:
        c = self._constraints.pop()
        assert isinstance(c, t)
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
            symbol = Symbol(name, parent=self.scope)
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

    _scopeTypes = {
        ast.ClassDef:Class,
        ast.FunctionDef:Function,
        ast.AsyncFunctionDef:Function,
    }
    def visit_Scope(self, node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        
        statement = self._scopeTypes[type(node)](node, self.scope, self.constraints, name=node.name)

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
        statement = OuterScopeRef(node, self.scope, self.constraints)
        for name in node.names:
            self._add_statement(name, statement)

    visit_Nonlocal = visit_Global

    # constraints gathering

    def visit_If(self, node: ast.If) -> None:

        self._push_constaint(IfConstraint(node.test))
        for b in node.body: self.visit(b)
        self._pop_constaint(IfConstraint)

        self._push_constaint(ElseConstraint(node.test))
        for b in node.orelse: self.visit(b)
        self._pop_constaint(ElseConstraint)
    
    def visit_Try(self, node: Union[ast.Try, 'ast.TryStar']) -> None:

        def handlerTypes(h:ast.ExceptHandler) -> Optional[Sequence[Optional[str]]]:
            
            dottedname = lambda n: '.'.join(node2dottedname(n) or ('',)) or None
            
            if isinstance(h.type, ast.Tuple):
                return [dottedname(n) for n in h.type.elts]
            elif h.type is None:
                return None
            else:
                return [dottedname(h.type)]

        for b in node.body: self.visit(b)

        for h in node.handlers: 
            self._push_constaint(ExceptHandlerConstraint(handlerTypes(h)))
            self.visit(h)
            self._pop_constaint(ExceptHandlerConstraint)
        
        for b in node.orelse: self.visit(b)
        for b in node.finalbody: self.visit(b)

    visit_TryStar = visit_Try
    
    def visit_Other(self, node:'Union[ast.For, ast.While, ast.AsyncFor, ast.Match]') -> None: # tpe:ignore[name-defined]
        self._push_constaint(UnsupportedConstraint())
        self.generic_visit(node)
        self._pop_constaint(UnsupportedConstraint)
    
    visit_For = visit_While = visit_AsyncFor = visit_Match = visit_Other
