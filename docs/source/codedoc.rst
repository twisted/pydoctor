How to Document Your Code
=========================

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
