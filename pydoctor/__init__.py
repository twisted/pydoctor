"""PyDoctor, an API documentation generator for Python libraries.

Warning:
    PyDoctor's own API isn't stable YET, custom builds are prone to break!

`Return to main documentation <https://mfesiem.github.io/pydoctor/index.html>`_

"""

__docformat__ = "restructuredtext en"

__all__ = ["__version__"]

from ._version import __version__


def _setuptools_version() -> str:
    return __version__.public() # type: ignore[no-any-return]
