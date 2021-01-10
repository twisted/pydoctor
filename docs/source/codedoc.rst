How to Document Your Code
=========================


Docstrings
----------

In Python, a string at the top of a module, class or function is called a *docstring*. For example::

    """This docstring describes the purpose of this module."""

    class C:
        """This docstring describes the purpose of this class."""

        def m(self):
            """This docstring describes the purpose of this method."""

As an extension, pydoctor also supports *attribute docstrings*::

    CONST = 123
    """This docstring describes a module level variable/constant."""

    class C:
        cvar = None
        """This docstring describes a class variable."""

        def __init__(self):
            self.ivar = []
            """This docstring describes an instance variable."""

For long docstrings, start with a short summary, followed by an empty line::

    def f():
        """This line is used as the summary.

        More detail about the workings of this function can be added here.
        They will be displayed in the documentation of the function itself
        but omitted from the summary table.
        """

Further reading:

- `Python Tutorial: Documentation Strings <https://docs.python.org/3/tutorial/controlflow.html#documentation-strings>`_
- `PEP 257 -- Docstring Conventions <https://www.python.org/dev/peps/pep-0257/>`_


Type annotations
----------------

Type annotations in your source code will be included in the API documentation that pydoctor generates. For example::

    colors: dict[str, int] = {
        'red': 0xFF0000, 'green': 0x00FF00, 'blue': 0x0000FF
    }

    def inverse(name: str) -> int:
        return colors[name] ^ 0xFFFFFF

If your project still supports Python versions prior to 3.6, you can also use type comments::

    from typing import Optional

    favorite_color = None  # type: Optional[str]

However, the ability to extract type comments only exists in the parser of Python 3.8 and later, so make sure you run pydoctor using a recent Python version, or the type comments will be ignored.

There is basic type inference support for variables/constants that are assigned literal values. But pydoctor cannot infer the type for computed values, unlike for example mypy::

    FIBONACCI = [1, 1, 2, 3, 5, 8, 13]
    # pydoctor will automatically determine the type: list[int]

    SQUARES = [n ** 2 for n in range(10)]
    # pydoctor needs an annotation to document this type

Further reading:

- `Python Standard Library: typing -- Support for type hints <https://docs.python.org/3/library/typing.html>`_
- `PEP 483 -- The Theory of Type Hints <https://www.python.org/dev/peps/pep-0483/>`_

Using ``attrs``
---------------

If you use the ``attrs`` library to define attributes on your classes, you can use inline docstrings combined with type annotations to provide pydoctor with all the information it needs to document those attributes::

    import attr

    @attr.s(auto_attribs=True)
    class SomeClass:

        a_number: int = 42
        """One number."""

        list_of_numbers: list[int]
        """Multiple numbers."""

If you are using explicit ``attr.ib`` definitions instead of ``auto_attribs``, pydoctor will try to infer the type of the attribute from the default value, but will need help in the form of type annotations or comments for collections and custom types::

    from typing import List
    import attr

    @attr.s
    class SomeClass:

        a_number = attr.ib(default=42)
        """One number."""

        list_of_numbers = attr.ib(factory=list)  # type: List[int]
        """Multiple numbers."""


Private API
-----------

Modules, classes and functions of which the name starts with an underscore are considered *private*. These will not be shown by default, but there is a button in the generated documentation to reveal them. An exception to this rule is *dunders*: names that start and end with double underscores, like ``__str__`` and ``__eq__``, which are always considered public::

    class _Private:
        """This class won't be shown unless explicitly revealed."""

    class Public:
        """This class is public, but some of its methods are private."""

        def public(self):
            """This is a public method."""

        def _private(self):
            """For internal use only."""

        def __eq__(self, other):
            """Is this object equal to 'other'?

            This method is public.
            """


Re-exporting
------------

If your project is a library or framework of significant size, you might want to split the implementation over multiple private modules while keeping the public API importable from a single module. This is supported using pydoctor's re-export feature.

A documented element which is defined in one (typically private) module can be imported into another module and re-exported by naming it in the ``__all__`` special variable. Doing so will move its documentation to the module from where it was re-exported, which is where users of your project will be importing it from.

In the following example, the documentation of ``MyClass`` is written in the ``my_project.core._impl`` module, which is imported into the top-level ``__init__.py`` and then re-exported by including ``"MyClass"`` in the value of ``__all__``. As a result, the documentation for ``MyClass`` can be read in the documentation of the top-level ``my_project`` package::

  ├── README.rst
  ├── my_project
  │   ├── __init__.py      <-- Re-export my_project.core._impl.MyClass
  │   ├── core                 as my_project.MyClass
  │   │   ├── __init__.py
  │   │   ├── _impl.py     <-- Defines and documents MyClass

The content of ``my_project/__init__.py`` includes::

    from .core._impl import MyClass

    __all__ = ["MyClass"]
