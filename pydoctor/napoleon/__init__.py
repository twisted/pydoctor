"""
Convert docstrings from numpy or google style format to reST. 

This package is a fork of U{sphinx.ext.napoleon 
<https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html?highlight=napoleon_custom_sections#module-sphinx.ext.napoleon>} 
adapted for C{pydoctor} usage. 

Supports both U{Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>} 
and U{NumpyDoc <https://numpydoc.readthedocs.io/en/latest/format.html>} docstrings. 

No settings are supported in this version.

**Type parsing**

All types will pre-processed and links will be automtically created. 
See L{TypeSpecDocstring} for more informations. 

**Numpy-style returns clause**

Allow users who have type annotations in their pure python code to omit 
types in the returns clause docstrings but as well as specify them when it's needed. 

All of the following return clauses will be interpreted as expected::

    Returns
    -------
    Description of return value

    Returns
    -------
    subprocess.Popen
        Description of return value

    Returns
    -------
    list[str]

See: U{sphinx/issues/7077 <https://github.com/sphinx-doc/sphinx/issues/7077>} 

Note: This comes with a little issue: in the case of a natural language 
    type like C{"list of int"}, it needs a follow-up indented description 
    in order to be recognized as type:: 
        Returns
        -------
        list of str
            Description of the list

@note: Napoleon U{upstream  
    <https://github.com/sphinx-doc/sphinx/pulls?q=is%3Apr+napoleon>}
    should be checked once in a while to make sure we don't miss any important updates. 

@copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
@license: BSD, see LICENSE for details.
"""
