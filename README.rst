pydoctor
========

.. image:: https://travis-ci.org/twisted/pydoctor.svg?branch=tox-travis-2
  :target: https://travis-ci.org/twisted/pydoctor

.. image:: https://codecov.io/gh/twisted/pydoctor/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/twisted/pydoctor

This is *pydoctor*, an API documentation generator that works by
static analysis.

It was written primarily to replace ``epydoc`` for the purposes of the
Twisted project as ``epydoc`` has difficulties with ``zope.interface``.
If you are looking for a successor to ``epydoc`` after moving to Python 3,
``pydoctor`` might be the right tool for your project as well.

``pydoctor`` puts a fair bit of effort into resolving imports and
computing inheritance hierarchies and, as it aims at documenting
Twisted, knows about ``zope.interface``'s declaration API and can present
information about which classes implement which interface, and vice
versa.

.. contents:: Contents:


Usage
-----

You can run pydoctor on your project like this::

    $ pydoctor --make-html --html-output=docs/api --add-package=src/mylib

You can see the full list of options using ``pydoctor --help``.

Markup
------

pydoctor currently supports the following markup languages in docstrings:

`epytext`__ (default)
    The markup language of epydoc.
    Simple and compact.

`reStructuredText`__
    The markup language used by Sphinx.
    More expressive than epytext, but also slighly more complex and verbose.

plain text
    Text without any markup.

__ http://epydoc.sourceforge.net/manual-epytext.html
__ https://docutils.sourceforge.io/rst.html

You can select a different format using the ``--docformat`` option.

What's New?
-----------

pydoctor 20.7.2
~~~~~~~~~~~~~~~

* Fix handling of external links in reStructuredText under Python 3
* Fix reporting of errors in reStructuredText under Python 3
* Restore syntax highlighting of Python code blocks

pydoctor 20.7.1
~~~~~~~~~~~~~~~

* Fix cross-reference links to builtin types in standard library
* Fix and improve error message printed for unknown fields

pydoctor 20.7.0
~~~~~~~~~~~~~~~

* Python 3 support
* Type annotations on attributes are supported when running on Python 3
* Type comments on attributes are supported when running on Python 3.8+
* Type annotations on function definitions are not supported yet
* Undocumented attributes are now included in the output
* Attribute docstrings: a module, class or instance variable can be documented by a following it up with a docstring
* Improved error reporting: more errors are reported, error messages include file name and line number
* Dropped support for implicit relative imports
* Explicit relative imports (using ``from``) no longer cause warnings
* Dropped support for index terms in epytext (``X{}``); this was never supported in any meaningful capacity, but now the tag is gone

This will be the last major release to support Python 2.7 and 3.5: future major releases will require Python 3.6 or later.

.. description-end