
PyDoctor *restructuredtext* quick ref
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document is a technical working document designed to help improve ReST support for PyDoctor.  
It is not part of the main documentation.
It's designed for PyDoctor developers.

It lists supported directives and link to the appropritate documentation, then demonstrate a few usages. 

Even if it is not part of the main documentation, it has some demontrative value. 

List of ReST directives
^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: List of ReST directives and status whether they are supported or unsupported by PyDoctor
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

.. contents:: Table of Contents

Fields
^^^^^^

author
++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     
   * - :: 
  
          :author: Michael Hudson-Doyle

seealso
+++++++

Synonym: 
  - ``:see:``

.. list-table:: 
   :header-rows: 1

   * - Docstring
     
   * - :: 

          :seealso: `PyDoctor <https://github.com/twisted/pydoctor>`_, an API documentation 
            generator that works by static analysis.

parameters
++++++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring

   * - :: 

          :Parameters:
              - `size`: The size of the fox (in meters)
              - `weight` (float) The weight of the fox (in stones)
              - `age` (int) The age of the fox (in years)
          :rtype: str
          :return: The number of foxes

   * - :: 
  
          :Parameters:
              size
                  The size of the fox (in meters)
              weight : float
                  The weight of the fox (in stones)
              age : int
                  The age of the fox (in years)
          :rtype: str
          :return: The number of foxes
          
   * - ::

          :param size: The size of the fox (in meters)
          :param weight: The weight of the fox (in stones)
          :param age: The age of the fox (in years)
          :type weight: float
          :type age: age
          :rtype: str
          :return: The number of foxes

Directives
^^^^^^^^^^

line-block
++++++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - :: 

        .. line-block::
            Subsequent indented lines comprise
            the body of the sidebar, and are
            interpreted as body elements.
    
     - .. line-block::
            Subsequent indented lines comprise
            the body of the sidebar, and are
            interpreted as body elements.
   * - :: 

        | But can a bee be said to be
        |     or not to be an entire bee,
        |         when half the bee is not a bee,
        |             due to some ancient injury?

     -
        | But can a bee be said to be
        |     or not to be an entire bee,
        |         when half the bee is not a bee,
        |             due to some ancient injury?

code
++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output

   * - ::
    
        .. python:: 

            def hey(**kargs):
                '''
                Do something.
                :Parameters:
                    size
                        The size of the fox (in meters)
                :rtype: str
                :return: The number of foxes
                '''
                pass

     - .. python:: 

        def hey(**kargs):
            '''
            Do something.
            :Parameters:
                size
                    The size of the fox (in meters)
            :rtype: str
            :return: The number of foxes
            '''
            pass

math
++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - :: 

        .. math::

        α_t(i) = P(O_1, O_2, … O_t, q_t = S_i λ)

     - .. math::

        α_t(i) = P(O_1, O_2, … O_t, q_t = S_i λ)

raw
+++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - :: 

        .. raw:: html

            <hr />

     - .. raw:: html

            <hr />

figure & image
++++++++++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - :: 

        .. figure:: https://khms1.googleapis.com/kh?v=878&hl=en-US&x=2273&y=3006&z=13

            This is the caption of the figure (a simple paragraph).

            The legend consists of all elements after the caption.  In this
            case, the legend consists of this paragraph.

     - .. figure:: https://khms1.googleapis.com/kh?v=878&hl=en-US&x=2273&y=3006&z=13

            This is the caption of the figure (a simple paragraph).

            The legend consists of all elements after the caption.  In this
            case, the legend consists of this paragraph.

tables
++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - ::

            .. table:: Truth table for "not"
                :widths: auto

                ==========  ==========
                A           not A
                ==========  ==========
                False       True
                True        False
                ==========  ==========
    
     -  .. table:: Truth table for "not"
            :widths: auto

            ==========  ==========
            A           not A
            ==========  ==========
            False       True
            True        False
            ==========  ==========

   * - ::

        .. csv-table:: Frozen Delights!
            :header: "Treat", "Quantity", "Description"
            :widths: 15, 10, 30

            "Albatross", 2.99, "On a stick!"
            "Crunchy Frog", 1.49, "If we took the bones out, it wouldn't be
            crunchy, now would it?"
            "Gannet Ripple", 1.99, "On a stick!"

     - .. csv-table:: Frozen Delights!
            :header: "Treat", "Quantity", "Description"
            :widths: 15, 10, 30

            "Albatross", 2.99, "On a stick!"
            "Crunchy Frog", 1.49, "If we took the bones out, it wouldn't be
            crunchy, now would it?"
            "Gannet Ripple", 1.99, "On a stick!"
     
   * - ::

        .. list-table:: Summary of supported and unsupported directives, 
                with links to appropritate reference. 
            :header-rows: 1
            
            * - Directive
              - Reference
              - Support

            * - ``.. pull-quote::``
              - `ref (docutils) <>`_
              - Yes

            * - ``.. compound::``
              - `ref (docutils) <>`_
              - eh

            * - ``.. container::``
              - `ref (docutils) <>`_
              - Yes

            * - ``.. table::``
              - `ref (docutils) <>`_
              - Yes

     - .. list-table:: Summary of supported and unsupported directives, with links to appropritate reference. 
            :header-rows: 1
            
            * - Directive
              - Reference
              - Support

            * - ``.. pull-quote::``
              - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#pull-quote>`_
              - Yes

            * - ``.. compound::``
              - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#compound-paragraph>`_
              - eh

            * - ``.. container::``
              - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#container>`_
              - Yes

            * - ``.. table::``
              - `ref (docutils) <https://docutils.sourceforge.io/docs/ref/rst/directives.html#table>`_
              - Yes

date
++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - ::

        .. |date| date::
        .. |time| date:: %H:%M

        Today's date is |date|.

        This document was generated on |date| at |time|.

     -  .. |date| date::
        .. |time| date:: %H:%M

        Today's date is |date|.

        This document was generated on |date| at |time|.

replace
+++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - ::

        I recommend you try |Python|_.

        .. |Python| replace:: Python, *the* best language around
        .. _Python: http://www.python.org/
     
     - I recommend you try |Python|_.

        .. |Python| replace:: Python, *the* best language around
        .. _Python: http://www.python.org/

unicode
+++++++

.. list-table:: 
   :header-rows: 1

   * - Docstring
     - Output
     
   * - ::
   
        Copyright |copy| 2003, |BogusMegaCorp (TM)| |---|
        all rights reserved.

        .. |copy| unicode:: 0xA9 .. copyright sign
        .. |BogusMegaCorp (TM)| unicode:: BogusMegaCorp U+2122
        .. with trademark sign
        .. |---| unicode:: U+02014 .. em dash
            :trim:
    
     - Copyright |copy| 2003, |BogusMegaCorp (TM)| |---|
        all rights reserved.

        .. |copy| unicode:: 0xA9 .. copyright sign
        .. |BogusMegaCorp (TM)| unicode:: BogusMegaCorp U+2122
        .. with trademark sign
        .. |---| unicode:: U+02014 .. em dash
            :trim:


Continue read in https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html
and https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#directives
