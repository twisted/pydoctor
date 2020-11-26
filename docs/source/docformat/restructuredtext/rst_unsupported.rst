
PyDoctor *restructuredtext* (Unsupported)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document is a technical working document designed to help improve ReST support for PyDoctor.  
It is not part of the main documentation.
It's designed for PyDoctor developers.

It lists some of the Unsupported fields of Directives. 

Even if it is not part of the main documentation, it has some demontrative value. 


topic
+++++

**Plain text**

::

    .. topic:: Topic Title

        Subsequent indented lines comprise
        the body of the topic, and are
        interpreted as body elements.

**Result**

.. topic:: Topic Title

    Subsequent indented lines comprise
    the body of the topic, and are
    interpreted as body elements.


compound
++++++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - :: 

        .. compound::

            The 'rm' command is very dangerous.  If you are logged
            in as root and enter ::

                cd /
                rm -rf *

            you will erase the entire contents of your file system.

    - .. compound::

            The 'rm' command is very dangerous.  If you are logged
            in as root and enter ::

                cd /
                rm -rf *

            you will erase the entire contents of your file system.


highlights
++++++++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - :: 

        .. highlights::

            - 1
            - 2
            - 3

    - .. highlights::

            - 1
            - 2
            - 3

..

pull-quote
++++++++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - :: 

        .. pull-quote::

            The legend consists of all elements after the caption.  In this
            case, the legend consists of this paragraph.

    - .. pull-quote::

            The legend consists of all elements after the caption.  In this
            case, the legend consists of this paragraph.

rubric
++++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - ::

        .. rubric:: rubric n. 1. a title, heading, or the like, 
            in a manuscript, book, statute, etc., written or printed 
            in red or otherwise distinguished from the rest of the text. ...

    - .. rubric:: rubric n. 1. a title, heading, or the like, 
            in a manuscript, book, statute, etc., written or printed 
            in red or otherwise distinguished from the rest of the text. ...

..

container
+++++++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - ::

        .. container:: custom

            This paragraph might be rendered in a custom way.

    - .. container:: custom

            This paragraph might be rendered in a custom way.

..

class
+++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - ::
  
        .. class:: special

            This is a "special" paragraph.
    
    - .. class:: special

            This is a "special" paragraph.

..

role
++++

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - ::

        .. role:: custom
            :class: code

        This is a "custom" code :custom:`interpreted text`

    -  .. role:: custom
            :class: code

        This is a "custom" code :custom:`interpreted text`

default-role
++++++++++++

  PYDOCTOR ALREADY REPLACE THE DEFAULT ROLE 

.. list-table:: 
  :header-rows: 1

  * - Plain text
    - Result
    
  * - ::

        .. default-role:: code

        An example of a `default` role.

    - .. default-role:: code

      An example of a `default` role.


Unsupported Directives
~~~~~~~~~~~~~~~~~~~~~~

header & footer
+++++++++++++++

.. header:: This space for rent.

.. footer:: License: MIT

meta
++++

.. meta::
   :description: This is PyDoctor
   :keywords: epytext, restructuredtext, docstring

title
+++++

.. title:: Just Testing Yay
