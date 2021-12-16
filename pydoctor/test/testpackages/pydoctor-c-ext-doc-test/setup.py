from setuptools import setup
from Cython.Build import cythonize

setup(
    name="PyDoctor Epydoc linking test",
    ext_modules=cythonize("mymodule/base_class.pyx"),
    zip_safe=False
)
