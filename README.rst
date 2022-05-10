pydoctor
--------

.. image:: https://img.shields.io/pypi/pyversions/pydoctor.svg
  :target: https://pypi.python.org/pypi/pydoctor

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

`google`__
    Docstrings formatted as specified by the Google Python Style Guide. 
    (compatible with reStructuredText markup)

`numpy`__
    Docstrings formatted as specified by the Numpy Docstring Standard. 
    (compatible with reStructuredText markup)

``plaintext``
    Text without any markup.

__ http://epydoc.sourceforge.net/manual-epytext.html
__ https://docutils.sourceforge.io/rst.html
__ https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings
__ https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard

You can select a different format using the ``--docformat`` option or the ``__docformat__`` module variable. 

What's New?
~~~~~~~~~~~

in development
^^^^^^^^^^^^^^
* Add support for `twisted.python.deprecated` (this was originally part of Twisted's customizations).
* Add support for re-exporting names imported from a wildcard import.

pydoctor 22.5.1
^^^^^^^^^^^^^^^
* ``docutils>=0.17`` is now the minimum supported version. This was done to fix crashing with ``AttributeError`` when processing type fields.

pydoctor 22.5.0
^^^^^^^^^^^^^^^
* Add Read The Docs theme, enable it with option ``--theme=readthedocs``.
* Add a sidebar. Configure it with options ``--sidebar-expand-depth`` and ``--sidebar-toc-depth``. Disable with ``--no-sidebar``. 
* Highlight the active function or attribute.
* Packages and modules are now listed together.
* Docstring summaries are now generated from docutils nodes:

  - fixes a bug in restructuredtext references in summary.
  - still display summary when the first paragraph is long instead of "No summary".

* The module index now uses a more compact presentation for modules with more than 50 submodules and no subsubmodules.
* Fix source links for code hosted on Bitbucket or SourceForge.
* The ``--html-viewsource-template`` option was added to allow for custom URL scheme when linking to the source code pages and lines. 

pydoctor 22.4.0
^^^^^^^^^^^^^^^
* Add option ``--privacy`` to set the privacy of specific objects when default rules doesn't fit the use case.
* Option ``--docformat=plaintext`` overrides any assignments to ``__docformat__`` 
  module variable in order to focus on potential python code parsing errors.
* Switch to ``configargparse`` to handle argument and configuration file parsing (`more infos <https://pydoctor.readthedocs.io/en/latest/help.html>`_).
* Improved performances with caching of docstring summaries.

pydoctor 22.3.0
^^^^^^^^^^^^^^^
* Add client side search system based on lunr.js.
* Fix broken links in docstring summaries.
* Add cache for the xref linker, reduces the number of identical warnings.
* Fix crash when reparenting objects with duplicate names.

pydoctor 22.2.2
^^^^^^^^^^^^^^^
* Fix resolving names re-exported in ``__all__`` variable.

pydoctor 22.2.1
^^^^^^^^^^^^^^^
* Fix crash of pydoctor when processing a reparented module.

pydoctor 22.2.0
^^^^^^^^^^^^^^^
* Improve the name resolving algo such that it checks in super classes for inherited attributes.
* C-modules wins over regular modules when there is a name clash.
* Packages wins over modules when there is a name clash.
* Fixed that modules were processed in a random order leading to several hard to reproduce bugs.
* Intersphinx links have now dedicated markup.
  With the default theme,
  this allows to have the external intershinx links blue while the internal links are red.
* Smarter line wrapping in summary and parameters tables.
* Any code inside of ``if __name__ == '__main__'`` is now excluded from the documentation.
* Fix variables named like the current module not being documented.
* The Module Index now only shows module names instead of their full name. You can hover over a module link to see the full name.
* If there is only a single root module, `index.html` now documents that module (previously it only linked the module page).
* Fix introspection of functions comming from C-extensions.
* Fix that the colorizer might make Twisted's flatten function crash with surrogates unicode strings.

pydoctor 21.12.1
^^^^^^^^^^^^^^^^
* Include module ``sre_parse36.py`` within ``pydoctor.epydoc`` to avoid an extra PyPi dependency.

pydoctor 21.12.0
^^^^^^^^^^^^^^^^

* Add support for reStructuredText directives ``.. deprecated::``, ``.. versionchanged::`` and ``.. versionadded::``.
* Add syntax highlight for constant values, decorators and parameter defaults.
* Embedded documentation links inside the value of constants, decorators and parameter defaults.
* Provide option ``--pyval-repr-maxlines`` and ``--pyval-repr-linelen`` to control the size of a constant value representation. 
* Provide option ``--process-types`` to automatically link types in docstring fields (`more info <https://pydoctor.readthedocs.io/en/latest/codedoc.html#type-fields>`_).
* Forked Napoleon Sphinx extension to provide google-style and numpy-style docstring parsing. 
* Introduced fields ``warns``,  ``yields`` and ``yieldtype``. 
* Following google style guide, ``*args`` and ``**kwargs`` are now rendered with asterisks in the parameters table.
* Mark variables as constants when their names is all caps or if using `Final` annotation.

pydoctor 21.9.2
^^^^^^^^^^^^^^^

* Fix ``AttributeError`` raised when parsing reStructuredText consolidated fields, caused by a change in ``docutils`` 0.18.
* Fix ``DeprecationWarning``, use newer APIs of ``importlib_resources`` module.

pydoctor 21.9.1
^^^^^^^^^^^^^^^

* Fix deprecation warning and officially support Python 3.10.
* Fix the literals style (use same style as before).

pydoctor 21.9.0
^^^^^^^^^^^^^^^

* Add support for multiple themes, selectable with ``--theme`` option.
* Support selecting a different docstring format for a module using the ``__docformat__`` variable.
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
