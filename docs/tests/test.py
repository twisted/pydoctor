#
# Run tests after the documentation is executed.
#
# These tests are designed to be executed inside tox, after sphinx-build.
#
import os
import pathlib
from typing import List
import xml.etree.ElementTree as ET
import json

from lunr.index import Index

from sphinx.ext.intersphinx import inspect_main

from pydoctor import __version__


BASE_DIR = pathlib.Path(os.environ.get('TOX_INI_DIR', os.getcwd())) / 'build' / 'docs'


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
    with open(BASE_DIR / 'docformat' / 'epytext_demo' / 'index.html', 'r') as stream:
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
    with open(BASE_DIR / 'docformat' / 'epytext_demo' / 'objects.inv', 'rb') as stream:
        page = stream.read()
        assert page.startswith(
            b'# Sphinx inventory version 2\n'
            b'# Project: pydoctor-epytext-demo\n'
            b'# Version: 1.3.0\n'
            ), page


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

def test_incons_get_copied():
    """
    Test if the icons the fonts directory get copid to the ouput folder

    Incons from https://primer.style/octicons/
    """

    assert (BASE_DIR / 'api' / 'fonts' / 'info.svg').is_file()
    assert (BASE_DIR / 'api' / 'fonts' / 'x-circle.svg').is_file()

def test_search_index_generated():
    """
    Test if the icons the fonts directory get copid to the ouput folder

    Incons from https://primer.style/octicons/
    """

    assert (BASE_DIR / 'api' / 'searchindex.json').is_file()
    assert (BASE_DIR / 'api' / 'fullsearchindex.json').is_file()
    assert (BASE_DIR / 'api' / 'all-documents.html').is_file()

def test_lunr_index() -> None:
    """
    Run some searches on the lunr index to test it's validity. 
    """

    with (BASE_DIR / 'api' / 'searchindex.json').open() as fobj:
        index_data = json.load(fobj)
        index = Index.load(index_data)

        def test_search(query:str, expected:List[str], order_is_important:bool=True) -> None:
            if order_is_important:
                assert [r["ref"] for r in index.search(query)] == expected
            else:
                assert sorted([r["ref"] for r in index.search(query)]) == sorted(expected)

        test_search('+qname:pydoctor', ['pydoctor'])
        test_search('+qname:pydoctor.epydoc2stan', ['pydoctor.epydoc2stan'])
        test_search('_colorize_re_pattern', ['pydoctor.epydoc.markup._pyval_repr.PyvalColorizer._colorize_re_pattern'])
        
        test_search('+name:Class', 
            ['pydoctor.model.Class', 
             'pydoctor.factory.Factory.Class',
             'pydoctor.model.DocumentableKind.CLASS',
             'pydoctor.model.System.Class'])
        
        to_stan_results = [
                    'pydoctor.epydoc.markup.ParsedDocstring.to_stan', 
                    'pydoctor.epydoc.markup.plaintext.ParsedPlaintextDocstring.to_stan',
                    'pydoctor.epydoc.markup._types.ParsedTypeDocstring.to_stan',
                    'pydoctor.epydoc.markup._pyval_repr.ColorizedPyvalRepr.to_stan',
                    'pydoctor.epydoc2stan.ParsedStanOnly.to_stan'
                ]
        test_search('to_stan*', to_stan_results, order_is_important=False)
        test_search('to_stan', to_stan_results, order_is_important=False)

        to_node_results = [
                    'pydoctor.epydoc.markup.ParsedDocstring.to_node', 
                    'pydoctor.epydoc.markup.plaintext.ParsedPlaintextDocstring.to_node',
                    'pydoctor.epydoc.markup._types.ParsedTypeDocstring.to_node',
                    'pydoctor.epydoc.markup.restructuredtext.ParsedRstDocstring.to_node',
                    'pydoctor.epydoc.markup.epytext.ParsedEpytextDocstring.to_node',
                    'pydoctor.epydoc2stan.ParsedStanOnly.to_node'
                ]
        test_search('to_node*', to_node_results, order_is_important=False)
        test_search('to_node', to_node_results, order_is_important=False)
        
        test_search('qname:pydoctor.epydoc.markup.restructuredtext.ParsedRstDocstring', 
                ['pydoctor.epydoc.markup.restructuredtext.ParsedRstDocstring'])
        test_search('pydoctor.epydoc.markup.restructuredtext.ParsedRstDocstring', 
                ['pydoctor.epydoc.markup.restructuredtext.ParsedRstDocstring'])

def test_pydoctor_test_is_hidden():
    """
    Test that option --privacy=HIDDEN:pydoctor.test makes everything under pydoctor.test HIDDEN.
    """

    def getText(node: ET.Element) -> str:
        return ''.join(node.itertext()).strip()

    with open(BASE_DIR / 'api' / 'all-documents.html', 'r', encoding='utf-8') as stream:
        document = ET.fromstring(stream.read())
        for liobj in document.findall('body/div/ul/li[@id]'):
            
            if not str(liobj.get("id")).startswith("pydoctor"):
                continue # not a all-documents list item, maybe in the menu or whatever.
            
            # figure obj name
            fullName = getText(liobj.findall('./div[@class=\'fullName\']')[0])
            
            if fullName.startswith("pydoctor.test"):
                # figure obj privacy
                privacy = getText(liobj.findall('./div[@class=\'privacy\']')[0])
                # check that it's indeed private
                assert privacy == 'HIDDEN'

def test_missing_subclasses():
    """
    Test for missing subclasses of ParsedDocstring, issue https://github.com/twisted/pydoctor/issues/528.
    """

    infos = ('pydoctor.epydoc.markup._types.ParsedTypeDocstring', 
        'pydoctor.epydoc.markup.epytext.ParsedEpytextDocstring', 
        'pydoctor.epydoc.markup.plaintext.ParsedPlaintextDocstring', 
        'pydoctor.epydoc.markup.restructuredtext.ParsedRstDocstring', 
        'pydoctor.epydoc2stan.ParsedStanOnly')

    with open(BASE_DIR / 'api' / 'pydoctor.epydoc.markup.ParsedDocstring.html', 'r', encoding='utf-8') as stream:
        page = stream.read()
        for i in infos:
            assert i in page, page
