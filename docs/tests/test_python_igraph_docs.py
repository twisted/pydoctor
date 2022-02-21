#
# Run tests after python-igraph's documentation is executed.
#
# These tests are designed to be executed inside tox, after pydoctor is run.
# Alternatively this can be excuted manually from the project root folder like:
#   pytest docs/tests/test_python_igraph_docs.py

from . import get_toxworkdir_subdir

BASE_DIR = get_toxworkdir_subdir('python-igraph-output')

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
