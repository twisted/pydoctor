import os
import pathlib
from typing import List
import xml.etree.ElementTree as ET
import json

from pydoctor import __version__

BASE_DIR = pathlib.Path(os.environ.get('TOX_INI_DIR', os.getcwd())) / 'build' / 'test-sphinx-ext'

def test_rtd_pydoctor_call():
    """
    With the pydoctor Sphinx extension, the pydoctor API HTML files are
    generated.
    """
    # The pydoctor index is generated and overwrites the Sphinx files.
    with open(BASE_DIR / 'api' / 'index.html', 'r') as stream:
        page = stream.read()
        assert 'moduleIndex.html' in page, page