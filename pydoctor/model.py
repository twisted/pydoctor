"""Core pydoctor objects.

The two core objects are L{Documentable} and L{System}.  Instances of
(subclasses of) L{Documentable} represent the documentable 'things' in the
system being documented.  An instance of L{System} represents the whole system
being documented -- a System is a bad of Documentables, in some sense.
"""

import abc
import ast
import attr
from collections import defaultdict
import datetime
import importlib
import platform
import sys
import textwrap
import types
from enum import Enum
from inspect import signature, Signature
from pathlib import Path
from typing import (
    TYPE_CHECKING, Any, Callable, Collection, Dict, Iterator, List, Mapping,
    Optional, Sequence, Set, Tuple, Type, TypeVar, Union, cast, overload
)
from urllib.parse import quote

from pydoctor.options import Options
from pydoctor import factory, qnmatch, utils, linker, astutils, mro
from pydoctor.epydoc.markup import ParsedDocstring
from pydoctor.sphinx import CacheT, SphinxInventory

import attr

if TYPE_CHECKING:
    from typing_extensions import Literal
    from pydoctor.astbuilder import ASTBuilder, DocumentableT
else:
    Literal = {True: bool, False: bool}
    ASTBuilder = object


# originally when I started to write pydoctor I had this idea of a big
# tree of Documentables arranged in an almost arbitrary tree.
#
# this was misguided.  the tree structure is important, to be sure,
# but the arrangement of the tree is far from arbitrary and there is
# at least some code that now relies on this.  so here's a list:
#
#   Packages can contain Packages and Modules
#   Modules can contain Functions and Classes
#   Classes can contain Functions (in this case they get called Methods) and
#       Classes
#   Functions can't contain anything.


_string_lineno_is_end = sys.version_info < (3,8) \
                    and platform.python_implementation() != 'PyPy'
"""True iff the 'lineno' attribute of an AST string node points to the last
line in the string, rather than the first line.
"""


class DocLocation(Enum):
    OWN_PAGE = 1
    PARENT_PAGE = 2
    # Nothing uses this yet.  Parameters will one day.
    #UNDER_PARENT_DOCSTRING = 3


class ProcessingState(Enum):
    UNPROCESSED = 0
    PROCESSING = 1
    PROCESSED = 2


class PrivacyClass(Enum):
    """L{Enum} containing values indicating how private an object should be.

    @cvar HIDDEN: Don't show the object at all.
    @cvar PRIVATE: Show, but de-emphasize the object.
    @cvar PUBLIC: Show the object as normal.
    """

    HIDDEN = 0
    PRIVATE = 1
    PUBLIC = 2
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
    EXCEPTION           = 750
    CLASS_METHOD        = 700
    STATIC_METHOD       = 600
    METHOD              = 500
    FUNCTION            = 400
    CONSTANT            = 310
    TYPE_VARIABLE       = 306
    TYPE_ALIAS          = 305
    CLASS_VARIABLE      = 300
    SCHEMA_FIELD        = 220
    ATTRIBUTE           = 210
    INSTANCE_VARIABLE   = 200
    PROPERTY            = 150
    VARIABLE            = 100

class Documentable:
    """An object that can be documented.

    The interface is a bit ridiculously wide.

    @ivar docstring: The object's docstring.  But also see docsources.
    @ivar system: The system the object is part of.

    """
    docstring: Optional[str] = None
    parsed_docstring: Optional[ParsedDocstring] = None
    parsed_summary: Optional[ParsedDocstring] = None
    parsed_type: Optional[ParsedDocstring] = None
    docstring_lineno = 0
    linenumber = 0
    sourceHref: Optional[str] = None
    kind: Optional[DocumentableKind] = None

    documentation_location = DocLocation.OWN_PAGE
    """Page location where we are documented."""

    def __init__(
            self, system: 'System', name: str,
            parent: Optional['Documentable'] = None,
            source_path: Optional[Path] = None
            ):
        if source_path is None and parent is not None:
            source_path = parent.source_path
        self.system = system
        self.name = name
        self.parent = parent
        self.parentMod: Optional[Module] = None
        self.source_path: Optional[Path] = source_path
        self.extra_info: List[ParsedDocstring] = []
        """
        A list to store extra informations about this documentable, as L{ParsedDocstring}.
        """
        self.setup()

    @property
    def doctarget(self) -> 'Documentable':
        return self

    def setup(self) -> None:
        self.contents: Dict[str, Documentable] = {}
        self._linker: Optional['linker.DocstringLinker'] = None

    def setDocstring(self, node: ast.Str) -> None:
        lineno, doc = astutils.extract_docstring(node)
        self.docstring = doc
        self.docstring_lineno = lineno

    def setLineNumber(self, lineno: int) -> None:
        if not self.linenumber:
            self.linenumber = lineno
            parentMod = self.parentMod
            if parentMod is not None:
                parentSourceHref = parentMod.sourceHref
                if parentSourceHref:
                    self.sourceHref = self.system.options.htmlsourcetemplate.format(
                        mod_source_href=parentSourceHref,
                        lineno=str(lineno)
                    )

    @property
    def description(self) -> str:
        """A string describing our source location to the user.

        If this module's code was read from a file, this returns
        its file path. In other cases, such as during unit testing,
        the full module name is returned.
        """
        source_path = self.source_path
        return self.module.fullName() if source_path is None else str(source_path)

    @property
    def page_object(self) -> 'Documentable':
        """The documentable to which the page we're documented on belongs.
        For example methods are documented on the page of their class,
        functions are documented in their module's page etc.
        """
        location = self.documentation_location
        if location is DocLocation.OWN_PAGE:
            return self
        elif location is DocLocation.PARENT_PAGE:
            parent = self.parent
            assert parent is not None
            return parent
        else:
            assert False, location

    @property
    def url(self) -> str:
        """Relative URL at which the documentation for this Documentable
        can be found.

        For page objects this method MUST return an C{.html} filename without a
        URI fragment (because L{pydoctor.templatewriter.writer.TemplateWriter}
        uses it directly to determine the output filename).
        """
        page_obj = self.page_object
        if list(self.system.root_names) == [page_obj.fullName()]:
            page_url = 'index.html'
        else:
            page_url = f'{quote(page_obj.fullName())}.html'
        if page_obj is self:
            return page_url
        else:
            return f'{page_url}#{quote(self.name)}'

    def fullName(self) -> str:
        parent = self.parent
        if parent is None:
            return self.name
        else:
            return f'{parent.fullName()}.{self.name}'

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} {self.fullName()!r}"

    def docsources(self) -> Iterator['Documentable']:
        """Objects that can be considered as a source of documentation.

        The motivating example for having multiple sources is looking at a
        superclass' implementation of a method for documentation for a
        subclass'.
        """
        yield self


    def reparent(self, new_parent: 'Module', new_name: str) -> None:
        # this code attempts to preserve "rather a lot" of
        # invariants assumed by various bits of pydoctor
        # and that are of course not written down anywhere
        # :/
        self._handle_reparenting_pre()
        old_parent = self.parent
        assert isinstance(old_parent, CanContainImportsDocumentable)
        old_name = self.name
        self.parent = self.parentMod = new_parent
        self.name = new_name
        self._handle_reparenting_post()
        del old_parent.contents[old_name]
        old_parent._localNameToFullName_map[old_name] = self.fullName()
        new_parent.contents[new_name] = self
        self._handle_reparenting_post()

    def _handle_reparenting_pre(self) -> None:
        del self.system.allobjects[self.fullName()]
        for o in self.contents.values():
            o._handle_reparenting_pre()

    def _handle_reparenting_post(self) -> None:
        self.system.allobjects[self.fullName()] = self
        for o in self.contents.values():
            o._handle_reparenting_post()

    def _localNameToFullName(self, name: str) -> str:
        raise NotImplementedError(self._localNameToFullName)

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
        parts = name.split('.')
        obj: Documentable = self
        for i, p in enumerate(parts):
            full_name = obj._localNameToFullName(p)
            if full_name == p and i != 0:
                # The local name was not found.
                # If we're looking at a class, we try our luck with the inherited members
                if isinstance(obj, Class):
                    inherited = obj.find(p)
                    if inherited: 
                        full_name = inherited.fullName()
                if full_name == p:
                    # We don't have a full name
                    # TODO: Instead of returning the input, _localNameToFullName()
                    #       should probably either return None or raise LookupError.
                    full_name = f'{obj.fullName()}.{p}'
                    break
            nxt = self.system.objForFullName(full_name)
            if nxt is None:
                break
            obj = nxt
        return '.'.join([full_name] + parts[i + 1:])

    def resolveName(self, name: str) -> Optional['Documentable']:
        """Return the object named by "name" (using Python's lookup rules) in
        this context, if any is known to pydoctor."""
        return self.system.objForFullName(self.expandName(name))

    @property
    def privacyClass(self) -> PrivacyClass:
        """How visible this object should be."""
        return self.system.privacyClass(self)

    @property
    def isVisible(self) -> bool:
        """Is this object so private as to be not shown at all?

        This is just a simple helper which defers to self.privacyClass.
        """
        isVisible = self.privacyClass is not PrivacyClass.HIDDEN
        # If a module/package/class is hidden, all it's members are hidden as well.
        if isVisible and self.parent:
            isVisible = self.parent.isVisible
        return isVisible

    @property
    def isPrivate(self) -> bool:
        """Is this object considered private API?

        This is just a simple helper which defers to self.privacyClass.
        """
        return self.privacyClass is not PrivacyClass.PUBLIC

    @property
    def module(self) -> 'Module':
        """This object's L{Module}.

        For modules, this returns the object itself, otherwise
        the module containing the object is returned.
        """
        parentMod = self.parentMod
        assert parentMod is not None
        return parentMod

    def report(self, descr: str, section: str = 'parsing', lineno_offset: int = 0, thresh:int=-1) -> None:
        """
        Log an error or warning about this documentable object.

        @param descr: The error/warning string
        @param section: What the warning is about.
        @param lineno_offset: Offset
        @param thresh: Thresh to pass to L{System.msg}, it will use C{-1} by default, 
          meaning it will count as a violation and will fail the build if option C{-W} is passed.
          But this behaviour is not applicable if C{thresh} is greater or equal to zero.
        """

        linenumber: object
        if section in ('docstring', 'resolve_identifier_xref'):
            linenumber = self.docstring_lineno or self.linenumber
        else:
            linenumber = self.linenumber
        if linenumber:
            linenumber += lineno_offset
        elif lineno_offset and self.module is self:
            linenumber = lineno_offset
        else:
            linenumber = '???'

        self.system.msg(
            section,
            f'{self.description}:{linenumber}: {descr}',
            thresh=thresh)

    @property
    def docstring_linker(self) -> 'linker.DocstringLinker':
        """
        Returns an instance of L{DocstringLinker} suitable for resolving names
        in the context of the object scope. 
        """
        if self._linker is not None:
            return self._linker
        self._linker = linker._CachedEpydocLinker(self)
        return self._linker


class CanContainImportsDocumentable(Documentable):
    def setup(self) -> None:
        super().setup()
        self._localNameToFullName_map: Dict[str, str] = {}


class Module(CanContainImportsDocumentable):
    kind = DocumentableKind.MODULE
    state = ProcessingState.UNPROCESSED

    @property
    def privacyClass(self) -> PrivacyClass:
        if self.name == '__main__':
            return PrivacyClass.PRIVATE
        else:
            return super().privacyClass

    def setup(self) -> None:
        super().setup()

        self._is_c_module = False
        """Whether this module is a C-extension."""
        self._py_mod: Optional[types.ModuleType] = None
        """The live module if the module was built from introspection."""
        self._py_string: Optional[str] = None
        """The module string if the module was built from text."""

        self.all: Optional[Collection[str]] = None
        """Names listed in the C{__all__} variable of this module.

        These names are considered to be exported by the module,
        both for the purpose of C{from <module> import *} and
        for the purpose of publishing names from private modules.

        If no C{__all__} variable was found in the module, or its
        contents could not be parsed, this is L{None}.
        """

        self._docformat: Optional[str] = None

    def _localNameToFullName(self, name: str) -> str:
        if name in self.contents:
            o: Documentable = self.contents[name]
            return o.fullName()
        elif name in self._localNameToFullName_map:
            return self._localNameToFullName_map[name]
        else:
            return name

    @property
    def module(self) -> 'Module':
        return self

    @property
    def docformat(self) -> Optional[str]:
        """The name of the format to be used for parsing docstrings in this module.
        
        The docformat value are inherited from packages if a C{__docformat__} variable 
        is defined in the C{__init__.py} file.

        If no C{__docformat__} variable was found or its
        contents could not be parsed, this is L{None}.
        """
        if self._docformat:
            return self._docformat
        elif isinstance(self.parent, Package):
            return self.parent.docformat
        return None
    
    @docformat.setter
    def docformat(self, value: str) -> None:
        self._docformat = value

    def submodules(self) -> Iterator['Module']:
        """Returns an iterator over the visible submodules."""
        return (m for m in self.contents.values()
                if isinstance(m, Module) and m.isVisible)

class Package(Module):
    kind = DocumentableKind.PACKAGE

# List of exceptions class names in the standard library, Python 3.8.10
_STD_LIB_EXCEPTIONS = ('ArithmeticError', 'AssertionError', 'AttributeError', 
    'BaseException', 'BlockingIOError', 'BrokenPipeError', 
    'BufferError', 'BytesWarning', 'ChildProcessError', 
    'ConnectionAbortedError', 'ConnectionError', 
    'ConnectionRefusedError', 'ConnectionResetError', 
    'DeprecationWarning', 'EOFError', 
    'EnvironmentError', 'Exception', 'FileExistsError', 
    'FileNotFoundError', 'FloatingPointError', 'FutureWarning', 
    'GeneratorExit', 'IOError', 'ImportError', 'ImportWarning', 
    'IndentationError', 'IndexError', 'InterruptedError', 
    'IsADirectoryError', 'KeyError', 'KeyboardInterrupt', 'LookupError', 
    'MemoryError', 'ModuleNotFoundError', 'NameError', 
    'NotADirectoryError', 'NotImplementedError', 
    'OSError', 'OverflowError', 'PendingDeprecationWarning', 'PermissionError', 
    'ProcessLookupError', 'RecursionError', 'ReferenceError', 
    'ResourceWarning', 'RuntimeError', 'RuntimeWarning', 'StopAsyncIteration', 
    'StopIteration', 'SyntaxError', 'SyntaxWarning', 'SystemError', 
    'SystemExit', 'TabError', 'TimeoutError', 'TypeError', 
    'UnboundLocalError', 'UnicodeDecodeError', 'UnicodeEncodeError', 
    'UnicodeError', 'UnicodeTranslateError', 'UnicodeWarning', 'UserWarning', 
    'ValueError', 'Warning', 'ZeroDivisionError')
def is_exception(cls: 'Class') -> bool:
    """
    Whether is class should be considered as 
    an exception and be marked with the special 
    kind L{DocumentableKind.EXCEPTION}.
    """
    for base in cls.mro(True, False):
        if base in _STD_LIB_EXCEPTIONS:
            return True
    return False

def compute_mro(cls:'Class') -> List[Union['Class', str]]:
    """
    Compute the method resolution order for this class.
    This function will also set the 
    C{_finalbaseobjects} and C{_finalbases} attributes on 
    this class and all it's superclasses.
    """
    def init_finalbaseobjects(o: 'Class', path:Optional[List['Class']]=None) -> None:
        if not path:
            path = []
        if o in path:
            cycle_str = " -> ".join([o.fullName() for o in path[path.index(cls):] + [cls]])
            raise ValueError(f"Cycle found while computing inheritance hierarchy: {cycle_str}")
        path.append(o)
        if o._finalbaseobjects is not None:
            return
        if o.rawbases:
            finalbaseobjects: List[Optional[Class]] = []
            finalbases: List[str] = []
            for i,((str_base, _), base) in enumerate(zip(o.rawbases, o._initialbaseobjects)):
                if base:
                    finalbaseobjects.append(base)
                    finalbases.append(base.fullName())
                else:
                    # Only re-resolve the base object if the base was None.
                    resolved_base = o.parent.resolveName(str_base)
                    if isinstance(resolved_base, Class):
                        base = resolved_base
                        finalbaseobjects.append(base)
                        finalbases.append(base.fullName())
                    else:
                        # the base object could not be resolved
                        finalbaseobjects.append(None)
                        finalbases.append(o._initialbases[i])
                if base:
                    # Recurse on super classes
                    init_finalbaseobjects(base, path.copy())
            o._finalbaseobjects = finalbaseobjects
            o._finalbases = finalbases
    
    def localbases(o:'Class') -> Iterator[Union['Class', str]]:
        """
        Like L{Class.baseobjects} but fallback to the expanded name if the base is not resolved to a L{Class} object.
        """
        for s,b in zip(o.bases, o.baseobjects):
            if isinstance(b, Class):
                yield b
            else:
                yield s

    def getbases(o:Union['Class', str]) -> List[Union['Class', str]]:
        if isinstance(o, str):
            return []
        return list(localbases(o))

    init_finalbaseobjects(cls)
    return mro.mro(cls, getbases)

class Class(CanContainImportsDocumentable):
    kind = DocumentableKind.CLASS
    parent: CanContainImportsDocumentable
    decorators: Sequence[Tuple[str, Optional[Sequence[ast.expr]]]]
    
    # set in post-processing:
    _finalbaseobjects: Optional[List[Optional['Class']]] = None 
    _finalbases: Optional[List[str]] = None
    _mro: Optional[List[Union['Class', str]]] = None

    def setup(self) -> None:
        super().setup()
        self.rawbases: Sequence[Tuple[str, ast.expr]] = []
        self.raw_decorators: Sequence[ast.expr] = []
        self.subclasses: List[Class] = []
        self._initialbases: List[str] = []
        self._initialbaseobjects: List[Optional['Class']] = []
    
    def _init_mro(self) -> None:
        """
        Compute the correct value of the method resolution order returned by L{mro()}.
        """
        try:
            self._mro = compute_mro(self)
        except ValueError as e:
            self.report(str(e), 'mro')
            self._mro = list(self.allbases(True))

    @overload
    def mro(self, include_external:'Literal[True]', include_self:bool=True) -> List[Union['Class', str]]:...
    @overload
    def mro(self, include_external:'Literal[False]'=False, include_self:bool=True) -> List['Class']:...
    def mro(self, include_external:bool=False, include_self:bool=True) -> List[Union['Class', str]]: # type:ignore[misc]
        """
        Get the method resution order of this class. 

        @note: The actual correct value is only set in post-processing, if L{mro()} is called
            in the AST visitors, it will return the same as C{list(self.allbases(include_self))}.
        """
        if self._mro is None:
            return list(self.allbases(include_self))
        
        _mro: List[Union[str, Class]]
        if include_external is False:
            _mro = [o for o in self._mro if not isinstance(o, str)]
        else:
            _mro = self._mro
        if include_self is False:
            _mro = _mro[1:]
        return _mro

    @property
    def bases(self) -> List[str]:
        """
        Fully qualified names of the bases of this class.
        """
        return self._finalbases if \
            self._finalbases is not None else self._initialbases

    
    @property
    def baseobjects(self) -> List[Optional['Class']]:
        """
        Base objects, L{None} value is inserted when the base class could not be found in the system.
        
        @note: This property is currently computed two times, a first time when we're visiting the ClassDef and initially creating the object. 
            It's computed another time in post-processing to try to resolve the names that could not be resolved the first time. This is needed when there are import cycles. 
            
            Meaning depending on the state of the system, this property can return either the initial objects or the final objects
        """
        return self._finalbaseobjects if \
            self._finalbaseobjects is not None else self._initialbaseobjects
    
    def allbases(self, include_self: bool = False) -> Iterator['Class']:
        """
        Iterate on all base objects of this class and it's super classes. Doesn't comply with MRO.
        """
        if include_self:
            yield self
        for b in self.baseobjects:
            if b is not None:
                yield from b.allbases(True)

    def find(self, name: str) -> Optional[Documentable]:
        """Look up a name in this class and its base classes.

        @return: the object with the given name, or L{None} if there isn't one
        """
        for base in self.mro():
            obj: Optional[Documentable] = base.contents.get(name)
            if obj is not None:
                return obj
        return None

    def _localNameToFullName(self, name: str) -> str:
        if name in self.contents:
            o: Documentable = self.contents[name]
            return o.fullName()
        elif name in self._localNameToFullName_map:
            return self._localNameToFullName_map[name]
        else:
            return self.parent._localNameToFullName(name)

    @property
    def constructor_params(self) -> Mapping[str, Optional[ast.expr]]:
        """A mapping of constructor parameter names to their type annotation.
        If a parameter is not annotated, its value is L{None}.
        """

        # We assume that the constructor parameters are the same as the
        # __init__() parameters. This is incorrect if __new__() or the class
        # call have different parameters.
        init = self.find('__init__')
        if isinstance(init, Function):
            return init.annotations
        else:
            return {}


class Inheritable(Documentable):
    documentation_location = DocLocation.PARENT_PAGE

    parent: CanContainImportsDocumentable

    def docsources(self) -> Iterator[Documentable]:
        yield self
        if not isinstance(self.parent, Class):
            return
        for b in self.parent.mro(include_self=False):
            if self.name in b.contents:
                yield b.contents[self.name]

    def _localNameToFullName(self, name: str) -> str:
        return self.parent._localNameToFullName(name)

class PropertyFunctionKind(Enum):
    GETTER = 1
    SETTER = 2
    DELETER = 3

@attr.s(auto_attribs=True)
class PropertyInfo:

    getter:Optional['Function'] = None
    """
    The getter.
    """
    setter: Optional['Function'] = None
    """
    None if it has not been set with C{@name.setter} decorator.
    """
    deleter: Optional['Function'] = None
    """
    None if it has not been set with C{@name.deleter} decorator.
    """

    def set(self, kind:PropertyFunctionKind, func:'Function') -> None:
        if kind is PropertyFunctionKind.GETTER:
            self.getter = func
        elif kind is PropertyFunctionKind.SETTER:
            self.setter = func
        elif kind is PropertyFunctionKind.DELETER:
            self.deleter = func
        else:
            assert False

class Function(Inheritable):
    kind = DocumentableKind.FUNCTION
    is_async: bool
    annotations: Mapping[str, Optional[ast.expr]]
    decorators: Optional[Sequence[ast.expr]]
    signature: Optional[Signature]
    overloads: List['FunctionOverload']

    def setup(self) -> None:
        super().setup()
        if isinstance(self.parent, Class):
            self.kind = DocumentableKind.METHOD
        self.signature = None
        self.overloads = []

@attr.s(auto_attribs=True)
class FunctionOverload:
    """
    @note: This is not an actual documentable type. 
    """
    primary: Function
    signature: Signature
    decorators: Sequence[ast.expr]

def init_property(attr:'Attribute') -> Iterator['Function']:
    """
    Initiates the L{Attribute} that represent the property in the tree.

    Returns the functions to remove from the tree. If the property matchup fails
    """
    info = attr._property_info
    assert info is not None

    getter = info.getter
    setter = info.setter
    deleter = info.deleter

    if getter is None:
        # The getter should never be None
        return ()

    # avoid cyclic import
    from pydoctor import epydoc2stan
    
    # Setup Attribute object for the property    
    attr.docstring = getter.docstring
    attr.annotation = getter.annotations.get('return')
    attr.decorators = getter.decorators
    
    attr.extra_info.extend(getter.extra_info)

    # Parse docstring now.
    if epydoc2stan.ensure_parsed_docstring(getter):
    
        pdoc = getter.parsed_docstring
        assert pdoc is not None

        other_fields = []
        # process fields such that :returns: clause docs takes the whole docs 
        # if no global description is written.
        for field in pdoc.fields:
            tag = field.tag()
            if tag == 'return':
                if not pdoc.has_body:
                    pdoc = field.body()
            elif tag == 'rtype':
                attr.parsed_type = field.body()
            else:
                other_fields.append(field)
        
        pdoc.fields = other_fields
        
        # Set the new attribute parsed docstring
        attr.parsed_docstring = pdoc

    # maybe TODO: Add inheritence info to getter/setter/deleters

    # Yield the objects to remove from the Documentable tree
    yield getter
    if setter:
        yield setter
    if deleter:
        yield deleter


class Attribute(Inheritable):
    kind: Optional[DocumentableKind] = DocumentableKind.ATTRIBUTE
    annotation: Optional[ast.expr]
    decorators: Optional[Sequence[ast.expr]] = None # decorators are used only if the attribute is a property
    value: Optional[ast.expr] = None
    """
    The value of the assignment expression. 

    None value means the value is not initialized 
    at the current point of the the process. 
    Or maybe it can be that the attribute is a property.
    """

    _property_info:Optional[PropertyInfo] = None
    
    @property
    def property_setter(self) -> Optional[Function]:
        """
        The property setter L{Function}, is any defined.
        Only applicable if L{kind} is L{DocumentableKind.PROPERTY}
        """
        if self._property_info:
            return self._property_info.setter
        return None

    @property
    def property_deleter(self) -> Optional[Function]:
        """Idem for the deleter."""
        if self._property_info:
            return self._property_info.deleter
        return None

# Work around the attributes of the same name within the System class.
_ModuleT = Module
_PackageT = Package

T = TypeVar('T')

def import_mod_from_file_location(module_full_name:str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_full_name, path)
    if spec is None: 
        raise RuntimeError(f"Cannot find spec for module {module_full_name} at {path}")
    py_mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert isinstance(loader, importlib.abc.Loader), loader
    loader.exec_module(py_mod)
    return py_mod


# Declare the types that we consider as functions (also when they are coming
# from a C extension)
func_types: Tuple[Type[Any], ...] = (types.BuiltinFunctionType, types.FunctionType)
if hasattr(types, "MethodDescriptorType"):
    # This is Python >= 3.7 only
    func_types += (types.MethodDescriptorType, )
else:
    func_types += (type(str.join), )
if hasattr(types, "ClassMethodDescriptorType"):
    # This is Python >= 3.7 only
    func_types += (types.ClassMethodDescriptorType, )
else:
    func_types += (type(dict.__dict__["fromkeys"]), )

_default_extensions = object()
class System:
    """A collection of related documentable objects.

    PyDoctor documents collections of objects, often the contents of a
    package.
    """

    # Not assigned here for circularity reasons:
    #defaultBuilder = astbuilder.ASTBuilder
    defaultBuilder: Type[ASTBuilder]
    systemBuilder: Type['ISystemBuilder']
    options: 'Options'
    extensions: List[str] = cast('List[str]', _default_extensions)
    """
    List of extensions.

    By default, all built-in pydoctor extensions will be loaded.
    Override this value to cherry-pick extensions. 
    """

    custom_extensions: List[str] = []
    """
    Additional list of extensions to load alongside default extensions.
    """

    show_attr_value = (DocumentableKind.CONSTANT, 
                       DocumentableKind.TYPE_VARIABLE, 
                       DocumentableKind.TYPE_ALIAS)
    """
    What kind of attributes we should display the value for?
    """

    def __init__(self, options: Optional['Options'] = None):
        self.allobjects: Dict[str, Documentable] = {}
        self.rootobjects: List[_ModuleT] = []

        self.violations = 0
        """The number of docstring problems found.
        This is used to determine whether to fail the build when using
        the --warnings-as-errors option, so it should only be increased
        for problems that the user can fix.
        """

        if options:
            self.options = options
        else:
            self.options = Options.defaults()
            self.options.verbosity = 3

        self.projectname = 'my project'

        self.parse_errors: Dict[str, Set[str]] = defaultdict(set)
        """
        Dict from the name of the thing we're rendering (C{section}) to the FullNames of objects for which the rendereable elements failed to parse.
        Typically the renderable element is the C{docstring}, but it can be the decorators, parameter default values or any other colorized AST.
        """

        self.verboselevel = 0
        self.needsnl = False
        self.once_msgs: Set[Tuple[str, str]] = set()

        # We're using the id() of the modules as key, and not the fullName becaue modules can
        # be reparented, generating KeyError.
        self.unprocessed_modules: List[_ModuleT] = []

        self.module_count = 0
        self.processing_modules: List[str] = []
        self.buildtime = datetime.datetime.now()
        self.intersphinx = SphinxInventory(logger=self.msg)

        # Since privacy handling now uses fnmatch, we cache results so we don't re-run matches all the time.
        # We use the fullName of the objets as the dict key in order to bind a full name to a privacy, not an object to a privacy.
        # this way, we are sure the objects' privacy stay true even if we reparent them manually.
        self._privacyClassCache: Dict[str, PrivacyClass] = {}
        
        # workaround cyclic import issue
        from pydoctor import extensions

        # Initialize the extension system
        self._factory = factory.Factory()
        self._astbuilder_visitors: List[Type['astutils.NodeVisitorExt']] = []
        self._post_processors: List[Callable[['System'], None]] = []
        
        if self.extensions == _default_extensions:
            self.extensions = list(extensions.get_extensions())
        assert isinstance(self.extensions, list)
        assert isinstance(self.custom_extensions, list)
        # pydoctor.astbuilder includes some required extensions, so always add it.
        self.extensions = ['pydoctor.astbuilder'] + self.extensions
        for ext in self.extensions + self.custom_extensions:
            # Load extensions
            extensions.load_extension_module(self, ext)

    @property
    def Class(self) -> Type['Class']:
        return self._factory.Class
    @property
    def Function(self) -> Type['Function']:
        return self._factory.Function
    @property
    def Module(self) -> Type['Module']:
        return self._factory.Module
    @property
    def Package(self) -> Type['Package']:
        return self._factory.Package
    @property
    def Attribute(self) -> Type['Attribute']:
        return self._factory.Attribute

    @property
    def sourcebase(self) -> Optional[str]:
        return self.options.htmlsourcebase

    @property
    def root_names(self) -> Collection[str]:
        """The top-level package/module names in this system."""
        return {obj.name for obj in self.rootobjects}

    def progress(self, section: str, i: int, n: Optional[int], msg: str) -> None:
        if n is None:
            d = str(i)
        else:
            d = f'{i}/{n}'
        if self.options.verbosity == 0 and sys.stdout.isatty():
            print('\r'+d, msg, end='')
            sys.stdout.flush()
            if d == n:
                self.needsnl = False
                print()
            else:
                self.needsnl = True

    def msg(self,
            section: str,
            msg: str,
            thresh: int = 0,
            topthresh: int = 100,
            nonl: bool = False,
            wantsnl: bool = True,
            once: bool = False
            ) -> None:
        """
        Log a message. pydoctor's logging system is bit messy.
        
        @param section: API doc generation step this message belongs to.
        @param msg: The message.
        @param thresh: The minimum verbosity level of the system for this message to actually be printed.
            Meaning passing thresh=-1 will make message still display if C{-q} is passed but not if C{-qq}. 
            Similarly, passing thresh=1 will make the message only apprear if the verbosity level is at least increased once with C{-v}.
            Using negative thresh will count this message as a violation and will fail the build if option C{-W} is passed.
        @param topthresh: The maximum verbosity level of the system for this message to actually be printed.
        """
        if once:
            if (section, msg) in self.once_msgs:
                return
            else:
                self.once_msgs.add((section, msg))

        if thresh < 0:
            # Apidoc build messages are generated using negative threshold
            # and we have separate reporting for them,
            # on top of the logging system.
            self.violations += 1

        if thresh <= self.options.verbosity <= topthresh:
            if self.needsnl and wantsnl:
                print()
            print(msg, end='')
            if nonl:
                self.needsnl = True
                sys.stdout.flush()
            else:
                self.needsnl = False
                print('')

    def objForFullName(self, fullName: str) -> Optional[Documentable]:
        return self.allobjects.get(fullName)

    def find_object(self, full_name: str) -> Optional[Documentable]:
        """Look up an object using a potentially outdated full name.

        A name can become outdated if the object is reparented:
        L{objForFullName()} will only be able to find it under its new name,
        but we might still have references to the old name.

        @param full_name: The fully qualified name of the object.
        @return: The object, or L{None} if the name is external (it does not
            match any of the roots of this system).
        @raise LookupError: If the object is not found, while its name does
            match one of the roots of this system.
        """
        obj = self.objForFullName(full_name)
        if obj is not None:
            return obj

        # The object might have been reparented, in which case there will
        # be an alias at the original location; look for it using expandName().
        name_parts = full_name.split('.', 1)
        for root_obj in self.rootobjects:
            if root_obj.name == name_parts[0]:
                obj = self.objForFullName(root_obj.expandName(name_parts[1]))
                if obj is not None:
                    return obj
                raise LookupError(full_name)

        return None

    def objectsOfType(self, cls: Union[Type['DocumentableT'], str]) -> Iterator['DocumentableT']:
        """Iterate over all instances of C{cls} present in the system. """
        if isinstance(cls, str):
            cls = utils.findClassFromDottedName(cls, 'objectsOfType', 
                base_class=cast(Type['DocumentableT'], Documentable))
        assert isinstance(cls, type)
        for o in self.allobjects.values():
            if isinstance(o, cls):
                yield o

    def privacyClass(self, ob: Documentable) -> PrivacyClass:
        ob_fullName = ob.fullName()
        cached_privacy = self._privacyClassCache.get(ob_fullName)
        if cached_privacy is not None:
            return cached_privacy
        
        # kind should not be None, this is probably a relica of a past age of pydoctor.
        # but keep it just in case.
        if ob.kind is None:
            return PrivacyClass.HIDDEN
        
        privacy = PrivacyClass.PUBLIC
        if ob.name.startswith('_') and \
               not (ob.name.startswith('__') and ob.name.endswith('__')):
            privacy = PrivacyClass.PRIVATE
        
        # Precedence order: CLI arguments order
        # Check exact matches first, then qnmatch
        _found_exact_match = False
        for priv, match in reversed(self.options.privacy):
            if ob_fullName == match:
                privacy = priv
                _found_exact_match = True
                break
        if not _found_exact_match:
            for priv, match in reversed(self.options.privacy):
                if qnmatch.qnmatch(ob_fullName, match):
                    privacy = priv
                    break

        # Store in cache
        self._privacyClassCache[ob_fullName] = privacy
        return privacy

    def addObject(self, obj: Documentable) -> None:
        """Add C{object} to the system."""

        if obj.parent:
            obj.parent.contents[obj.name] = obj
        elif isinstance(obj, _ModuleT):
            self.rootobjects.append(obj)
        else:
            raise ValueError(f'Top-level object is not a module: {obj!r}')

        first = self.allobjects.setdefault(obj.fullName(), obj)
        if obj is not first:
            self.handleDuplicate(obj)

    # if we assume:
    #
    # - that svn://divmod.org/trunk is checked out into ~/src/Divmod
    #
    # - that http://divmod.org/trac/browser/trunk is the trac URL to the
    #   above directory
    #
    # - that ~/src/Divmod/Nevow/nevow is passed to pydoctor as an argument
    #
    # we want to work out the sourceHref for nevow.flat.ten.  the answer
    # is http://divmod.org/trac/browser/trunk/Nevow/nevow/flat/ten.py.
    #
    # we can work this out by finding that Divmod is the top of the svn
    # checkout, and posixpath.join-ing the parts of the filePath that
    # follows that.
    #
    #  http://divmod.org/trac/browser/trunk
    #                          ~/src/Divmod/Nevow/nevow/flat/ten.py

    def setSourceHref(self, mod: _ModuleT, source_path: Path) -> None:
        if self.sourcebase is None:
            mod.sourceHref = None
        else:
            projBaseDir = mod.system.options.projectbasedirectory
            assert projBaseDir is not None
            relative = source_path.relative_to(projBaseDir).as_posix()
            mod.sourceHref = f'{self.sourcebase}/{relative}'

    @overload
    def analyzeModule(self,
            modpath: Path,
            modname: str,
            parentPackage: Optional[_PackageT],
            is_package: Literal[False] = False
            ) -> _ModuleT: ...

    @overload
    def analyzeModule(self,
            modpath: Path,
            modname: str,
            parentPackage: Optional[_PackageT],
            is_package: Literal[True]
            ) -> _PackageT: ...

    def analyzeModule(self,
            modpath: Path,
            modname: str,
            parentPackage: Optional[_PackageT] = None,
            is_package: bool = False
            ) -> _ModuleT:
        factory = self.Package if is_package else self.Module
        mod = factory(self, modname, parentPackage, modpath)
        self._addUnprocessedModule(mod)
        self.setSourceHref(mod, modpath)
        return mod

    def _addUnprocessedModule(self, mod: _ModuleT) -> None:
        """
        First add the new module into the unprocessed_modules list. 
        Handle eventual duplication of module names, and finally add the 
        module to the system.
        """
        assert mod.state is ProcessingState.UNPROCESSED
        first = self.allobjects.get(mod.fullName())
        if first is not None:
            # At this step of processing only modules exists
            assert isinstance(first, Module)
            self._handleDuplicateModule(first, mod)
        else:
            self.unprocessed_modules.append(mod)
            self.addObject(mod)
            self.progress(
                "analyzeModule", len(self.allobjects),
                None, "modules and packages discovered")        
            self.module_count += 1

    def _handleDuplicateModule(self, first: _ModuleT, dup: _ModuleT) -> None:
        """
        This is called when two modules have the same name. 

        Current rules are the following: 
            - C-modules wins over regular python modules
            - Packages wins over modules
            - Else, the last added module wins
        """
        dup.report(f"duplicate {str(first)}", thresh=1)

        if first._is_c_module and not isinstance(dup, Package):
            # C-modules wins
            return
        elif isinstance(first, Package) and not isinstance(dup, Package):
            # Packages wins
            return
        else:
            # Else, the last added module wins
            self._remove(first)
            self.unprocessed_modules.remove(first)
            self._addUnprocessedModule(dup)

    def _introspectThing(self, thing: object, parent: Documentable, parentMod: _ModuleT) -> None:
        for k, v in thing.__dict__.items():
            if (isinstance(v, func_types)
                    # In PyPy 7.3.1, functions from extensions are not
                    # instances of the abstract types in func_types
                    or (hasattr(v, "__class__") and v.__class__.__name__ == 'builtin_function_or_method')):
                f = self.Function(self, k, parent)
                f.parentMod = parentMod
                f.docstring = v.__doc__
                f.decorators = None
                try:
                    f.signature = signature(v)
                except ValueError:
                    # function has an invalid signature.
                    parent.report(f"Cannot parse signature of {parent.fullName()}.{k}")
                    f.signature = None
                except TypeError:
                    # in pypy we get a TypeError calling signature() on classmethods, 
                    # because apparently, they are not callable :/
                    f.signature = None
                        
                f.is_async = False
                f.annotations = {name: None for name in f.signature.parameters} if f.signature else {}
                self.addObject(f)
            elif isinstance(v, type):
                c = self.Class(self, k, parent)
                c.rawbases = []
                c.parentMod = parentMod
                c.docstring = v.__doc__
                self.addObject(c)
                self._introspectThing(v, c, parentMod)

    def introspectModule(self,
            path: Path,
            module_name: str,
            package: Optional[_PackageT]
            ) -> _ModuleT:

        if package is None:
            module_full_name = module_name
        else:
            module_full_name = f'{package.fullName()}.{module_name}'

        py_mod = import_mod_from_file_location(module_full_name, path)
        is_package = py_mod.__package__ == py_mod.__name__

        factory = self.Package if is_package else self.Module
        module = factory(self, module_name, package, path)
        
        module.docstring = py_mod.__doc__
        module._is_c_module = True
        module._py_mod = py_mod
        
        self._addUnprocessedModule(module)
        return module

    def addPackage(self, package_path: Path, parentPackage: Optional[_PackageT] = None) -> None:
        package = self.analyzeModule(
            package_path / '__init__.py', package_path.name, parentPackage, is_package=True)

        for path in sorted(package_path.iterdir()):
            if path.is_dir():
                if (path / '__init__.py').exists():
                    self.addPackage(path, package)
            elif path.name != '__init__.py' and not path.name.startswith('.'):
                self.addModuleFromPath(path, package)

    def addModuleFromPath(self, path: Path, package: Optional[_PackageT]) -> None:
        name = path.name
        for suffix in importlib.machinery.all_suffixes():
            if not name.endswith(suffix):
                continue
            module_name = name[:-len(suffix)]
            if suffix in importlib.machinery.EXTENSION_SUFFIXES:
                if self.options.introspect_c_modules:
                    self.introspectModule(path, module_name, package)
            elif suffix in importlib.machinery.SOURCE_SUFFIXES:
                self.analyzeModule(path, module_name, package)
            break
    
    def _remove(self, o: Documentable) -> None:
        del self.allobjects[o.fullName()]
        oc = list(o.contents.values())
        for c in oc:
            self._remove(c)

    def handleDuplicate(self, obj: Documentable) -> None:
        """
        This is called when we see two objects with the same
        .fullName(), for example::

            class C:
                if something:
                    def meth(self):
                        implementation 1
                if somethinglelse:
                    def meth(self):
                        implementation 2

        The default rule is that the last definition "wins".
        """
        i = 0
        fullName = obj.fullName()
        while (fullName + ' ' + str(i)) in self.allobjects:
            i += 1
        prev = self.allobjects[fullName]
        obj.report(f"duplicate {str(prev)}", thresh=1)
        self._remove(prev)
        prev.name = obj.name + ' ' + str(i)
        def readd(o: Documentable) -> None:
            self.allobjects[o.fullName()] = o
            for c in o.contents.values():
                readd(c)
        readd(prev)
        self.allobjects[fullName] = obj


    def getProcessedModule(self, modname: str) -> Optional[_ModuleT]:
        mod = self.allobjects.get(modname)
        if mod is None:
            return None
        if not isinstance(mod, Module):
            return None

        if mod.state is ProcessingState.UNPROCESSED:
            self.processModule(mod)

        assert mod.state in (ProcessingState.PROCESSING, ProcessingState.PROCESSED), mod.state
        return mod

    def processModule(self, mod: _ModuleT) -> None:
        assert mod.state is ProcessingState.UNPROCESSED
        assert mod in self.unprocessed_modules
        mod.state = ProcessingState.PROCESSING
        self.unprocessed_modules.remove(mod)
        if mod.source_path is None:
            assert mod._py_string is not None
        if mod._is_c_module:
            self.processing_modules.append(mod.fullName())
            self.msg("processModule", "processing %s"%(self.processing_modules), 1)
            self._introspectThing(mod._py_mod, mod, mod)
            mod.state = ProcessingState.PROCESSED
            head = self.processing_modules.pop()
            assert head == mod.fullName()
        else:
            builder = self.defaultBuilder(self)
            if mod._py_string is not None:
                ast = builder.parseString(mod._py_string, mod)
            else:
                assert mod.source_path is not None
                ast = builder.parseFile(mod.source_path, mod)
            if ast:
                self.processing_modules.append(mod.fullName())
                if mod._py_string is None:
                    self.msg("processModule", "processing %s"%(self.processing_modules), 1)
                builder.processModuleAST(ast, mod)
                mod.state = ProcessingState.PROCESSED
                head = self.processing_modules.pop()
                assert head == mod.fullName()
        self.progress(
            'process',
            self.module_count - len(self.unprocessed_modules),
            self.module_count,
            f"modules processed, {self.violations} warnings")


    def process(self) -> None:
        while self.unprocessed_modules:
            mod = next(iter(self.unprocessed_modules))
            self.processModule(mod)
        self.postProcess()


    def postProcess(self) -> None:
        """Called when there are no more unprocessed modules.

        Analysis of relations between documentables can be done here,
        without the risk of drawing incorrect conclusions because modules
        were not fully processed yet.
        """

        # default post-processing includes:
        # - Processing of subclasses
        # - MRO computing.
        # - Checking whether the class is an exception
        for cls in self.objectsOfType(Class):
            
            cls._init_mro()
            
            for b in cls.baseobjects:
                if b is not None:
                    b.subclasses.append(cls)
            
            if is_exception(cls):
                cls.kind = DocumentableKind.EXCEPTION
        
        # Machup property functions into an Attribute that already exist.
        # We are transforming the tree at the end only.
        to_delete: List[Documentable] = []
        for attr in self.objectsOfType(Attribute):
            if attr._property_info is not None:
                to_delete.extend(init_property(attr))
        for obj in set(to_delete):
            self._remove(obj)
            assert obj.parent is not None
            if obj.name in obj.parent.contents:
                del obj.parent.contents[obj.name]


        for post_processor in self._post_processors:
            post_processor(self)


    def fetchIntersphinxInventories(self, cache: CacheT) -> None:
        """
        Download and parse intersphinx inventories based on configuration.
        """
        for url in self.options.intersphinx:
            self.intersphinx.update(cache, url)

class SystemBuildingError(Exception):
    """
    Raised when there is a (handled) fatal error while adding modules to the builder.
    """

class ISystemBuilder(abc.ABC):
    """
    Interface class for building a system.
    """
    @abc.abstractmethod
    def __init__(self, system: 'System') -> None:
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

class SystemBuilder(ISystemBuilder):
    """
    This class is only an adapter for some System methods related to module building. 
    """
    def __init__(self, system: 'System') -> None:
        self.system = system
        self._added: Set[Path] = set()

    def addModule(self, path: Path, parent_name: Optional[str] = None, ) -> None:
        if path in self._added:
            return
        # Path validity check
        if self.system.options.projectbasedirectory is not None:
            # Note: Path.is_relative_to() was only added in Python 3.9,
            #       so we have to use this workaround for now.
            try:
                path.relative_to(self.system.options.projectbasedirectory)
            except ValueError as ex:
                raise SystemBuildingError(f"Source path lies outside base directory: {ex}")
        parent: Optional[Package] = None
        if parent_name:
            _p = self.system.allobjects[parent_name]
            assert isinstance(_p, Package)
            parent = _p
        if path.is_dir():
            self.system.msg('addPackage', f"adding directory {path}")
            if not (path / '__init__.py').is_file():
                raise SystemBuildingError(f"Source directory lacks __init__.py: {path}")
            self.system.addPackage(path, parent)
        elif path.is_file():
            self.system.msg('addModuleFromPath', f"adding module {path}")
            self.system.addModuleFromPath(path, parent)
        elif path.exists():
            raise SystemBuildingError(f"Source path is neither file nor directory: {path}")
        else:
            raise SystemBuildingError(f"Source path does not exist: {path}")
        self._added.add(path)

    def addModuleString(self, text: str, modname: str,
                        parent_name: Optional[str] = None,
                        is_package: bool = False, ) -> None:
        if parent_name is None:
            parent = None
        else:
            # Set containing package as parent.
            parent = self.system.allobjects[parent_name]
            assert isinstance(parent, Package), f"{parent.fullName()} is not a Package, it's a {parent.kind}"
        
        factory = self.system.Package if is_package else self.system.Module
        mod = factory(self.system, name=modname, parent=parent, source_path=None)
        mod._py_string = textwrap.dedent(text)
        self.system._addUnprocessedModule(mod)

    def buildModules(self) -> None:
        self.system.process()

System.systemBuilder = SystemBuilder

def prepend_package(builderT:Type[ISystemBuilder], package:str) -> Type[ISystemBuilder]:
    """
    Get a new system builder class, that extends the original C{builder} such that it will always use a "fake" 
    C{package} to be the only root object of the system and add new modules under it.
    """
    
    class PrependPackageBuidler(builderT): # type:ignore
        """
        Support for option C{--prepend-package}.
        """

        def __init__(self, system: 'System', *, package:str) -> None:
            super().__init__(system)
            
            self.package = package
            
            prependedpackage = None
            for m in package.split('.'):
                prependedpackage = system.Package(
                    system, m, prependedpackage)
                system.addObject(prependedpackage)
        
        def addModule(self, path: Path, parent_name: Optional[str] = None, ) -> None:
            if parent_name is None:
                parent_name = self.package
            super().addModule(path, parent_name)
        
        def addModuleString(self, text: str, modname: str,
                            parent_name: Optional[str] = None,
                            is_package: bool = False, ) -> None:
            if parent_name is None:
                parent_name = self.package
            super().addModuleString(text, modname, parent_name, is_package=is_package)
    
    return utils.partialclass(PrependPackageBuidler, package=package)
