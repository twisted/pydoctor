# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import os
import subprocess
import pathlib


# -- Project information -----------------------------------------------------

project = 'pydoctor'
copyright = '2020, Michael Hudson-Doyle and various contributors (see Git history)'
author = 'Michael Hudson-Doyle and various contributors (see Git history)'

from pydoctor._version import __version__
version = __version__.short()

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.intersphinx",
    "pydoctor.sphinx_ext._help_output",
    "pydoctor.sphinx_ext.build_apidocs",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# Configure intersphinx magic
intersphinx_mapping = {
    'twisted': ('https://twistedmatrix.com/documents/current/api/', None),
    'pydoctor': ('https://pydoctor.readthedocs.io/en/latest/api/', None),
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# Try to find URL fragment for the GitHub source page based on current
# branch or tag.
_git_reference = subprocess.getoutput('git rev-parse --abbrev-ref HEAD')
if _git_reference == 'HEAD':
    # It looks like the branch has no name.
    # Fallback to commit ID.
    _git_reference = subprocess.getoutput('git rev-parse HEAD')

if os.environ.get('READTHEDOCS', '') == 'True':
    rtd_version = os.environ.get('READTHEDOCS_VERSION', '')
    if '.' in rtd_version:
        # It looks like we have a tag build.
        _git_reference = rtd_version

_pydoctor_root = pathlib.Path(__file__).parent.parent.parent
pydoctor_args = [
    f'--add-package={_pydoctor_root}/pydoctor',
    '--html-output={outdir}/api',
    f'--project-base-dir={_pydoctor_root}',
    f'--html-viewsource-base=https://github.com/twisted/pydoctor/tree/{_git_reference}',
    '--quiet',
    '--make-html',
    '--project-name=pydoctor',
    '--project-url=https://github.com/twisted/pydoctor/',
    '--docformat=epytext',
    '--intersphinx=https://docs.python.org/3/objects.inv',
    '--intersphinx=https://twistedmatrix.com/documents/current/api/objects.inv',
    '--intersphinx=https://urllib3.readthedocs.io/en/latest/objects.inv',
    '--intersphinx=https://requests.readthedocs.io/en/latest/objects.inv',
    ]
