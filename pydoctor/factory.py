"""
Create customizable model classes. 
"""

from typing import Dict, List, Tuple, Type, Any, Union, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from pydoctor import model

class GenericFactory:

    def __init__(self, bases: Dict[str, Type[Any]]) -> None:
        self.bases = bases
        self.mixins: Dict[str, List[Type[Any]]] = {}
        self._class_cache: Dict[Tuple[str, Tuple[Type[Any], ...]], Type[Any]] = {}

    def add_mixin(self, for_class: str, mixin:Type[Any]) -> None:
        """
        Add a mixin class to the specied object in the factory. 
        """
        if for_class not in list(self.bases):
            raise ValueError("Invalid class name")
        
        try:
            mixins = self.mixins[for_class]
        except KeyError:
            mixins = []
            self.mixins[for_class] = mixins
        
        assert isinstance(mixins, list)
        mixins.append(mixin)

    def add_mixins(self, **kwargs:Union[Sequence[Type[Any]], Type[Any]]) -> None:
        """
        Add mixin classes to objects in the factory. 
        Example::
            class MyClassMixin: ...
            class MyDataMixin: ...
            factory = factory.Factory()
            factory.add_mixins(Class=MyClassMixin, Attribute=MyDataMixin)
        :param kwargs: Minin(s) classes to apply to names.
        """
        for key,value in kwargs.items():
            if isinstance(value, Sequence):
                for item in value:
                    self.add_mixin(key, item)
            else:
                self.add_mixin(key, value)

    def get_class(self, name:str) -> Type[Any]:
        try:
            class_id = name, tuple(self.mixins.get(name, [])+[self.bases[name]])
        except KeyError as e:
            raise ValueError(f"Invalid class name: '{name}'") from e
        else:
            cached = self._class_cache.get(class_id)
            if cached is not None:
                cls = cached
            else:
                cls = type(*class_id, {})
                self._class_cache[class_id] = cls
            return cls

class Factory(GenericFactory):
    """
    Classes are created dynamically with `type` such that they can inherith from customizable mixin classes. 
    """

    def __init__(self) -> None:
        # Workaround cyclic import issue.
        from pydoctor import model
        self.model = model
        _bases = {
            'Class': model.Class,
            'Function': model.Function,
            'Module': model.Module,
            'Package': model.Package,
            'Attribute': model.Attribute,
        }
        super().__init__(bases=_bases)

    @property
    def Class(self) -> Type['model.Class']:
        klass = self.get_class('Class')
        assert issubclass(klass, self.model.Class)
        return klass

    @property
    def Function(self) -> Type['model.Function']:
        func = self.get_class('Function')
        assert issubclass(func, self.model.Function)
        return func

    @property
    def Module(self) -> Type['model.Module']:
        mod = self.get_class('Module')
        assert issubclass(mod, self.model.Module)
        return mod
    
    @property
    def Package(self) -> Type['model.Package']:
        mod = self.get_class('Package')
        assert issubclass(mod, self.model.Package)
        return mod

    @property
    def Attribute(self) -> Type['model.Attribute']:
        data = self.get_class('Attribute')
        assert issubclass(data, self.model.Attribute)
        return data
