ReStructuredText
----------------

.. toctree::

    rst

``pydoctor`` needs the following packages to offer *restructuredtext* support::

   $ pip install -U docutils

Fields
^^^^^^

As a reminder, here are some of the supported *restructuredtext* fields:

    - ``:cvar foo:``
    - ``:ivar foo:``
    - ``:var foo:``
    - ``:param bar:`` (synonym: ``:arg bar:``)
    - ``:type bar: str``
    - ``:return:``
    - ``:rtype: list``
    - ``:except ValueError:``

Alternatively, fields can be passed with this syntax::

    :Parameters:
        size
            The size of the fox (in meters)
        weight : float
            The weight of the fox (in stones)
        age : int
            The age of the fox (in years)

Directives
^^^^^^^^^^

Here is a list of the supported ReST directives by package of origin:

- `docutils`: ``.. include::``, ``.. contents::``, ``.. image::``, ``.. figure::``, ``.. unicode::``, ``.. raw::``, ``.. math::``, etc
- `epydoc`: None
- `Sphinx`: None
- `pydoctor`: ``.. python::``, 



.. note:: HTML Classes *restructuredtext* markup creates have a ``"rst-"`` prefix

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.

For more documentation, read the `ReST docutils syntax reference <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_.
