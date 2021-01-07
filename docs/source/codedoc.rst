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

``__all__`` re-export
---------------------

A documented element which is defined in ``my_package.core.session`` module and included in the ``__all__`` special variable of ``my_package``
- in the ``__init__.py`` that it is imported into - will end up in the documentation of ``my_package``.

For instance, in the following exemple, the documentation of ``MyClass`` will be moved to the root package, ``my_package``.

::

  ├── CONTRIBUTING.rst
  ├── LICENSE.txt
  ├── README.rst
  ├── my_package
  │   ├── __init__.py     <-- Re-export `my_package.core.session.MyClass`
  │   ├── core                as `my_package.MyClass`
  │   │   ├── __init__.py
  │   │   ├── session.py  <-- Defines `MyClass`

The content of ``my_package/__init__.py`` includes::

  from .core.session import MyClass
  __all__ = ['MyClass', 'etc.']
