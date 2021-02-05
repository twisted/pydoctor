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
Advanced markup features such as type parsing, multiple return types or 
combined parameters are working just fine. 

Please refer to the `Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_
or `NumpyDoc style <https://numpydoc.readthedocs.io/en/latest/format.html>`_ reference documentation for markup details. 

Sections
--------

List of supported sections:
    - ``Args``, ``Arguments``, ``Parameters``, ``Receive(s)``, 
    - ``Keyword Args``, ``Keyword Arguments``
    - ``Return(s)``, ``Yield(s)`` 
      (if you use type annotations a ``Returns`` section will always be present)
    - ``Raise(s)``, ``Warn(s)``
    - ``See Also``, ``See``
    - ``References``, ``Example(s)``, ``Usage``
    - ``Note(s)``,  ``Warning(s)`` and other admonitions

Sections supported on a "best effort" basis:
    - ``Attributes``: Each item will be translated to ``:ivar:`` and ``:type:`` tags. 
    - ``Methods``: Items will be included into a "Methods" admonition. 
    - ``Other Parameters``: Parameters described in this section will be merged with regular parameters. 

For more informations, refer to py:mod:`pydoctor.napoleon` documentation. 

.. ReST syntax violations might be reported with a slightly incorrect 
   line number because of this pre-processing. (uncommented this when pydoctor/issues/237 is solved)
