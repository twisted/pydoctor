Documentation Formats
=====================

Epytext Support
---------------

`epytext syntax reference <http://epydoc.sourceforge.net/manual-epytext.html>`_

The Epytext support has been herited from the ``epydoc`` software. So all markup should work. Except ``X{}`` tag, which has been removed. 

As a reminder, the following fields are supported::

    @author
    @cvar
    @ivar
    @note
    @param (synonym: @arg)
    @raise (synonym: @raises)
    @return (synonym: @returns)
    @rtype (synonym: @returntype)
    @see (synonym: @seealso)
    @type
    @var

ReStructuredText Support
------------------------

`RST syntax reference <https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html>`_

.. important::

    - Abnomitions are not supported yet: ``.. warning::``, ``.. note::``, etc.

    - Other directives like ``.. contents::`` and ``.. include::`` are working just fine !

    (Full list of supported and unsupported ReStructuredText markup to come)

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.
