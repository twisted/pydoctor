Google and Numpy
================

.. toctree::
    :maxdepth: 1
    
    google/google_demo
    numpy/numpy_demo

Pydoctor now supports numpydoc and google style docstrings!

Docstrings will be first converted to reStructuredText and then parsed with ``docutils``. 
Any supported `reST markup <restructuredtext.html>`_ can be use to supplement google-style or numpy-style markup. 

The main difference between the two styles is that Google uses indentation to separate sections, 
whereas NumPy uses underlines. This means that 2 blank lines are needed to end a NumPy section 
that is followed by a regular paragraph (i.e. not another section header)

.. note:: Pydoctor* has forked and enhanced the `napoleon Sphinx extension 
    <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_.

    For more information, refer to :py:mod:`pydoctor.napoleon` documentation. 

For complete markup details, refer to the `Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
or `NumpyDoc style <https://numpydoc.readthedocs.io/en/latest/format.html>`_ reference documentation. 


Sections
--------

List of supported sections:
    - ``Args``, ``Arguments``, ``Parameters``
    - ``Keyword Args``, ``Keyword Arguments``
    - ``Return(s)``, ``Yield(s)`` 
      (if you use type annotations a ``Returns`` section will always be present)
    - ``Raise(s)``, ``Warn(s)``
    - ``See Also``, ``See``
    - ``Example(s)``, ``Usage``
    - ``Note(s)``,  ``Warning(s)`` and other admonitions

Sections supported on a "best effort" basis:
    - ``Methods``: Items will be included into a generic "Methods" section. 
    - ``Attributes``: Items will be translated into ``ivar`` fields.
    - ``References``: Rendered as a generic section. 
    - ``Other Parameters``, ``Receive(s)``: Parameters described in those sections will be merged with regular parameters. 

.. ReST syntax violations might be reported with a slightly incorrect 
   line number because of this pre-processing. (uncommented this when pydoctor/issues/237 is solved)
