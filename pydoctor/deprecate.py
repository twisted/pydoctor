
# Copyright (c) Twisted Matrix Laboratories.
# Adjusted from file twisted/python/_pydoctor.py

"""
Support for L{twisted.python.deprecate}.
"""

import ast
import inspect
from numbers import Number
from typing import Optional, Sequence, Tuple, Union, TYPE_CHECKING

from pydoctor import astbuilder, imodel as model, zopeinterface, epydoc2stan, astutils

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


class ModuleVisitor(zopeinterface.ZopeInterfaceModuleVisitor):
    def visit_ClassDef(self, node:ast.ClassDef) -> None:
        """
        Called when a class definition is visited.
        """
        super().visit_ClassDef(node)
        try:
            cls = self.builder.current.contents[node.name]
        except KeyError:
            # Classes inside functions are ignored.
            return
        assert isinstance(cls, cls.system.Class)
        getDeprecated(cls, cls.raw_decorators)

    def visit_FunctionDef(self, node:ast.FunctionDef) -> None:
        """
        Called when a function definition is visited.
        """
        super().visit_FunctionDef(node)
        try:
            func = self.builder.current.contents[node.name]
        except KeyError:
            # Inner functions are ignored.
            return
        assert isinstance(func, (func.system.Function, func.system.Attribute))
        if func.decorators:
            getDeprecated(func, func.decorators)

_incremental_Version_signature = inspect.signature(Version)
def versionToUsefulObject(version:ast.Call) -> 'incremental.Version':
    """
    Change an AST C{Version()} to a real one.

    @note: Only use required arguments, ignores arguments release_candidate, prerelease, post, dev.
    @raises ValueError: If the incremental.Version call is invalid.
    """
    bound_args = astutils.bind_args(_incremental_Version_signature, version)
    package = astutils.get_str_value(bound_args.arguments['package'])
    major: Union[Number, str, None] = astutils.get_num_value(bound_args.arguments['major']) or \
        astutils.get_str_value(bound_args.arguments['major'])
    if isinstance(major, str) and major != "NEXT": 
        raise ValueError("Invalid call to incremental.Version(), 'major' should be an int or 'NEXT'.")
    return Version(package, major, 
        minor=astutils.get_num_value(bound_args.arguments['minor']),
        micro=astutils.get_num_value(bound_args.arguments['micro']),)

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
    if not isinstance(_version_call, ast.Call) or \
       astbuilder.node2fullname(_version_call.func, ctx) != "incremental.Version":
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
        raise ValueError(f"Invalid replacement name: {replacement!r}")
    
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


class ASTBuilder(zopeinterface.ZopeInterfaceASTBuilder):
    # Vistor is not a typo...
    ModuleVistor = ModuleVisitor


class System(zopeinterface.ZopeInterfaceSystem):
    """
    A system with support for {twisted.python.deprecate}.
    """

    defaultBuilder = ASTBuilder
