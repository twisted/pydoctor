#
# Run tests after the documentation is executed.
#
# These tests are designed to be executed inside tox, after sphinx-build.
#
import os
import pathlib
from pydoctor import __version__


BASE_DIR = pathlib.Path(os.environ.get('TOX_INI_DIR', os.getcwd())) / 'build' / 'docs'
API_DIR = BASE_DIR / 'api'


def test_help_output_extension():
    """
    The help output extension will include the CLI help on the Sphinx page.
    """
    with open(BASE_DIR / 'help.html', 'r') as stream:
        assert '--project-url=PROJECTURL' in stream.read()


def test_rtd_pydoctor_call():
    """
    With the pydoctor Sphinx extension, the pydoctor API HTML files are
    generated.
    """
    # The pydoctor index is generated and overwrites the Sphinx files.
    with open(API_DIR / 'index.html', 'r') as stream:
        assert 'moduleIndex.html' in stream.read()


def test_rtd_pydoctor_multiple_call():
    """
    With the pydoctor Sphinx extension can call pydoctor for more than one
    API doc source.
    """
    with open(BASE_DIR / 'docformat' / 'epytext' / 'demo' / 'index.html', 'r') as stream:
        assert 'pydoctor-epytext-demo API Documentation' in stream.read()


def test_rtd_extension_inventory():
    """
    The Sphinx inventory is available during normals sphinx-build.
    """
    with open(BASE_DIR / 'usage.html', 'r') as stream:
        data = stream.read()
        assert 'href="/en/latest/api/pydoctor.sphinx_ext.build_apidocs.html"' in data, data


def test_sphinx_object_inventory_version():
    """
    The Sphinx inventory is generated with the project version in the header.
    """
    # The pydoctor own invetory.
    with open(BASE_DIR / 'objects.inv', 'rb') as stream:
        data = stream.read()
        assert data.startswith(
            b'# Sphinx inventory version 2\n'
            b'# Project: pydoctor\n'
            b'# Version: ' + __version__.encode() + b'\n'
            ), data

    # The demo/showcase inventor for which we have a fixed version.
    with open(BASE_DIR / 'docformat' / 'epytext' / 'demo' / 'objects.inv', 'rb') as stream:
        data = stream.read()
        assert data.startswith(
            b'# Sphinx inventory version 2\n'
            b'# Project: pydoctor-epytext-demo\n'
            b'# Version: 1.2.0\n'
            ), data
