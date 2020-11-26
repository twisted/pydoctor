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

``pydoctor`` needs the following packages to offer *restructuredtext* support::

   $ pip install -U docutils Pygments

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

Here is a list of the supported ReST directives by package of origin:

- `docutils`: ``.. include::``, ``.. contents::``, ``.. image::``, ``.. figure::``, ``.. unicode::``, ``.. raw::``, ``.. math::``, etc
- `epydoc`: None
- `Sphinx`: None
- `pydoctor`: ``.. python::``, 

Reference
^^^^^^^^^

`Read the PyDoctor ReST Reference <rst.html>`_

List
^^^^

.. list-table:: 
   :header-rows: 1
   
   * - Directive
     - Defined by
     - Supported

   * - ``.. include::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#including-an-external-document-fragment>`_
     - Yes

   * - ``.. contents::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table-of-contents>`_
     - Yes

   * - ``.. image::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#image>`_
     - Yes
       
   * - ``.. |time| date:: %H:%M``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#date>`_
     - Yes

   * - ``.. figure::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#figure>`_
     - Yes

   * - ``.. |T| replace:: term``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#replacement-text>`_
     - Yes
 
   * - ``.. unicode::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#unicode-character-codes>`_
     - Yes
 
   * - ``.. raw::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#raw-data-pass-through>`_
     - Yes
  
   * - ``.. class::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#class>`_
     - eh
  
   * - ``.. role::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#custom-interpreted-text-roles>`_
     - Yes
  
   * - ``.. default-role::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#setting-the-default-interpreted-text-role>`_
     - Yes
    
   * - ``.. line-block::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#line-block>`_
     - eh

   * - ``.. code::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#code>`_
     - No. Use ``.. python::``. 
   
   * - ``.. python::``
     - pydoctor
     - Yes

   * - ``.. math::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#math>`_
     - Yes
    
   * - ``.. highlights::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#highlights>`_
     - eh

   * - ``.. pull-quote::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#pull-quote>`_
     - eh

   * - ``.. container::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#container>`_
     - Yes

   * - ``.. table::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table>`_
     - Yes

   * - ``.. csv-table::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#id4>`_
     - Yes

   * - ``.. list-table::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table>`_
     - Yes

   * - ``.. warning::`` and other abnomitions
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#specific-admonitions>`_
     - No 

   * - ``.. versionadded::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-versionadded>`_
     - No

   * - ``.. versionchanged::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-versionchanged>`_
     - No

   * - ``.. deprecated::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-deprecated>`_
     - No

   * - ``.. centered::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-centered>`_
     - No

   * - ``.. digraph::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#digraph_directive>`_
     - No

   * - ``.. classtree::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#classtree_directive>`_
     - No

   * - ``.. packagetree::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#package_directive>`_
     - No

   * - ``.. importgraph::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#importgraph_directive>`_
     - No

   * - ``.. callgraph::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#callgraph_directive>`_
     - No

   * - ``.. hlist::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-hlist>`_
     - No

   * - ``.. highlight::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-highlight>`_
     - No

   * - ``.. code-block::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-code-block>`_
     - No

   * - ``.. literalinclude::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-literalinclude>`_
     - No

   * - ``.. glossary::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-glossary>`_
     - No

   * - ``.. index::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-index>`_
     - No

   * - ``.. sectionauthor::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-sectionauthor>`_
     - No

   * - ``.. codeauthor::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-codeauthor>`_
     - No

   * - ``.. topic::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#topic>`_
     - eh

   * - ``.. sidebar::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#sidebar>`_
     - No

   * - ``.. rubric::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#rubric>`_
     - eh

   * - ``.. epigraph::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#epigraph>`_
     - No

   * - ``.. compound::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#compound-paragraph>`_
     - eh
   
   * - ``.. sectnum::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#automatic-section-numbering>`_
     - No
 
   * - ``.. header::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#document-header-footer>`_
     - No
 
   * - ``.. footer::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#document-header-footer>`_
     - No
 
   * - ``.. meta::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#meta>`_
     - No
  
   * - ``.. title::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#metadata-document-title>`_
     - No


*This list is not exhaustive*

.. note:: HTML Classes *restructuredtext* markup creates have a ``"rst-"`` prefix

.. note:: In any case, *plaintext* docformat will be used if docstrings can't be parsed with *restructuredtext* parser.

.. PyDoctor *restructuredtext* quick ref
.. ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. *In construction*

.. `Visit the PyDoctor ReST Quick Reference <https://tristanlatr.github.io/pydoctor/rst-quick-ref/>`_
