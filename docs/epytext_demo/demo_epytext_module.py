"""
This is a module demonstrating epydoc code documentation features.

Most part of this documentation is using Python type hinting.
"""

from abc import ABC


def demo_fields_docstring_arguments(m, b):  # type: ignore
    """
    Fields are used to describe specific properties of a documented object.

    This function can be used in conjuction with L{demo_typing_arguments} to
    find an arbitrary function's zeros.

    @type  m: number
    @param m: The slope of the line.
    @type  b: number
    @param b: The y intercept of the line.
    @rtype:   number
    @return:  the x intercept of the line M{y=m*x+b}.
    """
    return -b/m


def demo_typing_arguments(name: str, size: bytes) -> bool:
    """
    Type documentation can be extracted from standard Python type hints.

    @param name: The human readable name for something.
    @param size: How big the name should be.
    @return: Always C{True}.
    """
    return True


def demo_cross_reference() -> None:
    """
    The inline markup construct C{LE{lb}text<object>E{rb}} is used to create links to the documentation for other Python objects.
    'text' is the text that should be displayed for the link, and 'object' is the name of the Python object that should be linked to.

    If you wish to use the name of the Python object as the text for the link, you can simply write C{LE{lb}objectE{rb}}.

        - L{demo_typing_arguments}
        - L{Custom name <demo_typing_arguments>}
    """


class _PrivateClass:
    """
    This is the docstring of a private class.
    """

    def method_inside_private(self) -> bool:
        """
        A public method inside a private class.

        @return: Something.
        """
        return True


    def _private_inside_private(self) -> bool:
        """
        A private method inside a private class.

        @return: Something.
        """
        return True


class DemoClass(ABC):
    """
    This is the docstring of this class.
    """

    def __init_(self, one: str, two: bytes) -> None:
        """
        Documentation for class initialization.

        @param one: Docs for first argument.
        @param two: Docs for second argument.
        """

    @property
    def read_only(self) -> int:
        """
        This is a read-only property.
        """
        return 1

    @property
    def read_and_write(self) -> int:
        """
        This is a read-write property.
        """
        return 1

    @read_and_write.setter
    def read_and_write(self, value: int) -> None:
        """
        This is a docstring for setter.
        """

    @property
    def read_and_write_delete(self) -> int:
        """
        This is a read-write-delete property.
        """
        return 1

    @read_and_write_delete.setter
    def read_and_write_delete(self, value: int) -> None:
        """
        This is a docstring for setter.
        """

    @read_and_write_delete.deleter
    def read_and_write_delete(self) -> None:
        """
        This is a docstring for deleter.
        """
