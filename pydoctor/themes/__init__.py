"""
Package directory used to store pydoctor templates.

Usage example:

>>> template_lookup = TemplateLookup(importlib_resources.files('pydoctor.themes') / 'base')
"""
import sys
from typing import Iterator

# In newer Python versions, use importlib.resources from the standard library.
# On older versions, a compatibility package must be installed from PyPI.
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

def get_themes() -> Iterator[str]:
    """
    Get the list of the available themes.
    """
    for path in importlib_resources.files('pydoctor.themes').iterdir():
        if not path.name.startswith('_') and not path.is_file():
            yield path.name
