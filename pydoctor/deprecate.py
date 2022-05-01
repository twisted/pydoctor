
# Copyright (c) Twisted Matrix Laboratories.
# Adjusted from file twisted/python/_pydoctor.py

"""
Support for L{twisted.python.deprecate}.
"""

import ast
import inspect
from numbers import Number
from typing import Optional, Sequence, Union, TYPE_CHECKING, cast

from pydoctor import astbuilder, model, zopeinterface, epydoc2stan, astutils

from twisted.python.deprecate import deprecated, _getDeprecationWarningString
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
                    text = deprecatedToUsefulText(self, self.name, a)
                except Exception as e:
                    # It's a reference or something that we can't figure out
                    # from the AST.
                    self.report(str(e), section='deprecation text')
                else:
                    # Add a warning with reStructuredText .. warning:: directive.
                    parsed_info = epydoc2stan.parse_docstring(self,
                        ".. warning:: {}".format(text), self, 
                        markup='restructuredtext', 
                        section='deprecation text')

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
        assert isinstance(cls, model.Class)
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
        assert isinstance(func, (model.Function, model.Attribute))
        if func.decorators:
            getDeprecated(func, func.decorators)


def versionToUsefulObject(version:ast.Call) -> 'incremental.Version':
    """
    Change an AST C{Version()} to a real one.

    @raises ValueError: If the incremental.Version call is invalid.
    """

    package = astutils.get_str_value(version.args[0])
    major: Union[Number, str, None] = astutils.get_num_value(version.args[1]) or astutils.get_str_value(version.args[1])
    if isinstance(major, str) and major != "NEXT": 
        raise ValueError("Invalid call to incremental.Version(), first argument should be an int or 'NEXT'.")
    return Version(package, major, *(astutils.get_num_value(x) for x in version.args[2:] if x))

_deprecated_signature = inspect.signature(deprecated)
def deprecatedToUsefulText(ctx:model.Documentable, name:str, deprecated:ast.Call) -> str:
    """
    Change a C{@deprecated} to a display string.

    @param ctx: The context in which the deprecation is evaluated.
    @param name: The name of the thing we're deprecating.
    @param deprecated: AST call to L{twisted.python.deprecate.deprecated} or L{twisted.python.deprecate.deprecatedProperty}.
    @returns: The text tu use in the deprecation warning.
    @raises ValueError or TypeError: If something is wrong.
    """

    bound_args = astutils.bind_args(_deprecated_signature, deprecated)
    _version_call = bound_args.arguments.get('version')
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

    return cast(str, _getDeprecationWarningString(name, version, replacement=replacement)) + "."


class ASTBuilder(zopeinterface.ZopeInterfaceASTBuilder):
    # Vistor is not a typo...
    ModuleVistor = ModuleVisitor


class System(zopeinterface.ZopeInterfaceSystem):
    """
    A system aware of {twisted.python.deprecate.deprecated} and cie.
    """

    defaultBuilder = ASTBuilder
