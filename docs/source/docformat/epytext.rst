Epytext
=======

.. toctree::
    :maxdepth: 1

    epytext/epytext_demo

Read the `the epytext manual <http://epydoc.sourceforge.net/manual-epytext.html>`_
for full documentation.

Pydoctor has extended ``epydoc``'s parser and uses it as a
library to parse epytext formatted docstrings.

All markup should work except the indexed terms ``X{}`` tag, which has been removed.

Fields
------

Here are the supported *epytext* fields:

    - ``@cvar foo:``
    - ``@ivar foo:``
    - ``@var foo:``
    - ``@note:``
    - ``@param bar:`` (synonym: ``@arg bar:``)
    - ``@type bar: C{list}``
    - ``@return:`` (synonym: ``@returns:``)
    - ``@rtype:`` (synonym: ``@returntype:``)
    - ``@raise ValueError:`` (synonym: ``@raises ValueError:``)
    - ``@see:`` (synonym: ``@seealso:``)
    - And more

.. note:: Not everything from the `epydoc fields manual
    <http://epydoc.sourceforge.net/manual-fields.html>`_ is applicable.
    Some fields might still display as unknown.

