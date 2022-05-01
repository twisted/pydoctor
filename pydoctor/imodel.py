"""
Interface classes for core pydoctor objetcs.

@Note: Concrete classes MUST subclass base classes defined below.
"""

import abc
import ast
import sys
from datetime import datetime
from enum import Enum, auto
from inspect import Signature
from pathlib import Path

from typing import (Collection, Iterator, List, Mapping, 
                    MutableMapping, Optional, Sequence, 
                    Set, Tuple, Type, TypeVar, Union, 
                    runtime_checkable, TYPE_CHECKING)

if sys.version_info < (3, 8):
    from typing_extensions import Protocol
else:
    from typing import Protocol

if TYPE_CHECKING:
    from pydoctor.epydoc.markup import ParsedDocstring, DocstringLinker
    from pydoctor.sphinx import CacheT, SphinxInventory
    from pydoctor.options import Options

class DocLocation(Enum):
    OWN_PAGE: int = auto()
    PARENT_PAGE: int = auto()
    # Nothing uses this yet.  Parameters will one day.
    #UNDER_PARENT_DOCSTRING = 3


class PrivacyClass(Enum):
    HIDDEN: int = auto()
    PRIVATE: int = auto()
    PUBLIC: int = auto()
    # For compatibility
    VISIBLE = PUBLIC

class DocumentableKind(Enum):
    """
    L{Enum} containing values indicating the possible object types.

    @note: Presentation order is derived from the enum values
    """
    PACKAGE             = 1000
    MODULE              = 900
    CLASS               = 800
    INTERFACE           = 850
    CLASS_METHOD        = 700
    STATIC_METHOD       = 600
    METHOD              = 500
    FUNCTION            = 400
    CONSTANT            = 310
    CLASS_VARIABLE      = 300
    SCHEMA_FIELD        = 220
    ATTRIBUTE           = 210
    INSTANCE_VARIABLE   = 200
    PROPERTY            = 150
    VARIABLE            = 100

@runtime_checkable
class IDocumentable(Protocol):
    """
    An object that can be documented.

    The interface is a bit ridiculously wide.

    @ivar docstring: The object's docstring.  But also see docsources.
    @ivar system: The system the object is part of.
    """

    docstring: Optional[str]
    parsed_docstring: Optional['ParsedDocstring']
    parsed_summary: Optional['ParsedDocstring']
    parsed_type: Optional['ParsedDocstring']
    docstring_lineno: int
    linenumber: int
    sourceHref: Optional[str]
    kind: Optional[DocumentableKind]
    documentation_location: DocLocation
    """Page location where we are documented."""

    system: 'ISystem'
    name: str
    parent: Optional['IDocumentable']
    source_path: Optional[Path]
    contents: MutableMapping[str, 'IDocumentable']
    extra_info: List['ParsedDocstring']
    
    def __init__(self, system: 'ISystem', name: str, 
                 parent: Optional['IDocumentable'] = ..., 
                 source_path: Optional[Path] = ...) -> None: ...
    
    def setup(self) -> None: ...
    def setLineNumber(self, lineno: int) -> None: ...
    @property
    def description(self) -> str:
        """A string describing our source location to the user.

        If this module's code was read from a file, this returns
        its file path. In other cases, such as during unit testing,
        the full module name is returned.
        """
    @property
    def page_object(self) -> 'IDocumentable':
        """The documentable to which the page we're documented on belongs.
        For example methods are documented on the page of their class,
        functions are documented in their module's page etc.
        """
    @property
    def url(self) -> str:
        """Relative URL at which the documentation for this Documentable
        can be found.

        For page objects this method MUST return an C{.html} filename without a
        URI fragment (because L{pydoctor.templatewriter.writer.TemplateWriter}
        uses it directly to determine the output filename).
        """
    def fullName(self) -> str: ...
    def docsources(self) -> Iterator['IDocumentable']:
        """Objects that can be considered as a source of documentation.

        The motivating example for having multiple sources is looking at a
        superclass' implementation of a method for documentation for a
        subclass'.
        """
    def reparent(self, new_parent: 'IModule', new_name: str) -> None: ...
    def expandName(self, name: str) -> str:
        """Return a fully qualified name for the possibly-dotted `name`.

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

        In the context of mod2.E, expandName("RenamedExternal") should be
        "external_location.External" and expandName("renamed_mod.Local")
        should be "mod1.Local". """
    def resolveName(self, name: str) -> Optional['IDocumentable']:
        """Return the object named by "name" (using Python's lookup rules) in
        this context, if any is known to pydoctor."""
    @property
    def privacyClass(self) -> PrivacyClass:
        """How visible this object should be."""
    @property
    def isVisible(self) -> bool:
        """Is this object so private as to be not shown at all?

        This is just a simple helper which defers to self.privacyClass.
        """
    @property
    def isPrivate(self) -> bool:
        """Is this object considered private API?

        This is just a simple helper which defers to self.privacyClass.
        """
    @property
    def module(self) -> 'IModule':
        """This object's L{Module}.

        For modules, this returns the object itself, otherwise
        the module containing the object is returned.
        """
    def report(self, descr: str, section: str = ..., lineno_offset: int = ...) -> None:
        """Log an error or warning about this documentable object."""
    @property
    def docstring_linker(self) -> 'DocstringLinker':
        """
        Returns an instance of L{DocstringLinker} suitable for resolving names
        in the context of the object scope. 
        """

IDocumentableT = TypeVar('IDocumentableT', bound=IDocumentable)

@runtime_checkable
class ICanContainImportsDocumentable(IDocumentable, Protocol):
    ...

@runtime_checkable
class IModule(ICanContainImportsDocumentable, Protocol):
    all:Optional[List[str]]
    """Names listed in the C{__all__} variable of this module.

    These names are considered to be exported by the module,
    both for the purpose of C{from <module> import *} and
    for the purpose of publishing names from private modules.

    If no C{__all__} variable was found in the module, or its
    contents could not be parsed, this is L{None}.
    """

    @property
    def docformat(self) -> Optional[str]: ...
    @docformat.setter
    def docformat(self, value: str) -> None: ...
    def submodules(self) -> Iterator['IModule']: ...

@runtime_checkable
class IPackage(IModule, Protocol):
    ...

@runtime_checkable
class IClass(ICanContainImportsDocumentable, Protocol):
    parent: ICanContainImportsDocumentable
    bases: List[str]
    baseobjects: List[Optional['IClass']]
    decorators: Sequence[Tuple[str, Optional[Sequence[ast.expr]]]]
    raw_decorators: Sequence[ast.expr]
    auto_attribs: bool
    rawbases: List[str]
    subclasses: List['IClass']

    def allbases(self, include_self: bool = ...) -> Iterator['IClass']: ...
    def find(self, name: str) -> Optional[IDocumentable]: 
        """Look up a name in this class and its base classes.

        @return: the object with the given name, or L{None} if there isn't one
        """
    @property
    def constructor_params(self) -> Mapping[str, Optional[ast.expr]]: 
        """A mapping of constructor parameter names to their type annotation.
        If a parameter is not annotated, its value is L{None}.
        """

@runtime_checkable
class IInheritable(IDocumentable, Protocol):
    ...

@runtime_checkable
class IFunction(IInheritable, Protocol):
    is_async: bool
    annotations: Mapping[str, Optional[ast.expr]]
    decorators: Optional[Sequence[ast.expr]]
    signature: Optional[Signature]

@runtime_checkable
class IAttribute(IInheritable, Protocol):
    kind: Optional[DocumentableKind]
    annotation: Optional[ast.expr]
    decorators: Optional[Sequence[ast.expr]]
    value: Optional[ast.expr]
    """
    The value of the assignment expression. 

    None value means the value is not initialized at the current point of the the process. 
    """

T = TypeVar('T')
# Work around the attributes of the same name within the System class.
_ModuleT = IModule
_PackageT = IPackage
_ClassT = IClass
_FunctionT = IFunction
_AttributeT = IAttribute

@runtime_checkable
class ISystem(Protocol):
    """A collection of related documentable objects.

    PyDoctor documents collections of objects, often the contents of a
    package.
    """
    Class: Type[_ClassT]
    Module: Type[_ModuleT]
    Package: Type[_PackageT]
    Function: Type[_FunctionT]
    Attribute: Type[_AttributeT]

    systemBuilder: Type['ISystemBuilder']

    options: 'Options'
    allobjects: MutableMapping[str, 'IDocumentable']
    rootobjects: List[_ModuleT]
    violations: int
    """The number of docstring problems found.
    This is used to determine whether to fail the build when using
    the --warnings-as-errors option, so it should only be increased
    for problems that the user can fix.
    """
    projectname: str
    docstring_syntax_errors: Set[str]
    """FullNames of objects for which the docstring failed to parse."""
    buildtime: datetime
    intersphinx: 'SphinxInventory'
    def __init__(self, options: Optional['Options'] = ...) -> None: ...
    @property
    def sourcebase(self) -> Optional[str]: ...
    @property
    def root_names(self) -> Collection[str]: ...
    def progress(self, section: str, i: int, n: Optional[int], msg: str) -> None: ...
    def msg(self, section: str, msg: str, thresh: int = ..., topthresh: int = ..., nonl: bool = ..., wantsnl: bool = ..., once: bool = ...) -> None: ...
    def objForFullName(self, fullName: str) -> Optional[IDocumentable]: ...
    def find_object(self, full_name: str) -> Optional[IDocumentable]: ...
    def objectsOfType(self, cls: Union[Type[IDocumentableT], str]) -> Iterator[IDocumentableT]: ...
    def privacyClass(self, ob: IDocumentable) -> PrivacyClass: ...
    def fetchIntersphinxInventories(self, cache: 'CacheT') -> None: ...
    def addObject(self, obj: IDocumentable) -> None: ...
    def setSourceHref(self, mod: _ModuleT, source_path: Path) -> None: ...

class SystemBuildingError(Exception):
    """
    Raised when there is a (handled) fatal error while adding modules to the builder.
    """

class ISystemBuilder(abc.ABC):
    """
    Interface class for building a system.
    """
    @abc.abstractmethod
    def __init__(self, system: 'ISystem') -> None:
        """
        Create the builder.
        """
    @abc.abstractmethod
    def addModule(self, path: Path, parent_name: Optional[str] = None, ) -> None:
        """
        Add a module or package from file system path to the pydoctor system. 
        If the path points to a directory, adds all submodules recursively.

        @raises SystemBuildingError: If there is an error while adding the module/package.
        """
    @abc.abstractmethod
    def addModuleString(self, text: str, modname: str,
                        parent_name: Optional[str] = None,
                        is_package: bool = False, ) -> None:
        """
        Add a module from text to the system.
        """
    @abc.abstractmethod
    def buildModules(self) -> None:
        """
        Build the modules.
        """

# Aliases to ease the transition
Documentable = IDocumentable
System = ISystem
CanContainImportsDocumentable = ICanContainImportsDocumentable
Module = IModule
Package = IPackage
Class = IClass
Inheritable = IInheritable
Attribute = IAttribute
Function = IFunction
