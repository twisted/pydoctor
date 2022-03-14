How to Document Your Code
=========================


Docstrings
----------

In Python, a string at the top of a module, class or function is called a *docstring*.
For example::

    """This docstring describes the purpose of this module."""

    class C:
        """This docstring describes the purpose of this class."""

        def m(self):
            """This docstring describes the purpose of this method."""

Pydoctor also supports *attribute docstrings*::

    CONST = 123
    """This docstring describes a module level constant."""

    class C:
        cvar = None
        """This docstring describes a class variable."""

        def __init__(self):
            self.ivar = []
            """This docstring describes an instance variable."""

Attribute docstrings are not part of the Python language itself (`PEP 224 <https://www.python.org/dev/peps/pep-0224/>`_ was rejected), so these docstrings are not available at runtime.

For long docstrings, start with a short summary, followed by an empty line::

    def f():
        """This line is used as the summary.

        More detail about the workings of this function can be added here.
        They will be displayed in the documentation of the function itself
        but omitted from the summary table.
        """

Since docstrings are Python strings, escape sequences such as ``\n`` will be parsed as if the corresponding character---for example a newline---occurred at the position of the escape sequence in the source code.

To have the text ``\n`` in a docstring at runtime and in the generated documentation, you either have escape it twice in the source: ``\\n`` or use the ``r`` prefix for a raw string literal.
The following example shows the raw string approach::

    def iter_lines(stream):
        r"""Iterate through the lines in the given text stream,
        with newline characters (\n) removed.
        """
        for line in stream:
            yield line.rstrip('\n')

Further reading:

- `Python Tutorial: Documentation Strings <https://docs.python.org/3/tutorial/controlflow.html#documentation-strings>`_
- `PEP 257 -- Docstring Conventions <https://www.python.org/dev/peps/pep-0257/>`_
- `Python Language Reference: String and Bytes literals <https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals>`_


Docstring assignments
---------------------

Simple assignments to the ``__doc__`` attribute of a class or function are recognized by pydoctor::

    class CustomException(Exception):
        __doc__ = MESSAGE = "Oops!"

Non-trivial assignments to ``__doc__`` are not supported. A warning will be logged by pydoctor as a reminder that the assignment will not be part of the generated API documentation::

    if LOUD_DOCS:
        f.__doc__ = f.__doc__.upper()

Assignments to ``__doc__`` inside functions are ignored by pydoctor. This can be used to avoid warnings when you want to modify runtime docstrings without affecting the generated API documentation::

    def mark_unavailable(func):
        func.__doc__ = func.__doc__ + '\n\nUnavailable on this system.'

    if not is_supported('thing'):
        mark_unavailable(do_the_thing)

Augmented assignments like ``+=`` are currently ignored as well, but that is an implementation limitation rather than a design decision, so this might change in the future.

Constants
---------

The value of a constant is rendered with syntax highlighting. 
See `module <docformat/restructuredtext/restructuredtext_demo.constants.html>`_ demonstrating the constant values rendering.

Following `PEP8 <https://www.python.org/dev/peps/pep-0008/#constants>`_, any variable defined with all upper case name will be considered as a constant.
Additionally, starting with Python 3.8, one can use the `typing.Final <https://www.python.org/dev/peps/pep-0008/#constants>`_ qualifier to declare a constant. 

For instance, these variables will be recognized as constants::
    
    from typing import Final
    X = 3.14
    y: Final = ['a', 'b']

In Python 3.6 and 3.7, you can use the qualifier present in the `typing_extensions` instead of `typing.Final`::

   from typing_extensions import Final
   z: Final = 'relative/path'

.. _codedoc-fields:

Fields
------

Pydoctor supports most of the common fields usable in Sphinx, and some others.

Epytext fields are written with arobase, like ``@field:`` or ``@field arg:``.
ReStructuredText fields are written with colons, like ``:field:`` or ``:field arg:``. 

Here are the supported fields (written with ReStructuredText format, but same fields are supported with Epytext): 

    - ``:cvar foo:``, document a class variable. Applicable in the context of the docstring of a class.
    - ``:ivar foo:``, document a instance variable. Applicable in the context of the docstring of a class.
    - ``:var foo:``, document a variable. Applicable in the context of the docstring of a module or class. 
      If used in the context of a class, behaves just like ``@ivar:``.
    - ``:note:``, add a note section.
    - ``:param bar:`` (synonym: ``@arg bar:``), document a function's (or method's) parameter. 
      Applicable in the context of the docstring of a function of method. 
    - ``:keyword:``, document a function's (or method's) keyword parameter (``**kwargs``).
    - ``:type bar: C{list}``, document the type of an argument/keyword or variable, depending on the context.
    - ``:return:`` (synonym: ``@returns:``), document the return type of a function (or method).
    - ``:rtype:`` (synonym: ``@returntype:``), document the type of the return value of a function (or method).
    - ``:yield:`` (synonym: ``@yields:``), document the values yielded by a generator function (or method).
    - ``:ytype:`` (synonym: ``@yieldtype:``), document the type of the values yielded by a generator function (or method).
    - ``:raise ValueError:`` (synonym: ``@raises ValueError:``), document the potential exception a function (or method) can raise.
    - ``:warn RuntimeWarning:`` (synonym: ``@warns ValueError:``), document the potential warning a function (or method) can trigger.
    - ``:see:`` (synonym: ``@seealso:``), add a see also section.
    - ``:since:``, document the date and/or version since a component is present in the API.
    - ``:author:``, document the author of a component, generally a module.

.. note:: Currently, any other fields will be considered "unknown" and will be flagged as such. 
    See `"fields" issues <https://github.com/twisted/pydoctor/issues?q=is%3Aissue+is%3Aopen+fields>`_
    for discussions and improvements.

.. note:: Unlike Sphinx, ``vartype`` and ``kwtype`` are not recognized as valid fields, we simply use ``type`` everywhere.

Type fields
~~~~~~~~~~~

Type fields, namely ``type``, ``rtype`` and ``ytype``, can be interpreted, such that, instead of being just a regular text field, 
types can be linked automatically.
For reStructuredText and Epytext documentation format, enable this behaviour with the option:: 
    
    --process-fields

The type auto-linking is always enabled for Numpy and Google style documentation formats.

Like in Sphinx, regular types and container types such as lists and dictionaries can be linked automatically:: 

    :type priority: int
    :type priorities: list[int]
    :type mapping: dict(str, int)
    :type point: tuple[float, float]

Natural language types can be linked automatically if separated by the words “or”, "and", "to", "of" or the comma::

    :rtype: float or str
    :returntype: list of str or list[int]
    :ytype: tuple of str, int and float
    :yieldtype: mapping of str to int

Additionally, it's still possible to include regular text description inside a type specification::

    :rtype: a result that needs a longer text description or str
    :rtype: tuple of a result that 
        needs a longer text description and str

Some special keywords will be recognized: "optional" and "default"::

    :type value: list[float], optional
    :type value: int, default: -1
    :type value: dict(str, int), default: same as default_dict

.. note:: Literals caracters - numbers and strings within quotes - will be automatically rendered like docutils literals.

.. note:: It's not currently possible to combine parameter type and description inside the same ``param`` field, see issue `#267 <https://github.com/twisted/pydoctor/issues/267>`_.

Type annotations
----------------

Type annotations in your source code will be included in the API documentation that pydoctor generates.
For example::

    colors: dict[str, int] = {
        'red': 0xFF0000, 'green': 0x00FF00, 'blue': 0x0000FF
    }

    def inverse(name: str) -> int:
        return colors[name] ^ 0xFFFFFF

If your project still supports Python versions prior to 3.6, you can also use type comments::

    from typing import Optional

    favorite_color = None  # type: Optional[str]

However, the ability to extract type comments only exists in the parser of Python 3.8 and later, so make sure you run pydoctor using a recent Python version, or the type comments will be ignored.

There is basic type inference support for variables/constants that are assigned literal values.
Unlike for example mypy, pydoctor cannot infer the type for computed values::

    FIBONACCI = [1, 1, 2, 3, 5, 8, 13]
    # pydoctor will automatically determine the type: list[int]

    SQUARES = [n ** 2 for n in range(10)]
    # pydoctor needs an annotation to document this type

Further reading:

- `Python Standard Library: typing -- Support for type hints <https://docs.python.org/3/library/typing.html>`_
- `PEP 483 -- The Theory of Type Hints <https://www.python.org/dev/peps/pep-0483/>`_


Properties
----------

A method with a decoration ending in ``property`` or ``Property`` will be included in the generated API documentation as an attribute rather than a method::

    class Knight:

        @property
        def name(self):
            return self._name

        @abc.abstractproperty
        def age(self):
            raise NotImplementedError

        @customProperty
        def quest(self):
            return f'Find the {self._object}'

All you have to do for pydoctor to recognize your custom properties is stick to this naming convention.


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

.. note::
    Pydoctor actually supports 3 types of privacy: public, private and hidden. 
    See `Override objects privacy <customize-privacy>` for more informations.

Re-exporting
------------

If your project is a library or framework of significant size, you might want to split the implementation over multiple private modules while keeping the public API importable from a single module. This is supported using pydoctor's re-export feature.

A documented element which is defined in one (typically private) module can be imported into another module and re-exported by naming it in the ``__all__`` special variable. Doing so will move its documentation to the module from where it was re-exported, which is where users of your project will be importing it from.

In the following example, the documentation of ``MyClass`` is written in the ``my_project.core._impl`` module, which is imported into the top-level ``__init__.py`` and then re-exported by including ``"MyClass"`` in the value of ``__all__``. As a result, the documentation for ``MyClass`` can be read in the documentation of the top-level ``my_project`` package::

  ├── README.rst
  ├── my_project
  │   ├── __init__.py      <-- Re-exports my_project.core._impl.MyClass
  │   ├── core                 as my_project.MyClass
  │   │   ├── __init__.py
  │   │   ├── _impl.py     <-- Defines and documents MyClass

The content of ``my_project/__init__.py`` includes::

    from .core._impl import MyClass

    __all__ = ("MyClass",)
