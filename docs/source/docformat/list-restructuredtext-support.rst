:orphan:

List of ReST directives
=======================

.. list-table:: List of ReST directives and status whether they are supported or unsupported by PyDoctor
   :header-rows: 1
   
   * - Directive
     - Defined by
     - Supported

   * - ``.. include::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#including-an-external-document-fragment>`__
     - Yes

   * - ``.. contents::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table-of-contents>`__
     - Yes

   * - ``.. image::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#image>`__
     - Yes
       
   * - ``.. |time| date:: %H:%M``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#date>`__
     - Yes

   * - ``.. figure::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#figure>`__
     - Yes

   * - ``.. |T| replace:: term``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#replacement-text>`__
     - Yes
 
   * - ``.. unicode::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#unicode-character-codes>`__
     - Yes
 
   * - ``.. raw::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#raw-data-pass-through>`__
     - Yes
  
   * - ``.. class::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#class>`__
     - No
  
   * - ``.. role::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#custom-interpreted-text-roles>`__
     - Yes
  
   * - ``.. default-role::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#setting-the-default-interpreted-text-role>`__
     - Should not be changed. 
    
   * - ``.. line-block::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#line-block>`__
     - No

   * - ``.. code::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#code>`__
     - Yes
   
   * - ``.. python::``
     - pydoctor
     - Yes

   * - ``.. math::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#math>`__
     - Yes
    
   * - ``.. highlights::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#highlights>`__
     - No

   * - ``.. pull-quote::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#pull-quote>`__
     - No

   * - ``.. container::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#container>`__
     - Yes

   * - ``.. table::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table>`__
     - Yes

   * - ``.. csv-table::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#id4>`__
     - Yes

   * - ``.. list-table::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#list-table>`__
     - Yes

   * - ``.. warning::`` and other admonitions
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#specific-admonitions>`__
     - Yes. This includes: attention, caution, danger, error, hint, important, note, tip, warning and the generic admonitions. 

   * - ``.. versionadded::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-versionadded>`__
     - No

   * - ``.. versionchanged::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-versionchanged>`__
     - No

   * - ``.. deprecated::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-deprecated>`__
     - No

   * - ``.. centered::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-centered>`__
     - No

   * - ``.. digraph::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#digraph_directive>`__
     - No

   * - ``.. classtree::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#classtree_directive>`__
     - No

   * - ``.. packagetree::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#package_directive>`__
     - No

   * - ``.. importgraph::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#importgraph_directive>`__
     - No

   * - ``.. callgraph::``
     - `epydoc <http://epydoc.sourceforge.net/api/epydoc.markup.restructuredtext-module.html#callgraph_directive>`__
     - No

   * - ``.. hlist::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-hlist>`__
     - No

   * - ``.. highlight::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-highlight>`__
     - No

   * - ``.. code-block::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-code-block>`__
     - No

   * - ``.. literalinclude::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-literalinclude>`__
     - No

   * - ``.. glossary::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-glossary>`__
     - No

   * - ``.. index::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-index>`__
     - No

   * - ``.. sectionauthor::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-sectionauthor>`__
     - No

   * - ``.. codeauthor::``
     - `Sphinx <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-codeauthor>`__
     - No

   * - ``.. topic::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#topic>`__
     - No

   * - ``.. sidebar::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#sidebar>`__
     - No

   * - ``.. rubric::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#rubric>`__
     - No

   * - ``.. epigraph::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#epigraph>`__
     - No

   * - ``.. compound::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#compound-paragraph>`__
     - No
   
   * - ``.. sectnum::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#automatic-section-numbering>`__
     - No
 
   * - ``.. header::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#document-header-footer>`__
     - No
 
   * - ``.. footer::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#document-header-footer>`__
     - No
 
   * - ``.. meta::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#meta>`__
     - No
  
   * - ``.. title::``
     - `docutils <https://docutils.sourceforge.io/docs/ref/rst/directives.html#metadata-document-title>`__
     - No


*This list is not exhaustive*
