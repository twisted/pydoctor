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

See `fields section <codedoc.rst#fields>`__.

.. note:: Not everything from the `epydoc fields manual
    <http://epydoc.sourceforge.net/manual-fields.html>`_ is applicable.
    Some fields might still display as unknown.

.. note:: In any case, *plaintext* docstring format will be used if docstrings can't be parsed with *epytext* parser.
