pydoctor
--------

.. image:: https://travis-ci.org/twisted/pydoctor.svg?branch=tox-travis-2
  :target: https://travis-ci.org/twisted/pydoctor

.. image:: https://codecov.io/gh/twisted/pydoctor/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/twisted/pydoctor

.. image:: https://img.shields.io/badge/-documentation-blue
  :target: https://pydoctor.readthedocs.io/

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


Simple Usage
~~~~~~~~~~~~

You can run pydoctor on your project like this::

    $ pydoctor --make-html --html-output=docs/api src/mylib

For more info, `Read The Docs <https://pydoctor.readthedocs.io/>`_.

Markup
~~~~~~

pydoctor currently supports the following markup languages in docstrings:

`epytext`__ (default)
    The markup language of epydoc.
    Simple and compact.

`restructuredtext`__
    The markup language used by Sphinx.
    More expressive than epytext, but also slightly more complex and verbose.

``plaintext``
    Text without any markup.

__ http://epydoc.sourceforge.net/manual-epytext.html
__ https://docutils.sourceforge.io/rst.html

You can select a different format using the ``--docformat`` option.

What's New?
~~~~~~~~~~~

in development
^^^^^^^^^^^^^^
* HTML templates are now customizable with ``--template-dir`` option.
* Change the fields layout to display the arguments type right after their name. Same goes for variables.

pydoctor 21.2.2
^^^^^^^^^^^^^^^

* Fix positioning of anchors, such that following a link to a member of a module or class will scroll its documentation to a visible spot at the top of the page.

pydoctor 21.2.1
^^^^^^^^^^^^^^^

* Fix presentation of the project name and URL in the navigation bars, such that it works as expected on all generated HTML pages.

pydoctor 21.2.0
^^^^^^^^^^^^^^^

* Removed the ``--html-write-function-pages`` option. As a replacement, you can use the generated Intersphinx inventory (``objects.inv``) for deep-linking your documentation.
* Fixed project version in the generated Intersphinx inventory. This used to be hardcoded to 2.0 (we mistook it for a format version), now it is unversioned by default and a version can be specified using the new ``--project-version`` option.
* Fixed multiple bugs in Python name resolution, which could lead to for example missing "implemented by" links.
* Fixed bug where class docstring fields such as ``cvar`` and ``ivar`` are ignored when they override inherited attribute docstrings.
* Property decorators containing one or more dots (such as ``@abc.abstractproperty``) are now recognized by the custom properties support.
* Improvements to `attrs`__ support:

  - Attributes are now marked as instance variables.
  - Type comments are given precedence over types inferred from ``attr.ib``.
  - Support positional arguments in ``attr.ib`` definitions. Please use keyword arguments instead though, both for clarity and to be compatible with future ``attrs`` releases.

* Improvements in the treatment of the ``__all__`` module variable:

  - Assigning an empty sequence is interpreted as exporting nothing instead of being ignored.
  - Better error reporting when the value assigned is either invalid or pydoctor cannot make sense of it.

* Added ``except`` field as a synonym of ``raises``, to be compatible with epydoc and to fix handling of the ``:Exceptions:`` consolidated field in reStructuredText.
* Exception types and external base classes are hyperlinked to their class documentation.
* Formatting of ``def func():`` and ``class Class:`` lines was made consistent with code blocks.
* Changes to the "Show/hide Private API" button:

  - The button was moved to the right hand side of the navigation bar, to avoid overlapping the content on narrow displays.
  - The show/hide state is now synced with a query argument in the location bar. This way, if you bookmark the page or send a link to someone else, the show/hide state will be preserved.
  - A deep link to a private API item will now automatically enable "show private API" mode.

* Improvements to the ``build_apidocs`` Sphinx extension:

  - API docs are now built before Sphinx docs, such that the rest of the documentation can link to it via Intersphinx.
  - New configuration variable ``pydoctor_url_path`` that will automatically update the ``intersphinx_mapping`` variable so that it uses the latest API inventory.
  - The extension can be configured to build API docs for more than one package.

* ``pydoctor.__version__`` is now a plain ``str`` instead of an ``incremental.Version`` object.

__ https://www.attrs.org/

pydoctor 20.12.1
^^^^^^^^^^^^^^^^

* Reject source directories outside the project base directory (if given), instead of crashing.
* Fixed bug where source directories containing symbolic links could appear to be outside of the project base directory, leading to a crash.
* Bring back source link on package pages.

pydoctor 20.12.0
^^^^^^^^^^^^^^^^

* Python 3.6 or higher is required.

* There is now a user manual that can be built with Sphinx or read online on `Read the Docs`__. This is a work in progress and the online version will be updated between releases.

* Added support for Python language features:

  - Type annotations of function parameters and return value are used when the docstring does not document a type.
  - Functions decorated with ``@property`` or any other decorator with a name ending in "property" are now formatted similar to variables.
  - Coroutine functions (``async def``) are included in the output.
  - Keyword-only and position-only parameters are included in the output.

* Output improvements:

  - Type names in annotations are hyperlinked to the corresponding documentation.
  - Styling changes to make the generated documentation easier to read and navigate.
  - Private API is now hidden by default on the Module Index, Class Hierarchy and Index of Names pages.
  - The pydoctor version is included in the "generated by" line in the footer.

* All parents of the HTML output directory are now created by pydoctor; previously it would create only the deepest directory.

* The ``--add-package`` and ``--add-module`` options have been deprecated; pass the source paths as positional arguments instead.

* New option ``-W``/``--warnings-as-errors`` to fail your build on documentation errors.

* Linking to the standard library documentation is more accurate now, but does require the use of an Intersphinx inventory (``--intersphinx=https://docs.python.org/3/objects.inv``).

* Caching of Intersphinx inventories is now enabled by default.

* Added a `Sphinx extension`__ for embedding pydoctor's output in a project's Sphinx documentation.

* Added an extra named ``rst`` for the dependencies needed to process reStructuredText (``pip install -U pydoctor[rst]``).

* Improved error reporting:

  - More accurate source locations (file + line number) in error messages.
  - Warnings were added for common mistakes when documenting parameters.
  - Clearer error message when a link target is not found.

* Increased reliability:

  - Fixed crash when analyzing ``from package import *``.
  - Fixed crash when the line number for a docstring error is unknown.
  - Better unit test coverage, more system tests, started adding type annotations to the code.
  - Unit tests are also run on Windows.

__ https://pydoctor.readthedocs.io/
__ https://pydoctor.readthedocs.io/en/latest/usage.html#building-pydoctor-together-with-sphinx-html-build

pydoctor 20.7.2
^^^^^^^^^^^^^^^

* Fix handling of external links in reStructuredText under Python 3.
* Fix reporting of errors in reStructuredText under Python 3.
* Restore syntax highlighting of Python code blocks.

pydoctor 20.7.1
^^^^^^^^^^^^^^^

* Fix cross-reference links to builtin types in standard library.
* Fix and improve error message printed for unknown fields.

pydoctor 20.7.0
^^^^^^^^^^^^^^^

* Python 3 support.
* Type annotations on attributes are supported when running on Python 3.
* Type comments on attributes are supported when running on Python 3.8+.
* Type annotations on function definitions are not supported yet.
* Undocumented attributes are now included in the output.
* Attribute docstrings: a module, class or instance variable can be documented by a following it up with a docstring.
* Improved error reporting: more errors are reported, error messages include file name and line number.
* Dropped support for implicit relative imports.
* Explicit relative imports (using ``from``) no longer cause warnings.
* Dropped support for index terms in epytext (``X{}``). This was never supported in any meaningful capacity, but now the tag is gone.

This was the last major release to support Python 2.7 and 3.5.

.. description-end
