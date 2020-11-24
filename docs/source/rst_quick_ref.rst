
PyDoctor *restructuredtext* quick ref
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document is a working draft for a *restructuredtext* demo page that would introduce 
users to PyDoctor output and specifications. 

.. contents:: Table of Contents

Fields
~~~~~~

author
++++++

.. list-table:: 
   :header-rows: 1

   * - Plain text
     
   * - :: 
  
          :author: Michael Hudson-Doyle

seealso
+++++++

Synonym: 
  - ``:see:``

.. list-table:: 
   :header-rows: 1

   * - Plain text
     
   * - :: 

          :seealso: `PyDoctor <https://github.com/twisted/pydoctor>`_, an API documentation 
            generator that works by static analysis.

parameters
++++++++++

.. list-table:: 
   :header-rows: 1

   * - Plain text
     
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

..

  and others
  ++++++++++

  :group Docstring Processing: markup
  :group Miscellaneous: util, test

  :author: `Edward Loper <edloper@gradient.cis.upenn.edu>`__
  :requires: Python 2.3+
  :version: 3.0.1
  :see: `The epydoc webpage <http://epydoc.sourceforge.net>`__
  :see: `The epytext markup language manual <http://epydoc.sourceforge.net/epytext.html>`__

  :todo: Create a better default top_page than trees.html.
  :todo: Fix trees.html to work when documenting non-top-levelmodules/packages
  :todo: Implement @include
  :todo: Optimize epytext
  :todo: More doctests
  :todo: When introspecting, limit how much introspection you do (eg, don't construct docs for imported modules' vars if it's not necessary)

  :bug: UserDict.* is interpreted as imported .. why??

  :license: IBM Open Source License
  :copyright: |copy| 2006 Edward Loper

  :newfield contributor: Contributor, Contributors (Alphabetical Order)
  :contributor: `Glyph Lefkowitz  <mailto:glyph@twistedmatrix.com>`__
  :contributor: `Edward Loper  <mailto:edloper@gradient.cis.upenn.edu>`__
  :contributor: `Bruce Mitchener  <mailto:bruce@cubik.org>`__
  :contributor: `Jeff O'Halloran  <mailto:jeff@ohalloran.ca>`__
  :contributor: `Simon Pamies  <mailto:spamies@bipbap.de>`__
  :contributor: `Christian Reis  <mailto:kiko@async.com.br>`__
  :contributor: `Daniele Varrazzo  <mailto:daniele.varrazzo@gmail.com>`__
  :contributor: `Jonathan Guyer <mailto:guyer@nist.gov>`__

  .. |copy| unicode:: 0xA9 .. copyright sign

Directives
~~~~~~~~~~

line-block
++++++++++

.. list-table:: 
   :header-rows: 1

   * - Plain text
     - Result
     
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

   * - Plain text
     - Result

   * - ::
    
        .. code:: python

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

     - .. code:: python

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

   * - Plain text
     - Result
     
   * - :: 

        .. math::

        α_t(i) = P(O_1, O_2, … O_t, q_t = S_i λ)

     - .. math::

        α_t(i) = P(O_1, O_2, … O_t, q_t = S_i λ)

raw
+++

.. list-table:: 
   :header-rows: 1

   * - Plain text
     - Result
     
   * - :: 

        .. raw:: html

            <hr />

     - .. raw:: html

            <hr />

figure & image
++++++++++++++

.. list-table:: 
   :header-rows: 1

   * - Plain text
     - Result
     
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

   * - Plain text
     - Result
     
   * - ::

            .. table:: Truth table for "not"
                :widths: auto

                =====  =====
                A      not A
                =====  =====
                False  True
                True   False
                =====  =====
    
     -  .. table:: Truth table for "not"
            :widths: auto

            =====  =====
            A      not A
            =====  =====
            False  True
            True   False
            =====  =====

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

   * - Plain text
     - Result
     
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

   * - Plain text
     - Result
     
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

   * - Plain text
     - Result
     
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


Continue read in https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#
and https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#directives
