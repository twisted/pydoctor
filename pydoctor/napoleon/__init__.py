"""
This package is a fork of U{sphinx.ext.napoleon 
<https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html?highlight=napoleon_custom_sections#module-sphinx.ext.napoleon>} 
(U{commit 
<https://github.com/sphinx-doc/sphinx/commit/f9968594206e538f13fa1c27c065027f10d4ea27>}))
adapted for the pydoctor usage. 

Supports only U{Google style <https://google.github.io/styleguide/pyguide.html>} docstrings for now. 

Not all settings are supported in this version. 

@note: Original package license::

    :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from typing import Dict, Iterable, Optional, Tuple, Union
import attr

@attr.s(auto_attribs=True)
class Config:
    """
    Supported Napoleon config values. 
    """

    napoleon_custom_sections:Optional[Iterable[Union[str, Tuple[str, str]]]] = None
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
