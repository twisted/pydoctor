Google and Numpy
================

.. toctree::
    :maxdepth: 1
    
    google/google_demo
    numpy/numpy_demo

Pydoctor now support `Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
and `NumpyDoc style <https://numpydoc.readthedocs.io/en/latest/format.html>`_  docstrings. 

Docstrings will be first converted to reStructuredText and then parsed with ``docutils``. 
This means any supported `reST markup <restructuredtext>`_ can be use to supplement google-style or numpy-style markup. 

Please refer to the appropriate references documentation for markup details. 

Sections
--------

List of supported sections:
    - ``Args``, ``Arguments``, ``Parameters``, ``Receive(s)``, ``Other Parameters``
    - ``Keyword Args``, ``Keyword Arguments``
    - ``Return(s)``, ``Yield(s)`` 
      (if you use type annotations a ``Returns`` section will always be present)
    - ``Raise(s)``, ``Warn(s)``
    - ``See Also``, ``See``
    - ``Attributes``, ``Methods``, ``References``, ``Example(s)``, ``Usage``
    - ``Note(s)``,  ``Warning(s)`` and other admonitions

.. note:: 
   Pydoctor has forked the `napoleon Sphinx extension 
   <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_.  

   ReST syntax violations might be reported with a slightly incorrect 
   line number because of this pre-processing. 
