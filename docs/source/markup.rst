Documentation Formats
=====================

Epytext Support
---------------

`Syntax reference <http://epydoc.sourceforge.net/manual-epytext.html>`_

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

`Syntax reference <https://docutils.sourceforge.io/rst.html>`_

.. important::

    The following fields are **NOT supported yet**:

    - Abnomitions: ``.. warning::``, ``.. note::`` and others... 
    
    (Full list of supported and unsupported ReStructuredText markup to come)

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.  