Google and Numpy
================

.. toctree::
    :maxdepth: 1
    
    google/google_demo
    numpy/numpy_demo


Docstrings will be first converted to reStructuredText and then parsed with ``docutils``. 
This means any supported `reST markup <restructuredtext.html>`_ can be use to supplement google-style or numpy-style markup. 

*Pydoctor* has forked and enhanced the `napoleon Sphinx extension 
<https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_.

For more information on syntax enhancements, 
refer to :py:mod:`pydoctor.napoleon` documentation. 

For markup details, refer to the `Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
or `NumpyDoc style <https://numpydoc.readthedocs.io/en/latest/format.html>`_ reference documentation. 

Sections
--------

List of supported sections:
    - ``Args``, ``Arguments``, ``Parameters``
    - ``Keyword Args``, ``Keyword Arguments``
    - ``Return(s)``, ``Yield(s)`` 
      (if you use type annotations a ``Returns`` section will always be present)
    - ``Raise(s)``, ``Warn(s)``
    - ``Attributes``
    - ``See Also``, ``See``
    - ``References``, ``Example(s)``, ``Usage``
    - ``Note(s)``,  ``Warning(s)`` and other admonitions

Sections supported on a "best effort" basis:
    - ``Methods``: Items will be included into a generic "Methods" admonition. 
    - ``Other Parameters``, ``Receive(s)``: Parameters described in those sections will be merged with regular parameters. 
    - Numpy-style multiple return section: elements will be listed but layout is sub optimal. 



.. ReST syntax violations might be reported with a slightly incorrect 
   line number because of this pre-processing. (uncommented this when pydoctor/issues/237 is solved)
