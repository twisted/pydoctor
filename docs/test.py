#
# Run tests after the documentation is executed.
#
# These tests are designed to be executed inside tox, after sphinx-build.
#
import os
import pathlib

from sphinx.ext.intersphinx import inspect_main

from pydoctor import __version__


BASE_DIR = pathlib.Path(os.environ.get('TOX_INI_DIR', os.getcwd())) / 'build' / 'docs'


def test_help_output_extension():
    """
    The help output extension will include the CLI help on the Sphinx page.
    """
    with open(BASE_DIR / 'help.html', 'r') as stream:
        page = stream.read()
        assert '--project-url=PROJECTURL' in page, page


def test_rtd_pydoctor_call():
    """
    With the pydoctor Sphinx extension, the pydoctor API HTML files are
    generated.
    """
    # The pydoctor index is generated and overwrites the Sphinx files.
    with open(BASE_DIR / 'api' / 'index.html', 'r') as stream:
        page = stream.read()
        assert 'moduleIndex.html' in page, page


def test_rtd_pydoctor_multiple_call():
    """
    With the pydoctor Sphinx extension can call pydoctor for more than one
    API doc source.
    """
    with open(BASE_DIR / 'docformat' / 'epytext' / 'index.html', 'r') as stream:
        page = stream.read()
        assert '<a href="../epytext.html" class="projecthome">pydoctor-epytext-demo</a>' in page, page


def test_rtd_extension_inventory():
    """
    The Sphinx inventory is available during normal sphinx-build.
    """
    with open(BASE_DIR / 'sphinx-integration.html', 'r') as stream:
        page = stream.read()
        assert 'href="/en/latest/api/pydoctor.sphinx_ext.build_apidocs.html"' in page, page


def test_sphinx_object_inventory_version(capsys):
    """
    The Sphinx inventory is generated with the project version in the header.
    """
    # The pydoctor own inventory.
    apidocs_inv = BASE_DIR / 'api' / 'objects.inv'
    with open(apidocs_inv, 'rb') as stream:
        page = stream.read()
        assert page.startswith(
            b'# Sphinx inventory version 2\n'
            b'# Project: pydoctor\n'
            b'# Version: ' + __version__.encode() + b'\n'
            ), page

    # Check that inventory can be parsed by Sphinx own extension.
    inspect_main([str(apidocs_inv)])
    out, err = capsys.readouterr()

    assert '' == err
    assert 'pydoctor.driver.main' in out, out


def test_sphinx_object_inventory_version_epytext_demo():
    """
    The Sphinx inventory for demo/showcase code has a fixed version and name,
    passed via docs/source/conf.py.
    """
    with open(BASE_DIR / 'docformat' / 'epytext' / 'objects.inv', 'rb') as stream:
        page = stream.read()
        assert page.startswith(
            b'# Sphinx inventory version 2\n'
            b'# Project: pydoctor-epytext-demo\n'
            b'# Version: 1.3.0\n'
            ), page


def test_index_contains_infos():
    """
    Test if index.html contains the following informations:

        - meta generator tag
        - nav and links to modules, classes, names
        - link to the root package
        - pydoctor github link in the footer
    """

    infos = (f'<meta name="generator" content="pydoctor {__version__}"', 
              '<nav class="navbar navbar-default mainnavbar"', 
              '<a href="moduleIndex.html"',
              '<a href="classIndex.html"',
              '<a href="nameIndex.html"',
              'Start at <code><a href="pydoctor.html">pydoctor</a></code>, the root package.',
              '<a href="https://github.com/twisted/pydoctor/">pydoctor</a>',)

    with open(BASE_DIR / 'api' / 'index.html', 'r', encoding='utf-8') as stream:
        page = stream.read()
        for i in infos:
            assert i in page, page

def test_page_contains_infos():
    """
    Test if pydoctor.driver.html contains the following informations:

        - meta generator tag
        - nav and links to modules, classes, names
        - js script source
        - pydoctor github link in the footer
    """

    infos = (f'<meta name="generator" content="pydoctor {__version__}"', 
              '<nav class="navbar navbar-default mainnavbar"', 
              '<a href="moduleIndex.html"',
              '<a href="classIndex.html"',
              '<a href="nameIndex.html"',
              '<script src="pydoctor.js" type="text/javascript"></script>',
              '<a href="https://github.com/twisted/pydoctor/">pydoctor</a>',)

    with open(BASE_DIR / 'api' / 'pydoctor.driver.html', 'r', encoding='utf-8') as stream:
        page = stream.read()
        for i in infos:
            assert i in page, page

def test_custom_template_contains_infos():
    """
    Test if the custom template index.html contains the following informations:

        - meta generator tag
        - nav and links to modules, classes, names
        - pydoctor github link in the footer
        - the custom header
        - link to teh extra.css
    """

    infos = (f'<meta name="generator" content="pydoctor {__version__}"', 
              '<nav class="navbar navbar-default mainnavbar"', 
              '<a href="moduleIndex.html"',
              '<a href="classIndex.html"',
              '<a href="nameIndex.html"',
              '<a href="https://github.com/twisted/pydoctor/">pydoctor</a>',
              '<img src="https://twistedmatrix.com/trac/chrome/common/trac_banner.png" alt="Twisted" />',
              '<link rel="stylesheet" type="text/css" href="extra.css" />',)

    with open(BASE_DIR / 'custom_template_demo' / 'index.html', 'r', encoding='utf-8') as stream:
        page = stream.read()
        for i in infos:
            assert i in page, page

def test_meta_pydoctor_template_version_tag_gets_removed():
    """
    Test if the index.html effectively do not contains the meta pydoctor template version tag
    """
    with open(BASE_DIR / 'api' / 'index.html', 'r', encoding='utf-8') as stream:
        page = stream.read()
        assert '<meta name="pydoctor-template-version" content="' not in page, page
