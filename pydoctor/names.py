"""
Module containing the logic to resolve names, aliases and imports.
"""
from typing import Optional, List

from pydoctor import model

# _IndirectionT = Union[model.Attribute, model.Import]
_IndirectionT = model.Attribute

def _localDocumentableToFullName(ctx: model.Documentable, o: 'model.Documentable', 
                            indirections:Optional[List['_IndirectionT']]=None) -> Optional[str]:
    """
    If the documentable is an alias, then follow it and return the supposed full name fo the documentable object,
    or return the passed object's - C{o} - full name.

    Calls L{_resolveAlias} if the documentable is an alias.
    """
    if o.kind is model.DocumentableKind.ALIAS:
        assert isinstance(o, model.Attribute)
        return _resolveAlias(ctx, o, indirections)
    return o.fullName()

def _localNameToFullName(ctx: model.Documentable, name: str, indirections:Optional[List['_IndirectionT']]=None) -> str:
    if isinstance(ctx, model.CanContainImportsDocumentable):
        # Local names and aliases
        if name in ctx.contents:
            resolved = _localDocumentableToFullName(ctx, ctx.contents[name], indirections)
            if resolved:
                return resolved
        
        # Imports
        if name in ctx._localNameToFullName_map:
            return _localImportToFullName(ctx, name, indirections)
        
        # Not found
        if isinstance(ctx, model.Class):
            # for classes, we try the upper scope.
            return _localNameToFullName(ctx.parent, name)
        else:
            return name
    else:
        assert ctx.parent is not None
        return _localNameToFullName(ctx.parent, name)

def _localImportToFullName(ctx: model.CanContainImportsDocumentable, name:str, indirections:Optional[List['_IndirectionT']]=None) -> str:
    fullName = ctx._localNameToFullName_map[name]
    allobjects = ctx.system.allobjects

    if fullName in allobjects:
        # the imported name is an alias, so follow it
        resolved = _localDocumentableToFullName(ctx, allobjects[fullName], indirections)
        if resolved:
            return resolved
        
    # # TODO: We could follow imported modules by doing something like:
    # dottedName = fullName.split('.')
    # parentName = '.'.join(dottedName[0:-1])
    # targetName = dottedName[-1]
    
    # if parentName in allobjects:
    #     parent = allobjects[parentName]
    #     if isinstance(parent, model.CanContainImportsDocumentable):
    #         if targetName in parent._localNameToFullName_map:
    #             ...
    #             # the imported name is an imported name, so follow it

    return fullName

# TODO: This same function should be applicable for imports sa well.
def _resolveAlias(self: model.Documentable, alias: _IndirectionT, indirections:Optional[List[_IndirectionT]]=None) -> Optional[str]:
    """
    Resolve the indirection value to it's target full name.
    Or fall back to original name if we've exhausted the max recursions.
    
    @param alias: an indirection (alias or import)
    @param indirections: Chain of indirection objects followed. 
        This variable is used to prevent infinite loops when doing the lookup.
    """
    
    indirections = indirections if isinstance(indirections, list) else []

    if indirections and len(indirections) > self._RESOLVE_ALIAS_MAX_RECURSE:
        self.report("Too many aliases: can't resolve")
        return indirections[0].fullName() 

    # the alias attribute should never be None for indirections objects
    name = alias.alias
    if name is None:
        self.report("Error resolving alias")
        return indirections[0].fullName() 
    
    # the context is important
    ctx = self

    if alias not in indirections:
        # We redirect to the original object
        return ctx.expandName(name, indirections=indirections+[alias])
    
    # Prevent recursion errors, we try the upper scope only if we detect a dicrect cycle.
    # Otherwise just fail.
    if alias is not indirections[-1]:
        self.report("Recursive aliases: can't resolve")
        return indirections[0].fullName()

    # Issue tracing the alias back to it's original location, found the same alias again.
    parent = ctx.parent
    if parent is not None and not isinstance(self, model.Module):
        # We try with the parent scope and redirect to the original object!
        # This is used in situations like right here in the System class and it's aliases (before version > 22.5.1), 
        # because they have the same name as the name they are aliasing, it's causing trouble.
        # We could use astuce here to be more precise.
        return parent.expandName(name, indirections=indirections+[alias])

    return None

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
