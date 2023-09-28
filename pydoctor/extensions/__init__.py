"""
Pydoctor's extension system.

An extension can be composed by mixin classes, AST builder visitor extensions and post processors.
"""
import importlib
import sys
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple, Type, Union, TYPE_CHECKING, cast

# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

if TYPE_CHECKING:
    from pydoctor import astbuilder, model

import attr
from pydoctor import astutils

class ClassMixin:
    """Base class for mixins applied to L{model.Class} objects."""
class ModuleMixin:
    """Base class for mixins applied to L{model.Module} objects."""
class PackageMixin:
    """Base class for mixins applied to L{model.Package} objects."""
class FunctionMixin:
    """Base class for mixins applied to L{model.Function} objects."""
class AttributeMixin:
    """Base class for mixins applied to L{model.Attribute} objects."""
class DocumentableMixin(ModuleMixin, ClassMixin, FunctionMixin, AttributeMixin):
    """Base class for mixins applied to all L{model.Documentable} objects."""
class CanContainImportsDocumentableMixin(PackageMixin, ModuleMixin, ClassMixin):
    """Base class for mixins applied to L{model.Class}, L{model.Module} and L{model.Package} objects."""
class InheritableMixin(FunctionMixin, AttributeMixin):
    """Base class for mixins applied to L{model.Function} and L{model.Attribute} objects."""

MixinT = Union[ClassMixin, ModuleMixin, PackageMixin, FunctionMixin, AttributeMixin]

def _importlib_resources_contents(package: str) -> Iterable[str]:
    """Return an iterable of entries in C{package}.

    Note that not all entries are resources.  Specifically, directories are
    not considered resources. 
    """
    return [path.name for path in importlib_resources.files(package).iterdir()]


def _importlib_resources_is_resource(package: str, name: str) -> bool:
    """True if C{name} is a resource inside C{package}.

    Directories are B{not} resources.
    """
    resource = name
    return any(
        traversable.name == resource and traversable.is_file()
        for traversable in importlib_resources.files(package).iterdir()
    )

def _get_submodules(pkg: str) -> Iterator[str]:
    for name in _importlib_resources_contents(pkg):
        if (not name.startswith('_') and _importlib_resources_is_resource(pkg, name)) and name.endswith('.py'):
            name = name[:-len('.py')]
            yield f"{pkg}.{name}"

def _get_setup_extension_func_from_module(module: str) -> Callable[['ExtRegistrar'], None]:
    """
    Will look for the special function C{setup_pydoctor_extension} in the provided module.
    
    @Raises AssertionError: if module do not provide a valid setup_pydoctor_extension() function.
    @Raises ModuleNotFoundError: if module is not found.
    @Returns: a tuple(str, callable): extension module name, setup_pydoctor_extension() function.
    """
    mod = importlib.import_module(module)
    
    assert hasattr(mod, 'setup_pydoctor_extension'), f"{mod}.setup_pydoctor_extension() function not found."
    assert callable(mod.setup_pydoctor_extension), f"{mod}.setup_pydoctor_extension should be a callable."
    return cast('Callable[[ExtRegistrar], None]', mod.setup_pydoctor_extension)

_mixin_to_class_name: Dict[Any, str] = {
        ClassMixin: 'Class',
        ModuleMixin: 'Module',
        PackageMixin: 'Package',
        FunctionMixin: 'Function',
        AttributeMixin: 'Attribute',
    }

def _get_mixins(*mixins: Type[MixinT]) -> Dict[str, List[Type[MixinT]]]:
    """
    Transform a list of mixins classes to a dict from the 
    concrete class name to the mixins that must be applied to it.
    This relies on the fact that mixins shoud extend one of the 
    base mixin classes in L{pydoctor.extensions} module.
    
    @raises AssertionError: If a mixin does not extends any of the 
        provided base mixin classes.
    """
    mixins_by_name: Dict[str, List[Type[MixinT]]] = {}
    for mixin in mixins:
        added = False
        for k,v in _mixin_to_class_name.items():
            if isinstance(mixin, type) and issubclass(mixin, k):
                mixins_by_name.setdefault(v, [])
                mixins_by_name[v].append(mixin)
                added = True
                # do not break, such that one class can be added to several class
                # bases if it extends the right types.
        if not added:
            assert False, f"Invalid mixin {mixin.__name__!r}. Mixins must subclass one of the base class."
    return mixins_by_name

# Largely inspired by docutils Transformer class.
DEFAULT_PRIORITY = 100
class PriorityProcessor:
    """
    Stores L{Callable} and applies them to the system based on priority or insertion order.
    The default priority is C{100}, see code source of L{astbuilder.setup_pydoctor_extension}, 
    and others C{setup_pydoctor_extension} functions.

    Highest priority callables will be called first, when priority is the same it's FIFO order.

    One L{PriorityProcessor} should only be run once on the system.
    """
    
    def __init__(self, system:'model.System'):
        self.system = system
        self.applied: List[Callable[['model.System'], None]] = []
        self._post_processors: List[Tuple[object, Callable[['model.System'], None]]] = []
        self._counter = 256
        """Internal counter to keep track of the add order of callables."""
    
    def add_post_processor(self, post_processor:Callable[['model.System'], None], 
                           priority:Optional[int]) -> None:
        if priority is None:
            priority = DEFAULT_PRIORITY
        priority_key = self._get_priority_key(priority)
        self._post_processors.append((priority_key, post_processor))
    
    def _get_priority_key(self, priority:int) -> object:
        """
        Return a tuple, `priority` combined with `self._counter`.

        This ensures FIFO order on callables with identical priority.
        """
        self._counter -= 1
        return (priority, self._counter)
    
    def apply_processors(self) -> None:
        """Apply all of the stored processors, in priority order."""
        if self.applied:
            # this is typically only reached in tests, when we 
            # call fromText() several times with the same 
            # system or when we manually call System.postProcess()
            self.system.msg('post processing', 
                            'warning: multiple post-processing pass detected', 
                            thresh=-1)
            self.applied.clear()
        
        self._post_processors.sort()
        for p in reversed(self._post_processors):
            _, post_processor = p
            post_processor(self.system)
            self.applied.append(post_processor)

@attr.s(auto_attribs=True)
class ExtRegistrar:
    """
    The extension registrar class provides utilites to register an extension's components.
    """
    system: 'model.System'

    def register_mixin(self, *mixin: Type[MixinT]) -> None:
        """
        Register mixin for model objects. Mixins shoud extend one of the 
        base mixin classes in L{pydoctor.extensions} module, i.e. L{ClassMixin} or L{DocumentableMixin}, etc.
        """
        self.system._factory.add_mixins(**_get_mixins(*mixin))

    def register_astbuilder_visitor(self, 
            *visitor: Type[astutils.NodeVisitorExt]) -> None:
        """
        Register AST visitor(s). Typically visitor extensions inherits from L{ModuleVisitorExt}.
        """
        self.system._astbuilder_visitors.extend(visitor)
    
    def register_post_processor(self, 
            *post_processor: Callable[['model.System'], None], 
            priority:Optional[int]=None) -> None:
        """
        Register post processor(s).
         
        A post-processor is simply a one-argument callable receiving 
        the processed L{model.System} and doing stuff on the L{model.Documentable} tree.

        @param priority: See L{PriorityProcessor}.
        """
        for p in post_processor:
            self.system._post_processor.add_post_processor(p, priority)

def load_extension_module(system:'model.System', mod: str) -> None:
    """
    Load the pydoctor extension module into the system.
    """
    setup_pydoctor_extension = _get_setup_extension_func_from_module(mod)
    setup_pydoctor_extension(ExtRegistrar(system))

def get_extensions() -> Iterator[str]:
    """
    Get the full names of all the pydoctor extension modules.
    """
    return _get_submodules('pydoctor.extensions')

class ModuleVisitorExt(astutils.NodeVisitorExt):
    """
    Base class to extend the L{astbuilder.ModuleVistor}.
    """
    when = astutils.NodeVisitorExt.When.AFTER
    visitor: 'astbuilder.ModuleVistor'
