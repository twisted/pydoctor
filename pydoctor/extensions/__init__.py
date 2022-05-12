"""
Pydoctor's extension system.

An extension can be composed by mixin classes, AST builder visitor extensions and post processors.
"""
import importlib
import sys
from typing import Any, Callable, Dict, Iterable, Iterator, Type, Union, cast

# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

import attr
from pydoctor import model, astutils

class ClassMixin:
    """Base class for mixins applied to `model.Class` objects."""
class ModuleMixin:
    """Base class for mixins applied to `model.Module` objects."""
class PackageMixin:
    """Base class for mixins applied to `model.Package` objects."""
class FunctionMixin:
    """Base class for mixins applied to `model.Function` objects."""
class AttributeMixin:
    """Base class for mixins applied to `model.Attribute` objects."""
class DocumentableMixin(ModuleMixin, ClassMixin, FunctionMixin, AttributeMixin):
    """Base class for mixins applied to all `model.Documentable` objects."""
class CanContainImportsDocumentableMixin(PackageMixin, ModuleMixin, ClassMixin):
    """Base class for mixins applied to `model.Class`, `model.Module` and `model.Package` objects."""
class InheritableMixin(FunctionMixin, AttributeMixin):
    """Base class for mixins applied to `model.Function` and `model.Attribute` objects."""

def _importlib_resources_contents(package: str) -> Iterable[str]:
    """Return an iterable of entries in `package`.

    Note that not all entries are resources.  Specifically, directories are
    not considered resources.  Use `is_resource()` on each entry returned here
    to check if it is a resource or not.
    """
    return [path.name for path in importlib_resources.files(package).iterdir()]


def _importlib_resources_is_resource(package: str, name: str) -> bool:
    """True if `name` is a resource inside `package`.

    Directories are *not* resources.
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
    Will look for the special function ``setup_pydoctor_extension`` in the provided module.
    
    Raises AssertionError if module do not provide a valid setup_pydoctor_extension() function.
    Raises ModuleNotFoundError if module is not found.
    Returns a tuple(str, callable): extension module name, setup_pydoctor_extension() function.
    """
    mod = importlib.import_module(module)
    
    assert hasattr(mod, 'setup_pydoctor_extension'), f"{mod}.setup_pydoctor_extension() function not found."
    assert callable(mod.setup_pydoctor_extension), f"{mod}.setup_pydoctor_extension should be a callable."
    return cast('Callable[[ExtRegistrar], None]', mod.setup_pydoctor_extension)

_mixin_to_class_name: Dict[Any, str] = {
        ClassMixin: 'Class',
        ModuleMixin: 'Module',
        FunctionMixin: 'Function',
        AttributeMixin: 'Attribute',
    }

def _get_mixins(*mixins: Type[Any]) -> Dict[str, Type[Any]]:
    """
    Transform a list of mixins classes to a dict from the 
    concrete class name to the mixins that must be applied to it.
    This relies on the fact that mixins shoud extend one of the 
    base mixin classes in `pydoctor.extensions` module.
    
    :raises AssertionError: If a mixin does not extends any of the 
        provided base mixin classes.
    """
    mixins_by_name = {}
    for mixin in mixins:
        added = False
        for k,v in _mixin_to_class_name.items():
            if isinstance(mixin, type) and issubclass(mixin, k):
                mixins_by_name[v] = mixin
                added = True
                # do not break, such that one class can be added to several class
                # bases if it extends the right types.
        if not added:
            assert False, f"Invalid mixin {mixin.__name__!r}. Mixins must subclass one of the base class."
    return mixins_by_name

@attr.s(auto_attribs=True)
class ExtRegistrar:
    """
    The extension registrar class provides utilites to register an extenion's components.
    """
    system: model.System

    def register_mixins(self, *mixins: Type[Any]) -> None:
        """
        Register mixin classes for model objects. Mixins shoud extend one of the 
        base mixin classes in `pydoctor.extensions` module, i.e. `ClassMixin` or `ApiObjectMixin`, etc.
        """
        self.system.factory.add_mixins(**_get_mixins(*mixins))

    def register_astbuilder_visitors(self, 
            *visitors: Type[astutils.NodeVisitorExt]) -> None:
        """
        Register AST visitor extensions.
        """
        self.system.astbuilder_visitors.add(*visitors)
    
    def register_post_processor(self, 
            *post_processor: Callable[[model.System], None]) -> None:
        """
        Register post processors.
        """
        self.system.post_processors.add(*post_processor)

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
