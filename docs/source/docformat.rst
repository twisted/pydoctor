Documentation Formats
=====================

Epytext Support
---------------

Read the `epytext syntax reference <http://epydoc.sourceforge.net/manual-epytext.html>`_.

The Epytext support has been herited from the ``epydoc`` software. So all markup should work. Except ``X{}`` tag, which has been removed. 

Fields
^^^^^^

As a reminder, here are some of the supported *epytext* fields:

    - ``@cvar foo:``
    - ``@ivar foo:``
    - ``@var foo:``
    - ``@note``
    - ``@param bar:`` (synonym: ``@arg bar:``)
    - ``@type bar: C{list}``
    - ``@return:`` (synonym: ``@returns:``)
    - ``@rtype:`` (synonym: ``@returntype:``)
    - ``@raise ValueError:`` (synonym: ``@raises ValueError:``)
    - ``@see:`` (synonym: ``@seealso:``)
    - And more

ReStructuredText Support
------------------------

Install PyDoctor with *restructuredtext* support::

   $ pip install -U pydoctor docutils

Read the `RST syntax reference <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_.

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

.. list-table:: Supported and unsupported directives
   :header-rows: 1
   
   * - Directive
     - Support

   * - ``.. include::``
     
     - Yes

   * - ``.. contents::``
     
     - Yes

   * - ``.. image::``
     
     - Yes
    
   * - ``.. warning::``
     
     - No. This include support for other abnomitions like ``note``, ``attention``, ``important``, etc

   * - ``.. versionadded::``
     
     - No

   * - ``.. versionchanged::``
     
     - No

   * - ``.. deprecated::``
     
     - No

   * - ``.. centered::``
     
     - ?

   * - ``.. hlist::``
     
     - ?

   * - ``.. highlight::``
     
     - ?

   * - ``.. code-block::``
     
     - ?

   * - ``.. literalinclude::``
     
     - ?

   * - ``.. glossary::``
     
     - ?

   * - ``.. index::``
     
     - ?

   * - ``.. sectionauthor::``
     
     - ?

   * - ``.. codeauthor::``
     
     - ?

   * - ``.. figure::``
     
     - ?

   * - ``.. topic::``
     
     - ?

   * - ``.. sidebar::``
     
     - ?

   * - ``.. line-block::``
     
     - ?

   * - ``.. code::``
     
     - ?

   * - ``.. math::``
     
     - ?

   * - ``.. rubric::``
     
     - ?

   * - ``.. epigraph::``
     
     - ?

   * - ``.. highlights::``
     
     - ?

   * - ``.. pull-quote::``
     
     - ?

   * - ``.. compound::``
     
     - ?

   * - ``.. container::``
     
     - ?

   * - ``.. table::``
     
     - ?

   * - ``.. csv-table::``
     
     - ?

   * - ``.. list-table::``
     
     - ?
 
   * - ``.. sectnum::``
     
     - ?
 
   * - ``.. header::``
     
     - ?
 
   * - ``.. footer::``
     
     - ?
 
   * - ``.. meta::``
     
     - ?
 
   * - ``.. |time| date:: %H:%M``
     
     - ?
 
   * - ``.. |RST| replace:: restructuredtext``
     
     - ?
 
   * - ``.. unicode::``
     
     - ?
 
   * - ``.. raw::``
     
     - ?
  
   * - ``.. class::``
     
     - ?
  
   * - ``.. role::``
     
     - ?
  
   * - ``.. default-role::``
     
     - ?
  
   * - ``.. title::``
     
     - ?
  
   * - ``.. restructuredtext-test-directive::``
     
     - ?

*This list is not exhaustive*

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.
