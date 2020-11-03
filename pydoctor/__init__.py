"""PyDoctor, an API documentation generator for Python libraries.

Warning:
    PyDoctor's API isn't stable YET, custom builds are prone to break!

"""

__docformat__ = "restructuredtext en"

__all__ = ["__version__"]

from ._version import __version__


def _setuptools_version() -> str:
    return __version__.public() # type: ignore[no-any-return]
