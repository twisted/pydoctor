ReStructuredText
----------------

``pydoctor`` needs ``docutils`` to offer *restructuredtext* support.

For the language syntax documentation, read the `ReST docutils syntax reference <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_.

Cross references
^^^^^^^^^^^^^^^^

PyDoctor replaces the Docutils' default `interpreted text role <http://docutils.sourceforge.net/docs/ref/rst/roles.html>`_ with the creation of
`documentation crossreference links <http://epydoc.sourceforge.net/epydoc.html#documentation-crossreference-links>`_. If you want to create a crossreference link
to the ``module.Example`` class, simply put backquotes around it, typing::

    `module.Example`

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

In addition to the standard set of fields, the reStructruedText
parser also supports **consolidated fields**, which combine the documentation
for several objects into a single field.

These consolidated fields may be written using either a `bulleted list <http://docutils.sourceforge.net/docs/user/rst/quickref.html#bullet-lists>`_
or a `definition list <http://docutils.sourceforge.net/docs/user/rst/quickref.html#definition-lists>`_.

- If a consolidated field is written as a bulleted list, then each list item must begin with the field's argument,
  marked as `interpreted text <http://docutils.sourceforge.net/docs/user/rst/quickref.html#inline-markup>`_, and followed by a colon or dash.
- If a consolidated field is written as a definition list, then each definition item's term should contain the field's argument, (it is not mandatory for it being marked as interpreted text).

The following example shows the use of a definition list to define the ``Parameters`` consolidated field with type definition.
Note that *docutils* requires a space before and after the ``:`` used to mark classifiers.

.. code:: python

    def fox_speed(size, weight, age):
        """
        :Parameters:
            size
                The size of the fox (in meters)
            weight : float
                The weight of the fox (in stones)
            age : int
                The age of the fox (in years)
        """

Using a bulleted list.

.. code:: python

    def fox_speed(size:float, weight:float, age:int):
        """
        :Parameters:
            - `size`: The size of the fox (in meters)
            - `weight`: The weight of the fox (in stones)
            - `age`: The age of the fox (in years)
        """

The following consolidated fields are currently supported by PyDoctor:

.. table:: Consolidated Fields

    ==============================      ==============================
    Consolidated Field Tag              Corresponding Base Field Tag
    ==============================      ==============================
    ``:Parameters:``	                ``:param:``
    ``:Exceptions:``	                ``:except:``
    ``:Groups:``	                    ``:group:``
    ``:Keywords:``	                    ``:keyword:``
    ``:Variables:``	                    ``:var:``
    ``:IVariables:``	                ``:ivar:``
    ``:CVariables:``	                ``:cvar:``
    ``:Types:``	                        ``:type:``
    ==============================      ==============================

Case *insensitive*.

Directives
^^^^^^^^^^

Here is a list of the supported ReST directives by package of origin:

- `docutils`: ``.. include::``, ``.. contents::``, ``.. image::``, ``.. figure::``, ``.. unicode::``, ``.. raw::``, ``.. math::``, ``.. role::``, ``.. table::``, etc.
- `epydoc`: None
- `Sphinx`: None
- `pydoctor`: ``.. python::``.

Colorized snippets directive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using reStructuredText markup it is possible to specify Python snippets in a `doctest block <https://docutils.sourceforge.io/docs/user/rst/quickref.html#doctest-blocks>`_.

If the Python prompt gets in your way when you try to copy and paste and you are not interested in self-testing docstrings, the python directive will let you obtain a simple block of colorized text::

    .. python::

        def fib(n):
            """Print a Fibonacci series."""
            a, b = 0, 1
            while b < n:
                print b,
                a, b = b, a+b

.. note:: HTML Classes *restructuredtext* markup creates have a ``"rst-"`` prefix

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.
