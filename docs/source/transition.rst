Transition to ``pydoctor``
==========================

From ``epydoc``
---------------

If you are looking for a successor to ``epydoc`` after moving to Python 3, ``pydoctor`` is the right tool for your project!

.. important::

    - ``pydoctor`` dropped support for the ``X{}`` tag. All other epytext matkup should be fully supported

From ``pdoc3``
--------------

There a couple reasons to stop using ``pdoc3``, the main one beeing the swastika in their website footer.

.. important::

    - ``pydoctor`` do not support natively markdown docstrings. The easiest is to use `restructuredtext` docformat as they are sharing numerous markup syntax.

    - ``pydoctor`` can only genrate HTML, if you are using markdown output, consider using ``pdocs``. 

    - Some ReStructuredText directives are not supported yet, please refer to "Documentation Formats / ReStructuredText Support" for more infos

Other alternatives
------------------

The following softwares are considered as potential alternatives to ``pydoctor`` as they offer similar (but different) features and usage. 

- ``portray``: `Github repo <https://github.com/timothycrosley/portray>`_
- ``mkdocstrings``: `Github repo <https://github.com/pawamoy/mkdocstrings>`_
