Documentation Formats
=====================

The following sections roughly documents the supported docstrings formatting.

As an additional reference, small python packages demonstrates how docstrings are rendered.

.. toctree::
    :maxdepth: 1

    epytext
    restructuredtext

To override the default markup language for a module, define a module-level string variable 
``__docformat__``, containing the name of the module's markup language::

    __docformat__ = "reStructuredText"
    __docformat__ = "Epytext"

.. note:: Language code can be added. It is currently ignored, though it might be used it 
    the future to generate ``lang`` attribute in HTML or as configuration for a spell checker::

        __docformat__ = "reStructuredText en"

Parser name and language code are **case insensitve**.

The docformat value are inherited from packages if a ``__docformat__`` variable is defined in 
the ``__init__.py`` file.
