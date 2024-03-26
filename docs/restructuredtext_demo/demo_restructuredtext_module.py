"""
This is a module demonstrating reST code documentation features.

Most part of this documentation is using Python type hinting.
"""
from abc import ABC
from ast import Tuple
import math
import zope.interface
import zope.schema
from typing import overload, Callable, Sequence, Optional, AnyStr, Generator, Union, List, Dict, TYPE_CHECKING
from incremental import Version
from twisted.python.deprecate import deprecated, deprecatedProperty

if TYPE_CHECKING:
    from typing_extensions import Final

Parser = Callable[[str], Tuple[int, bytes, bytes]]
"""
Type aliases are documented as such and their value is shown just like constants.
"""

LANG = 'Fr'
"""
This is a constant. See `constants` for more examples.
"""

lang: 'Final[Sequence[str]]' = ['Fr', 'En']
"""
This is also a constant, but annotated with typing.Final.
"""

@deprecated(Version("demo", "NEXT", 0, 0), replacement=math.prod)
def demo_product_deprecated(x, y) -> float: # type: ignore
    return float(x * y)

def demo_fields_docstring_arguments(m, b = 0):  # type: ignore
    """
    Fields are used to describe specific properties of a documented object.

    This function's ":type:" tags are taking advantage of the --process-types.

    :type  m: numbers.Number
    :param m: The slope of the line.
    :type  b: numbers.Number, optional
    :param b: The y intercept of the line.
    :rtype:   numbers.Number
    :return:  the x intercept of the line M{y=m*x+b}.
    """
    return -b/m

def demo_consolidated_fields(a:float, b):  # type: ignore
    """
    Fields can be condensed into one "consolidated" field. Looks better in plain text.

    :Parameters:
        - `a`: The size of the fox (in meters)
        - `b`: The weight of the fox (in stones)
    :rtype: str
    :return: The number of foxes
    """
    return -b/a

def demo_typing_arguments(name: str, size: Optional[bytes] = None) -> bool:
    """
    Type documentation can be extracted from standard Python type hints.

    :param name: The human readable name for something.
    :param size: How big the name should be. Leave none if you don't care.
    :return: Always `True`.
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
    r"""
    The inline markup construct ```object``` is used to create links to the documentation for other Python objects.
    'text' is the text that should be displayed for the link, and 'object' is the name of the Python object that should be linked to.

    If you wish to use the name of the Python object as the text for the link, you can simply write ```object``` -> `object`.

    - `demo_typing_arguments`
    """

@overload
def demo_overload(s: str) -> str:
    ...

@overload
def demo_overload(s: bytes) -> bytes:
    ...

def demo_overload(s: Union[str, bytes]) -> Union[str, bytes]:
    """
    Overload signatures appear without the main signature and with ``@overload`` decorator.

    :param s: Some string or bytes param.
    :return: Some string or bytes result.
    """
    raise NotImplementedError

def demo_undocumented(s: str) -> str:
    raise NotImplementedError


class _PrivateClass:
    """
    This is the docstring of a private class.
    """

    def method_inside_private(self) -> bool:
        """
        A public method inside a private class.

        :return: Something.
        """
        return True


    def _private_inside_private(self) -> List[str]:
        """
        Returns something. 
        :rtype: `list`
        """
        return []
    
    @property
    def isPrivate(self) -> bool:
        """Whether this class is private"""
        return True
    @isPrivate.setter
    def isPrivate(self, v) -> bool:
        raise NotImplemented()
    
    @property
    def isPublic(self) -> bool:
        """Whether this class is public"""
        return False
    @isPublic.setter
    def isPublic(self, v) -> bool:
        raise NotImplemented()



class DemoClass(ABC, _PrivateClass):

    """
    This is the docstring of this class.

    .. versionchanged:: 1.1
        This class now inherits from `_PrivateClass` and 
        demonstrate the ``.. versionchanged::`` directive support.
    
    .. versionchanged:: 1.2
        Add `read_and_write_delete` property.
    """

    def __init__(self, one: str, two: bytes) -> None:
        """
        Documentation for class initialization.

        :param one: Docs for first argument.
        :param two: Docs for second argument.
        """

    @property
    def read_only(self) -> int:
        """
        This is a read-only property.
        """
        return 1

    @deprecatedProperty(Version("demo", 1, 3, 0), replacement=read_only)
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
        Their are usually not explicitely documented though. 
        """

    @property
    def read_and_write_delete(self) -> int:
        """
        This is the docstring of the property.
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
    
    @property
    def undoc_prop(self) -> bytes:
        """This property has a docstring only on the getter."""
    @undoc_prop.setter
    def undoc_prop(self, p) -> None: # type:ignore
        ...
    
    @property
    def isPrivate(self) -> bool:
        return False
    
    @_PrivateClass.isPublic.setter
    def isPublic(self, v):
        self._v = v

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
