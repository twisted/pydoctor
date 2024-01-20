# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'test-sphinx-ext'
copyright = '2023, Contributors'
author = 'Contributors'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []
templates_path = []
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = []

# ----------------------------------------------------------------------------
# Test configuration for pydoctor.sphinx_ext.build_apidocs

from pathlib import Path
extensions.append("pydoctor.sphinx_ext.build_apidocs")

_testpackages = Path(__file__).parent.parent.parent.joinpath('testpackages')

pydoctor_args = [
    '--project-name=test-sphinx-ext-api',
    f'--project-version={release}',
    '--docformat=epytext',
    '--intersphinx=https://docs.python.org/3/objects.inv',
    '--html-output={outdir}/api',
    f'{_testpackages / "report_trigger"}',
    f'{_testpackages / "epytext_syntax_error"}',
    ]