Documentation Formats
=====================

The following sections roughly documents the supported docstrings formatting. 

As an additional reference, small python packages demonstrates how docstrings are rendered. 

.. toctree::
    :maxdepth: 1

    epytext
    restructuredtext

To override the default markup language for a module, define a module-level string variable 
``__docformat__``, containing the name of the module's markup language.

Language code is ignored and parser name is lowercased::

    __docformat__ = "reStructuredText en"
    __docformat__ = "epytext"
