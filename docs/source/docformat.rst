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

.. list-table:: Summary of supported and unsupported directives, with links to appropritate reference. 
   :header-rows: 1
   
   * - Directive
     - Reference
     - Support

   * - ``.. include::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#including-an-external-document-fragment>`_
     - Yes

   * - ``.. contents::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table-of-contents>`_
     - Yes

   * - ``.. image::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#image>`_
     - Yes
       
   * - ``.. |time| date:: %H:%M``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#date>`_
     - Yes

   * - ``.. figure::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#figure>`_
     - Yes

   * - ``.. |T| replace:: term``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#replacement-text>`_
     - Yes
 
   * - ``.. unicode::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#unicode-character-codes>`_
     - Yes
 
   * - ``.. raw::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#raw-data-pass-through>`_
     - Yes
  
   * - ``.. class::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#class>`_
     - Yes
  
   * - ``.. role::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#custom-interpreted-text-roles>`_
     - Yes
  
   * - ``.. default-role::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#setting-the-default-interpreted-text-role>`_
     - Yes
    
   * - ``.. line-block::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#line-block>`_
     - Yes

   * - ``.. code::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#code>`_
     - Yes (syntax highlight ignored)

   * - ``.. math::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#math>`_
     - Yes
    
   * - ``.. highlights::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#highlights>`_
     - Yes

   * - ``.. pull-quote::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#pull-quote>`_
     - Yes

   * - ``.. container::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#container>`_
     - Yes

   * - ``.. table::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table>`_
     - Yes

   * - ``.. csv-table::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#id4>`_
     - Yes

   * - ``.. list-table::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table>`_
     - Yes

   * - ``.. warning::`` and other abnomitions
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#specific-admonitions>`_
     - No 

   * - ``.. versionadded::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-versionadded>`_
     - No

   * - ``.. versionchanged::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-versionchanged>`_
     - No

   * - ``.. deprecated::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-deprecated>`_
     - No

   * - ``.. centered::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-centered>`_
     - No

   * - ``.. hlist::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-hlist>`_
     - No

   * - ``.. highlight::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-highlight>`_
     - No

   * - ``.. code-block::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-code-block>`_
     - No

   * - ``.. literalinclude::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-literalinclude>`_
     - No

   * - ``.. glossary::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-glossary>`_
     - No

   * - ``.. index::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-index>`_
     - No

   * - ``.. sectionauthor::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-sectionauthor>`_
     - No

   * - ``.. codeauthor::``
     - `ref (Sphinx) <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-codeauthor>`_
     - No

   * - ``.. topic::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#topic>`_
     - eh

   * - ``.. sidebar::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#sidebar>`_
     - No

   * - ``.. rubric::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#rubric>`_
     - eh

   * - ``.. epigraph::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#epigraph>`_
     - No

   * - ``.. compound::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#compound-paragraph>`_
     - eh
   
   * - ``.. sectnum::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#automatic-section-numbering>`_
     - No
 
   * - ``.. header::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#document-header-footer>`_
     - No
 
   * - ``.. footer::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#document-header-footer>`_
     - No
 
   * - ``.. meta::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#meta>`_
     - No
  
   * - ``.. title::``
     - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#metadata-document-title>`_
     - No


*This list is not exhaustive*

.. note:: HTML Classes *restructuredtext* markup creates have a ``"rst-"`` prefix

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.
