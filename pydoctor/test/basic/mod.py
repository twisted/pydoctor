class C:
    """Class docstring."""
    def f(self):
        """Method docstring."""
    @classmethod
    def cls_method(cls):
        pass
    @staticmethod
    def static_method():
        pass


class D(C):
    """Subclass docstring."""
    def f(self):
        # no docstring, should be inherited from superclass
        pass
    def g(self):
        pass
    @classmethod
    def cls_method2(cls):
        pass
    @staticmethod
    def static_method2():
        pass
