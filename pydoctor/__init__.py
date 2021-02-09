"""PyDoctor, an API documentation generator for Python libraries.

Warning: PyDoctor's API isn't stable YET, custom builds are prone to break!

"""

from typing import TYPE_CHECKING

# On Python 3.8+, use importlib.metadata from the standard library.
# On older versions, a compatibility package can be installed from PyPI.
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    if not TYPE_CHECKING:
        import importlib_metadata


__version__ = importlib_metadata.version('pydoctor')

__all__ = ["__version__"]
