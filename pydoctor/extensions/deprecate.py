
# Copyright (c) Twisted Matrix Laboratories.
# Adjusted from file twisted/python/_pydoctor.py

"""
Support for L{twisted.python.deprecate}.
"""
from __future__ import annotations

import ast
import inspect
from typing import Optional, Sequence, Tuple, Union, TYPE_CHECKING

from pydoctor import astbuilder, model, epydoc2stan, astutils, extensions

from twisted.python.deprecate import deprecated
from incremental import Version

if TYPE_CHECKING:
    import incremental

def getDeprecated(self:model.Documentable, decorators:Sequence[ast.expr]) -> None:
    """
    With a list of decorators, and the object it is running on, set the
    C{_deprecated_info} flag if any of the decorators are a Twisted deprecation
    decorator.
    """
    for a in decorators:
        if isinstance(a, ast.Call):
            fn = astbuilder.node2fullname(a.func, self)

            if fn in (
                "twisted.python.deprecate.deprecated",
                "twisted.python.deprecate.deprecatedProperty",
            ):
                try:
                    version, text = deprecatedToUsefulText(self, self.name, a)
                except Exception as e:
                    # It's a reference or something that we can't figure out
                    # from the AST.
                    self.report(str(e), section='deprecation text')
                else:
                    # Add a deprecation info with reStructuredText .. deprecated:: directive.
                    parsed_info = epydoc2stan.parse_docstring(
                        obj=self,
                        doc=f".. deprecated:: {version}\n   {text}", 
                        source=self, 
                        markup='restructuredtext', 
                        section='deprecation text',)
                    self.extra_info.append(parsed_info)

class ModuleVisitor(extensions.ModuleVisitorExt):
    
    def depart_ClassDef(self, node:ast.ClassDef) -> None:
        """
        Called after a class definition is visited.
        """
        current = self.visitor.builder.current
        try:
            cls = current.contents[node.name]
        except KeyError:
            # Classes inside functions are ignored.
            return
        getDeprecated(cls, node.decorator_list)

    def depart_FunctionDef(self, node:ast.FunctionDef) -> None:
        """
        Called after a function definition is visited.
        """
        current = self.visitor.builder.current
        try:
            # Property or Function
            func = current.contents[node.name]
        except KeyError:
            # Inner functions are ignored.
            return
        getDeprecated(func, node.decorator_list)

_incremental_Version_signature = inspect.signature(Version)
def versionToUsefulObject(version:ast.Call) -> 'incremental.Version':
    """
    Change an AST C{Version()} to a real one.

    @note: Only use required arguments, ignores arguments release_candidate, prerelease, post, dev.
    @raises ValueError: If the incremental.Version call is invalid.
    """
    bound_args = astutils.bind_args(_incremental_Version_signature, version)
    package = astutils.get_str_value(bound_args.arguments['package'])
    major: Union[int, str, None] = astutils.get_int_value(bound_args.arguments['major']) or \
        astutils.get_str_value(bound_args.arguments['major'])
    if major is None or (isinstance(major, str) and major != "NEXT"): 
        raise ValueError("Invalid call to incremental.Version(), 'major' should be an int or 'NEXT'.")
    assert isinstance(major, (int, str))
    minor = astutils.get_int_value(bound_args.arguments['minor'])
    micro = astutils.get_int_value(bound_args.arguments['micro'])
    if minor is None or micro is None:
        raise ValueError("Invalid call to incremental.Version(), 'minor' and 'micro' should be an ints.")
    return Version(package, major, minor=minor, micro=micro) # type:ignore[arg-type]

_deprecation_text_with_replacement_template = "``{name}`` was deprecated in {package} {version}; please use `{replacement}` instead."
_deprecation_text_without_replacement_template = "``{name}`` was deprecated in {package} {version}."

_deprecated_signature = inspect.signature(deprecated)
def deprecatedToUsefulText(ctx:model.Documentable, name:str, deprecated:ast.Call) -> Tuple[str, str]:
    """
    Change a C{@deprecated} to a display string.

    @param ctx: The context in which the deprecation is evaluated.
    @param name: The name of the thing we're deprecating.
    @param deprecated: AST call to L{twisted.python.deprecate.deprecated} or L{twisted.python.deprecate.deprecatedProperty}.
    @returns: The version and text to use in the deprecation warning.
    @raises ValueError or TypeError: If something is wrong.
    """

    bound_args = astutils.bind_args(_deprecated_signature, deprecated)
    _version_call = bound_args.arguments['version']
    
    # Also support using incremental from twisted.python.versions: https://github.com/twisted/twisted/blob/twisted-22.4.0/src/twisted/python/versions.py
    if not isinstance(_version_call, ast.Call) or \
       astbuilder.node2fullname(_version_call.func, ctx) not in ("incremental.Version", "twisted.python.versions.Version"):
        raise ValueError("Invalid call to twisted.python.deprecate.deprecated(), first argument should be a call to incremental.Version()")
    
    version = versionToUsefulObject(_version_call)
    replacement: Optional[str] = None

    replvalue = bound_args.arguments.get('replacement')
    if replvalue is not None:
        if astutils.node2dottedname(replvalue) is not None:
            replacement = astbuilder.node2fullname(replvalue, ctx)
        else:
            replacement = astutils.get_str_value(replvalue)
    _version = version.public()
    _package = version.package

    # Avoids html injections
    def validate_identifier(_text:str) -> bool:
        if not all(p.isidentifier() for p in _text.split('.')):
            return False
        return True

    if not validate_identifier(_package):
        raise ValueError(f"Invalid package name: {_package!r}")
    
    if replacement is not None and not validate_identifier(replacement):
        # The replacement is not an identifier, so don't even try to resolve it.
        # By adding extras backtics, we make the replacement a literal text.
        replacement = replacement.replace('\n', ' ')
        replacement = f"`{replacement}`"
    
    if replacement is not None:
        text = _deprecation_text_with_replacement_template.format(
            name=name, 
            package=_package,
            version=_version,
            replacement=replacement
        )
    else:
        text = _deprecation_text_without_replacement_template.format(
            name=name, 
            package=_package,
            version=_version,
        )
    return _version, text

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitor(ModuleVisitor)
