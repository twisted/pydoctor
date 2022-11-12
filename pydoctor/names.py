"""
Module containing the logic to resolve names, aliases and imports.
"""
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Protocol
else:
    Protocol = object

from pydoctor import model

class _IndirectionT(Protocol):
    # This protocol is implemented by model.Attribute and model.ImportAlias
    system: model.System
    name: str
    parent: model.CanContainImportsDocumentable
    linenumber : int
    alias: Optional[str]
    def fullName(self) -> str:...

def _localDocumentableToFullName(ctx: model.CanContainImportsDocumentable, o: 'model.Documentable', indirections:Optional[List['_IndirectionT']]) -> str:
    """
    If the documentable is an alias, then follow it and return the supposed full name fo the documentable object,
    or return the passed object's - C{o} - full name.

    Calls L{_resolveAlias} if the documentable is an alias.
    """
    if o.kind is model.DocumentableKind.ALIAS:
        assert isinstance(o, model.Attribute)
        return _resolveAlias(ctx, o, indirections)
    return o.fullName()

def _localNameToFullName(ctx: model.Documentable, name: str, indirections:Optional[List['_IndirectionT']]) -> str:
    if isinstance(ctx, model.CanContainImportsDocumentable):
        # Local names and aliases
        if name in ctx.contents:
            return _localDocumentableToFullName(ctx, ctx.contents[name], indirections)
        
        # Imports
        if name in ctx._localNameToFullName_map:
            return _resolveImport(ctx, ctx._localNameToFullName_map[name], indirections)
        
        # Not found
        if isinstance(ctx, model.Class):
            # for classes, we try the upper scope.
            return _localNameToFullName(ctx.parent, name, indirections)
        else:
            return name
    else:
        assert ctx.parent is not None
        return _localNameToFullName(ctx.parent, name, indirections)

_ensure_indirection_list = lambda indirections: indirections if isinstance(indirections, list) else []

def _resolveImport(ctx: model.CanContainImportsDocumentable, import_:_IndirectionT, indirections:Optional[List['_IndirectionT']]) -> str:
    indirections = _ensure_indirection_list(indirections) + [import_]

    failed = fail_to_many_aliases(ctx, import_, indirections)
    if failed:
        return failed
    
    fullName = import_.alias
    assert fullName is not None, f"Bad import: {ctx.module.description}:{import_.linenumber}"

    allobjects = ctx.system.allobjects

    # the imported name is part of the system
    if fullName in allobjects:
        # the imported name might be an alias, so use _localDocumentableToFullName
        resolved = _localDocumentableToFullName(ctx, allobjects[fullName], indirections)
        if resolved:
            return resolved

    dottedName = fullName.split('.')
    parentName, targetName = '.'.join(dottedName[0:-1]), dottedName[-1]

    # the imported name is not part of the system, but it's parent is,
    # so try to resolve the name from the parent's context.
    # this logic has a blind spot: i the parent of the imported name is not found but
    # the grand-parent exists in the system, it will not be used to resolve the imports "chain".
    # We clould use a while loop to walk grand parents until there are no more.
    if parentName in allobjects:
        parent = allobjects[parentName]
        return _localNameToFullName(parent, targetName, indirections)
    else:
        return fullName

def fail_to_many_aliases(self: model.CanContainImportsDocumentable, alias: _IndirectionT, indirections:Optional[List[_IndirectionT]]=None) -> Optional[str]:
    """
    Returns None if the alias can be resolved normally, 
    returns a string and log a warning if the alias 
    can't be resolved because it's too complex.
    """
    if indirections and len(indirections) > self._RESOLVE_ALIAS_MAX_RECURSE:
        self.module.report("Too many aliases", lineno_offset=alias.linenumber, section='aliases')
        return indirections[0].fullName()
    return None

# TODO: This function should be applicable for imports sa well.
# or maybe part of this function should also be applicable. Some special
# care needs to be taken while resolving an ALIAS vs an IMPORT because an alias
# can have the same name and target and redirect to the upper scope name, 
# so this needs to be handled specially. 
def _resolveAlias(self: model.CanContainImportsDocumentable, alias: _IndirectionT, indirections:Optional[List[_IndirectionT]]=None) -> str:
    """
    Resolve the indirection value to it's target full name.
    Or fall back to original name if we've exhausted the max recursions (or something else went wrong).
    
    @param alias: an indirection (alias or import)
    @param indirections: Chain of indirection objects followed. 
        This variable is used to prevent infinite loops when doing the lookup.
    @returns: The potential full name of the 
    """
    indirections = _ensure_indirection_list(indirections)

    failed = fail_to_many_aliases(self, alias, indirections)
    if failed:
        return failed

    # the alias attribute should never be None for indirections objects
    name = alias.alias
    assert name, f"Bad alias: {self.module.description}:{alias.linenumber}"
    
    # the context is important
    ctx = self

    if alias not in indirections:
        # We redirect to the original object
        return ctx.expandName(name, indirections=indirections + [alias])
    
    # We try the upper scope only if we detect a direct cycle.
    # Otherwise just fail.
    if alias is not indirections[-1]:
        self.module.report("Can't resolve cyclic aliases", lineno_offset=alias.linenumber, section='aliases')
        return indirections[0].fullName()

    # Issue tracing the alias back to it's original location, found the same alias again.
    parent = ctx.parent
    if parent is not None and not isinstance(self, model.Module):
        # We try with the parent scope.
        # This is used in situations like right here in the System class and it's aliases (before version > 22.5.1), 
        # because they have the same name as the name they are aliasing, the alias resolves to the same object.
        # We could use astuce here to be more precise (better static analysis) and make this code more simple and less error-prone.
        return parent.expandName(name, indirections=indirections + [alias])

    self.module.report("Failed to resolve alias (found same alias again)", lineno_offset=alias.linenumber, section='aliases')
    return indirections[0].fullName()

def expandName(self:model.Documentable, name: str, indirections:Optional[List[_IndirectionT]]=None) -> str:
    """
    Return a fully qualified name for the possibly-dotted `name`.

    To explain what this means, consider the following modules:

    mod1.py::

        from external_location import External
        class Local:
            pass

    mod2.py::

        from mod1 import External as RenamedExternal
        import mod1 as renamed_mod
        class E:
            pass

    In the context of mod2.E, C{expandName("RenamedExternal")} should be
    C{"external_location.External"} and C{expandName("renamed_mod.Local")}
    should be C{"mod1.Local"}. 
    
    This method is in charge to follow the aliases when possible!
    It will reccursively follow any L{DocumentableKind.ALIAS} entry found 
    up to certain level of complexity. 

    Example:

    mod1.py::

        import external
        class Processor:
            spec = external.Processor.more_spec
        P = Processor

    mod2.py::

        from mod1 import P
        class Runner:
            processor = P

    In the context of mod2, C{expandName("Runner.processor.spec")} should be
    C{"external.Processor.more_spec"}.
    
    @param name: The name to expand.
    @param indirections: See L{_resolveAlias}
    @note: The implementation replies on iterating through the each part of the dotted name, 
        calling L{_localNameToFullName} for each name in their associated context and incrementally building 
        the fullName from that. 

        Lookup members in superclasses when possible and follows L{DocumentableKind.ALIAS}. This mean that L{expandName} will never return the name of an alias,
        it will always follow it's indirection to the origin.
    """

    parts = name.split('.')
    ctx: model.Documentable = self # The context for the currently processed part of the name. 
    for i, part in enumerate(parts):
        if i > 0 and not isinstance(ctx, model.CanContainImportsDocumentable):
            # Stop now, this is a big blind spot of this function. 
            # The problem is that trying to resolve an attribute (because i > 0 meaning we're resolving an attribute part of the name)
            # within the context of another attribute or function will always fallback to the parent scope, which is simply wrong.
            # So we stop resolving the name when we encounter something that is not a class or module. 
            full_name = f'{ctx.fullName()}.{part}'
            break
        full_name = _localNameToFullName(ctx, part, indirections)
        if full_name == part and i != 0:
            # The local name was not found.
            # If we're looking at a class, we try our luck with the inherited members
            if isinstance(ctx, model.Class):
                inherited = ctx.find(part)
                if inherited: 
                    full_name = inherited.fullName()
            if full_name == part:
                # We don't have a full name
                # TODO: Instead of returning the input, _localNameToFullName()
                #       should probably either return None or raise LookupError.
                # Or maybe we should find a way to indicate if the expanded name is "guessed" or if we have the the correct fullName. 
                # With the current implementation, this would mean checking if "parts[i + 1:]" contains anything.
                full_name = f'{ctx.fullName()}.{part}'
                break
        nxt = self.system.objForFullName(full_name)
        if nxt is None:
            break
        ctx = nxt

    return '.'.join([full_name] + parts[i + 1:])
