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

from pydoctor import __version__ as version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.intersphinx",
    "pydoctor.sphinx_ext.build_apidocs",
    "sphinxcontrib.spelling",
    "sphinxarg.ext",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# Definitions that will be made available to every document.
rst_epilog = """
.. include:: <isonum.txt>
"""

# Configure spell checker.
spelling_word_list_filename = 'spelling_wordlist.txt'

# Configure intersphinx magic
intersphinx_mapping = {
    'twisted': ('https://twistedmatrix.com/documents/current/api/', None),
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
_common_args = [
    f'--html-viewsource-base=https://github.com/twisted/pydoctor/tree/{_git_reference}',
    f'--project-base-dir={_pydoctor_root}',
]
pydoctor_args = {
    'main': [
        '--html-output={outdir}/api/',  # Make sure to have a trailing delimiter for better usage coverage.
        '--project-name=pydoctor',
        f'--project-version={version}',
        '--docformat=epytext',
        '--project-url=../index.html',
        f'{_pydoctor_root}/pydoctor',
        ] + _common_args,
    'custom_template_demo': [
        '--html-output={outdir}/custom_template_demo/',
        '--project-name=pydoctor with a twisted theme',
        f'--project-version={version}',
        '--docformat=epytext',
        '--project-url=../customize.html',
        f'--template-dir={_pydoctor_root}/docs/sample_template',
        f'{_pydoctor_root}/pydoctor',
        ] + _common_args,
    'epydoc_demo': [
        '--html-output={outdir}/docformat/epytext',
        '--project-name=pydoctor-epytext-demo',
        '--project-version=1.3.0',
        '--docformat=epytext', 
        '--intersphinx=https://zopeschema.readthedocs.io/en/latest/objects.inv',
        '--intersphinx=https://zopeinterface.readthedocs.io/en/latest/objects.inv',
        '--project-url=../epytext.html',
        f'{_pydoctor_root}/docs/epytext_demo',
        ] + _common_args,
    'restructuredtext_demo': [
        '--html-output={outdir}/docformat/restructuredtext',
        '--project-name=pydoctor-restructuredtext-demo',
        '--project-version=1.0.0',
        '--docformat=restructuredtext',
        '--project-url=../restructuredtext.html',
        f'{_pydoctor_root}/docs/restructuredtext_demo',
        ] + _common_args,
    }

pydoctor_url_path = {
    'main': '/en/{rtd_version}/api',
    'epydoc_demo': '/en/{rtd_version}/docformat/epytext/',
    'restructuredtext_demo': '/en/{rtd_version}/docformat/restructuredtext/',
    }
