"""PyDoctor, an API documentation generator for Python libraries.

Warning: PyDoctor's API isn't stable YET, custom builds are prone to break!

"""
import importlib.metadata as importlib_metadata

__version__ = importlib_metadata.version('pydoctor')

__all__ = ["__version__"]
