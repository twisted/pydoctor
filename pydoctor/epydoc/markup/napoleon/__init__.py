"""
This package is a fork (`commit 
<https://github.com/sphinx-doc/sphinx/commit/f9968594206e538f13fa1c27c065027f10d4ea27>`_) 
of `sphinx.ext.napoleon <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html?highlight=napoleon_custom_sections#module-sphinx.ext.napoleon>`_ 
adapted for the pydoctor usage. 

Support only `Google style`_ docstrings for now. 

.. _Google style:
    https://google.github.io/styleguide/pyguide.html

Not all settings are supported in this version. 

@note: Sphinx license::

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from typing import Dict, Iterable, Tuple, Union
import attr

@attr.s(auto_attribs=True)
class Config:
    """
    Supported Napoleon config values. 
    """
    # config values 

    napoleon_use_param:bool = True
    """
    (Defaults to True)
    True to use a ``:param:`` role for each function parameter. False to
    use a single ``:parameters:`` role for all the parameters.
    This `NumPy style`_ snippet will be converted as follows::
        Parameters
        ----------
        arg1 : str
            Description of `arg1`
        arg2 : int, optional
            Description of `arg2`, defaults to 0
    **If True**::
        :param arg1: Description of `arg1`
        :type arg1: str
        :param arg2: Description of `arg2`, defaults to 0
        :type arg2: int, optional
    **If False**::
        :parameters: * **arg1** (*str*) --
                        Description of `arg1`
                     * **arg2** (*int, optional*) --
                        Description of `arg2`, defaults to 0
    """
    napoleon_use_rtype:bool = True
    """
    (Defaults to True)
    True to use the ``:rtype:`` role for the return type. False to output
    the return type inline with the description.
    This `NumPy style`_ snippet will be converted as follows::
        Returns
        -------
        bool
            True if successful, False otherwise
    **If True**::
        :returns: True if successful, False otherwise
        :rtype: bool
    **If False**::
        :returns: *bool* -- True if successful, False otherwise
    """

    napoleon_use_keyword:bool = True
    """
    (Defaults to True)
    True to use a ``:keyword:`` role for each function keyword argument.
    False to use a single ``:keyword arguments:`` role for all the
    keywords.
    This behaves similarly to  :attr:`napoleon_use_param`. Note unlike
    docutils, ``:keyword:`` and ``:param:`` will not be treated the same
    way - there will be a separate "Keyword Arguments" section, rendered
    in the same fashion as "Parameters" section (type links created if
    possible)
    See Also
    --------
    :attr:`napoleon_use_param`

    """
    napoleon_custom_sections:Iterable[Union[str, Tuple[str, str]]] = None
    """
    (Defaults to None)
    Add a list of custom sections to include, expanding the list of parsed sections.
    The entries can either be strings or tuples, depending on the intention:
        * To create a custom "generic" section, just pass a string.
        * To create an alias for an existing section, pass a tuple containing the
        alias name and the original, in that order.
    If an entry is just a string, it is interpreted as a header for a generic
    section. If the entry is a tuple/list/indexed container, the first entry
    is the name of the section, the second is the section key to emulate.
    """
