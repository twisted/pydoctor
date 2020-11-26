
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
~~~~~~~~~~

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


Continue read in https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#
and https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#directives
