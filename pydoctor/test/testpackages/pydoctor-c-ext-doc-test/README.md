Build instructions
==================

$ python -m venv .venv
$ .venv/bin/pip install cython pydoctor
$ .venv/bin/python setup.py build_ext --inplace
$ .venv/bin/pydoctor --introspect-c-modules mymodule
