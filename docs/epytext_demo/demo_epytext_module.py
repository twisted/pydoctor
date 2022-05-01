"""
This is a module demonstrating epydoc code documentation features.

Most part of this documentation is using Python type hinting.
"""

from abc import ABC
import math
from typing import AnyStr, Dict, Generator, List, Union, TYPE_CHECKING
from somelib import SomeInterface
import zope.interface
import zope.schema
from typing import Sequence, Optional
from incremental import Version
from twisted.python.deprecate import deprecated, deprecatedProperty

if TYPE_CHECKING:
    from typing_extensions import Final

LANG = 'Fr'
"""
This is a constant. See L{constants} for more examples.
"""

lang: 'Final[Sequence[str]]' = ['Fr', 'En']
"""
This is also a constant, but annotated with typing.Final.
"""

@deprecated(Version("demo", "NEXT", 0, 0), replacement=math.prod)
def demo_product_deprecated(x, y) -> float: # type: ignore
    return float(x * y)

def demo_fields_docstring_arguments(m, b):  # type: ignore
    """
    Fields are used to describe specific properties of a documented object.

    This function can be used in conjunction with L{demo_typing_arguments} to
    find an arbitrary function's zeros.

    @type  m: number
    @param m: The slope of the line.
    @type  b: number
    @param b: The y intercept of the line.
    @rtype:   number
    @return:  the x intercept of the line M{y=m*x+b}.
    """
    return -b/m

def demo_typing_arguments(name: str, size: Optional[bytes] = None) -> bool:
    """
    Type documentation can be extracted from standard Python type hints.

    @param name: The human readable name for something.
    @param size: How big the name should be. Leave none if you don't care.
    @return: Always C{True}.
    """
    return True

def demo_long_function_and_parameter_names__this_indeed_very_long(
        this_is_a_very_long_parameter_name_aahh: str, 
        what__another_super_super_long_name__ho_no: Generator[Union[List[AnyStr], Dict[str, AnyStr]], None, None]) -> bool:
    """
    Long names and annotations should display on several lines when they don't fit in a single line. 
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


class DemoClass(ABC, SomeInterface, _PrivateClass):
    """
    This is the docstring of this class.
    """

    def __init__(self, one: str, two: bytes) -> None:
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

    @deprecatedProperty(Version("demo", 1, 3, 0), replacement=read_only)
    @property
    def read_only_deprecated(self) -> int:
        """
        This is a deprecated read-only property.
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


class IContact(zope.interface.Interface):
    """
    Example of an interface with schemas.

    Provides access to basic contact information.
    """

    first = zope.schema.TextLine(description="First name")

    email = zope.schema.TextLine(description="Electronic mail address")

    address = zope.schema.Text(description="Postal address")

    def send_email(text: str) -> None:
        pass
