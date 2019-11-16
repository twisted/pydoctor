"""
Module docstring.

@var CONSTANT: A shiny constant.
"""

class C:
    """Class docstring.

    This docstring has lines, paragraphs and everything!

    Please see L{CONSTANT}.

    @ivar notreally: even a field!
    @since: 2.1
    """
    class S:
        pass
    def f(self):
        """Method docstring of C.f."""
    @some_random_decorator
    @some_other_decorator
    def h(self):
        """Method docstring."""
    @some_random_decorator
    @classmethod
    def cls_method(cls):
        pass
    @staticmethod
    def static_method():
        pass


class D(C):
    """Subclass docstring."""
    class T:
        pass
    def f(self):
        # no docstring, should be inherited from superclass
        pass
    def g(self):
        pass
    @classmethod
    def cls_method2(cls):
        pass
    def static_method2():
        pass
    static_method2 = staticmethod(static_method2)

def _private():
    pass
