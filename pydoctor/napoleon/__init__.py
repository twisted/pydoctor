"""
Convert docstrings from numpy or google style format to reST. 

`This package is a fork of U{sphinx.ext.napoleon 
<https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html?highlight=napoleon_custom_sections#module-sphinx.ext.napoleon>} 
(U{commit 
<https://github.com/sphinx-doc/sphinx/commit/f9968594206e538f13fa1c27c065027f10d4ea27>})
adapted for the ``pydoctor`` usage. 

Supports both U{Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>} 
and U{NumpyDoc <https://numpydoc.readthedocs.io/en/latest/format.html>} docstrings. 

Not all settings are supported in this version. 

There is also a new setting: C{napoleon_numpy_returns_allow_free_from}. See L{Config} for more informations. 

@note: Original package license::

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from typing import Dict, Iterable, Mapping, Optional, Tuple, Union
import attr

@attr.s(auto_attribs=True)
class Config:
    """
    Supported Napoleon config values. 
    """

    napoleon_numpy_returns_allow_free_from: bool = False
    """
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
        subprocess.Popen

    For more discussion: U{sphinx/issues/7077 <https://github.com/sphinx-doc/sphinx/issues/7077>} 

    @note: This come with a little issue: in the case of a natural language 
       type like C{"list of int"}, it needs a follow-up indented description 
       in order to be recognized as type:: 
           Returns
           -------
           list of str
                Description of the list
    """


    napoleon_custom_sections: Optional[Iterable[Union[str, Tuple[str, str]]]] = None
    """
    Add a list of custom sections to include, expanding the list of parsed sections.
    The entries can either be strings or tuples, depending on the intention:

        - To create a custom "generic" section, just pass a string.
        - To create an alias for an existing section, pass a tuple containing the
        alias name and the original, in that order.

    If an entry is just a string, it is interpreted as a header for a generic
    section. If the entry is a tuple/list/indexed container, the first entry
    is the name of the section, the second is the section key to emulate.
    """

    napoleon_type_aliases: Optional[Mapping[str, str]] = None
    """
    A mapping to translate type names to other names or references. 
    *Defaults to None.*

    With::

        napoleon_type_aliases = {
            "CustomType": "mypackage.CustomType",
            "dict-like": "Mapping",
        }

    This NumPy style snippet::

        Parameters
        ----------
        arg1 : CustomType
            Description of `arg1`
        arg2 : dict-like
            Description of `arg2`

    becomes::

        :param arg1: Description of `arg1`
        :type arg1: `mypackage.CustomType`
        :param arg2: Description of `arg2`
        :type arg2: `Mapping`

   """