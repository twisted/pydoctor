Transition to ``pydoctor``
==========================

From ``epydoc``
---------------

If you are looking for a successor to ``epydoc`` after moving to Python 3, ``pydoctor`` is the right tool for your project!

- ``pydoctor`` dropped support for the ``X{}`` tag. All other epytext markup syntax should be fully supported.

- Specific per file ``__docformat__`` are not supported, though it won't create errors if you keep them.

From ``pdoc3``
--------------

- ``pydoctor`` do not support markdown docstrings. The easiest is to use *restructuredtext* docformat as they are sharing numerous markup syntax.

- ``pydoctor`` can only genrate HTML, if you are using markdown output, consider using ``pdocs``.

- Some ReStructuredText directives are not supported yet, please refer to `Documentation Formats <docformat.html>`_ section for more infos.

- All references to ``__pdoc__`` module variable should be deleted as they are not supported. If you dynamically generated documentation, you should create a separate script and include it's output with an ``.. include::`` directive.
