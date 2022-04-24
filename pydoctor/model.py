"""Core pydoctor objects.

The two core objects are L{Documentable} and L{System}.  Instances of
(subclasses of) L{Documentable} represent the documentable 'things' in the
system being documented.  An instance of L{System} represents the whole system
being documented -- a System is a bad of Documentables, in some sense.
"""

import ast
import datetime
import importlib
import inspect
import platform
import sys
import types
from enum import Enum
from inspect import signature, Signature
from pathlib import Path
from typing import (
    TYPE_CHECKING, Any, Collection, Dict, Iterator, List, Mapping,
    Optional, Sequence, Set, Tuple, Type, TypeVar, overload
)
from collections import OrderedDict
from urllib.parse import quote

from pydoctor.options import Options
from pydoctor import qnmatch
from pydoctor.epydoc.markup import ParsedDocstring
from pydoctor.sphinx import CacheT, SphinxInventory

if TYPE_CHECKING:
    from typing_extensions import Literal
    from twisted.web.template import Flattenable
    from pydoctor.astbuilder import ASTBuilder
    from pydoctor import epydoc2stan
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
        self._deprecated_info: Optional["Flattenable"] = None
        self.setup()

    @property
    def doctarget(self) -> 'Documentable':
        return self

    def setup(self) -> None:
        self.contents: Dict[str, Documentable] = {}
        self._linker: Optional['epydoc2stan.DocstringLinker'] = None

    def setDocstring(self, node: ast.Str) -> None:
        doc = node.s
        lineno = node.lineno
        if _string_lineno_is_end:
            # In older CPython versions, the AST only tells us the end line
            # number and we must approximate the start line number.
            # This approximation is correct if the docstring does not contain
            # explicit newlines ('\n') or joined lines ('\' at end of line).
            lineno -= doc.count('\n')

        # Leading blank lines are stripped by cleandoc(), so we must
        # return the line number of the first non-blank line.
        for ch in doc:
            if ch == '\n':
                lineno += 1
            elif not ch.isspace():
                break

        self.docstring = inspect.cleandoc(doc)
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

    def report(self, descr: str, section: str = 'parsing', lineno_offset: int = 0) -> None:
        """Log an error or warning about this documentable object."""

        linenumber: object
        if section in ('docstring', 'resolve_identifier_xref'):
            linenumber = self.docstring_lineno
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
            thresh=-1)

    @property
    def docstringlinker(self) -> 'epydoc2stan.DocstringLinker':
        """
        Returns an instance of L{epydoc2stan.DocstringLinker} suitable for resolving names
        in the context of the object scope. 
        """
        if self._linker is not None:
            return self._linker
        # FIXME: avoid cyclic import https://github.com/twisted/pydoctor/issues/507
        from pydoctor.epydoc2stan import _CachedEpydocLinker
        self._linker = _CachedEpydocLinker(self)
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


class Class(CanContainImportsDocumentable):
    kind = DocumentableKind.CLASS
    parent: CanContainImportsDocumentable
    bases: List[str]
    baseobjects: List[Optional['Class']]
    decorators: Sequence[Tuple[str, Optional[Sequence[ast.expr]]]]
    # Note: While unused in pydoctor itself, raw_decorators is still in use
    #       by Twisted's custom System class, to find deprecations.
    raw_decorators: Sequence[ast.expr]

    auto_attribs: bool = False
    """L{True} iff this class uses the C{auto_attribs} feature of the C{attrs}
    library to automatically convert annotated fields into attributes.
    """

    def setup(self) -> None:
        super().setup()
        self.rawbases: List[str] = []
        self.subclasses: List[Class] = []

    def allbases(self, include_self: bool = False) -> Iterator['Class']:
        if include_self:
            yield self
        for b in self.baseobjects:
            if b is not None:
                yield from b.allbases(True)

    def find(self, name: str) -> Optional[Documentable]:
        """Look up a name in this class and its base classes.

        @return: the object with the given name, or L{None} if there isn't one
        """
        for base in self.allbases(include_self=True):
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
        for b in self.parent.allbases(include_self=False):
            if self.name in b.contents:
                yield b.contents[self.name]

    def _localNameToFullName(self, name: str) -> str:
        return self.parent._localNameToFullName(name)

class Function(Inheritable):
    kind = DocumentableKind.FUNCTION
    is_async: bool
    annotations: Mapping[str, Optional[ast.expr]]
    decorators: Optional[Sequence[ast.expr]]
    signature: Optional[Signature]

    def setup(self) -> None:
        super().setup()
        if isinstance(self.parent, Class):
            self.kind = DocumentableKind.METHOD

class Attribute(Inheritable):
    kind: Optional[DocumentableKind] = DocumentableKind.ATTRIBUTE
    annotation: Optional[ast.expr]
    decorators: Optional[Sequence[ast.expr]] = None
    value: Optional[ast.expr] = None
    """
    The value of the assignment expression. 

    None value means the value is not initialized at the current point of the the process. 
    """

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


class System:
    """A collection of related documentable objects.

    PyDoctor documents collections of objects, often the contents of a
    package.
    """

    Class = Class
    Module = Module
    Package = Package
    Function = Function
    Attribute = Attribute
    # Not assigned here for circularity reasons:
    #defaultBuilder = astbuilder.ASTBuilder
    defaultBuilder: Type[ASTBuilder]
    options: 'Options'


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

        self.docstring_syntax_errors: Set[str] = set()
        """FullNames of objects for which the docstring failed to parse."""

        self.verboselevel = 0
        self.needsnl = False
        self.once_msgs: Set[Tuple[str, str]] = set()

        # We're using the id() of the modules as key, and not the fullName becaue modules can
        # be reparented, generating KeyError.
        self.unprocessed_modules: Dict[int, _ModuleT] = OrderedDict()

        self.module_count = 0
        self.processing_modules: List[str] = []
        self.buildtime = datetime.datetime.now()
        self.intersphinx = SphinxInventory(logger=self.msg)

        # Since privacy handling now uses fnmatch, we cache results so we don't re-run matches all the time.
        # We use the fullName of the objets as the dict key in order to bind a full name to a privacy, not an object to a privacy.
        # this way, we are sure the objects' privacy stay true even if we reparent them manually.
        self._privacyClassCache: Dict[str, PrivacyClass] = {}


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


    def _warning(self,
            current: Optional[Documentable],
            message: str,
            detail: str
            ) -> None:
        if current is not None:
            fn = current.fullName()
        else:
            fn = '<None>'
        if self.options.verbosity > 0:
            print(fn, message, detail)

    def objectsOfType(self, cls: Type[T]) -> Iterator[T]:
        """Iterate over all instances of C{cls} present in the system. """
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
        First add the new module into the unprocessed_modules mapping. 
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
            self.unprocessed_modules[id(mod)] = mod
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
        self._warning(dup.parent, "duplicate", str(first))

        if first._is_c_module and not isinstance(dup, Package):
            # C-modules wins
            return
        elif isinstance(first, Package) and not isinstance(dup, Package):
            # Packages wins
            return
        else:
            # Else, the last added module wins
            del self.unprocessed_modules[id(dup)]
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
                c.bases = []
                c.baseobjects = []
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

    def handleDuplicate(self, obj: Documentable) -> None:
        '''This is called when we see two objects with the same
        .fullName(), for example::

            class C:
                if something:
                    def meth(self):
                        implementation 1
                else:
                    def meth(self):
                        implementation 2

        The default is that the second definition "wins".
        '''
        i = 0
        fullName = obj.fullName()
        while (fullName + ' ' + str(i)) in self.allobjects:
            i += 1
        prev = self.allobjects[fullName]
        self._warning(obj.parent, "duplicate", str(prev))
        def remove(o: Documentable) -> None:
            del self.allobjects[o.fullName()]
            oc = list(o.contents.values())
            for c in oc:
                remove(c)
        remove(prev)
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

        assert mod.state in (ProcessingState.PROCESSING, ProcessingState.PROCESSED)
        return mod

    def processModule(self, mod: _ModuleT) -> None:
        assert mod.state is ProcessingState.UNPROCESSED
        mod.state = ProcessingState.PROCESSING
        if mod.source_path is None:
            return
        if mod._is_c_module:
            self.processing_modules.append(mod.fullName())
            self.msg("processModule", "processing %s"%(self.processing_modules), 1)
            self._introspectThing(mod._py_mod, mod, mod)
            mod.state = ProcessingState.PROCESSED
            head = self.processing_modules.pop()
            assert head == mod.fullName()
        else:
            builder = self.defaultBuilder(self)
            ast = builder.parseFile(mod.source_path)
            if ast:
                self.processing_modules.append(mod.fullName())
                self.msg("processModule", "processing %s"%(self.processing_modules), 1)
                builder.processModuleAST(ast, mod)
                mod.state = ProcessingState.PROCESSED
                head = self.processing_modules.pop()
                assert head == mod.fullName()
        del self.unprocessed_modules[id(mod)]
        self.progress(
            'process',
            self.module_count - len(self.unprocessed_modules),
            self.module_count,
            f"modules processed, {self.violations} warnings")


    def process(self) -> None:
        while self.unprocessed_modules:
            mod = next(iter(self.unprocessed_modules.values()))
            self.processModule(mod)
        self.postProcess()


    def postProcess(self) -> None:
        """Called when there are no more unprocessed modules.

        Analysis of relations between documentables can be done here,
        without the risk of drawing incorrect conclusions because modules
        were not fully processed yet.
        """
        pass


    def fetchIntersphinxInventories(self, cache: CacheT) -> None:
        """
        Download and parse intersphinx inventories based on configuration.
        """
        for url in self.options.intersphinx:
            self.intersphinx.update(cache, url)
