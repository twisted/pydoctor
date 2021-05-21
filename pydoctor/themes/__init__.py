"""
Package directory used to store pydoctor templates.

Usage example:

>>> template_lookup = TemplateLookup(importlib_resources.files('pydoctor.themes') / 'base')
"""
import sys
from typing import Iterator

# On Python 3.7+, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 7):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

def get_themes() -> Iterator[str]:
    """
    Get the list of the available themes.
    """
    for name in importlib_resources.contents('pydoctor.themes'):
        if (not name.startswith('_') and not
            importlib_resources.is_resource('pydoctor.themes', name)) :
            yield name
