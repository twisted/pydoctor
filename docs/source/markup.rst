Documentation Formats
=====================

Epytext Support
---------------

Find the syntax reference `HERE <http://epydoc.sourceforge.net/manual-epytext.html>`_

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

Find the syntax reference `HERE <https://docutils.sourceforge.io/rst.html>`_

.. important::

    The following fields are **NOT supported yet**:

    - Abnomitions: ``.. warning::``, ``.. note::`` and others... :/ 

.. note:: In any case, *plaintext* docformat will be used if docstings can't be parsed with *restructuredtext* parser.  