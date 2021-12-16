from .base_class import BaseClass


class DerivedClass(BaseClass):
    """Derived class whose base class is in a C extension."""

    def another_func(self):
        """Function whose docstring refers to L{func()} from the base class."""
        pass

