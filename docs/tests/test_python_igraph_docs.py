#
# Run tests after python-igraph's documentation is executed.
#
# These tests are designed to be executed inside tox, after bin/admin/build-apidocs.
#

import pathlib
import os

BASE_DIR = pathlib.Path(os.environ.get('TOX_WORK_DIR', os.getcwd())) / 'python-igraph-output'

def test_python_igraph_docs() -> None:
    """
    Test for https://github.com/twisted/pydoctor/issues/287
    """

    with open(BASE_DIR / 'igraph.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in ['href="igraph._igraph.html"']), page

    with open(BASE_DIR / 'igraph.Graph.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in ['href="igraph._igraph.GraphBase.html"']), page

    with open(BASE_DIR / 'igraph._igraph.GraphBase.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in ['href="igraph.Graph.html"']), page
