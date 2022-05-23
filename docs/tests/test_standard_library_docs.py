#
# Run tests after Python standard library's documentation is executed.
#
# These tests are designed to be executed inside tox, after pydoctor is run.
# Alternatively this can be excuted manually from the project root folder like:
#   pytest docs/tests/test_standard_library_docs.py

from . import get_toxworkdir_subdir

PYTHON_DIR = get_toxworkdir_subdir('cpython')
BASE_DIR = get_toxworkdir_subdir('cpython-output')

def test_std_lib_docs() -> None:
    """
    For each top-level module in python standard library, check if there is an associated documentation page.
    """
    for entry in PYTHON_DIR.joinpath('Lib').iterdir():
        if entry.is_file() and entry.suffix=='.py': # Module
            name = entry.name[0:-3]
            if name == "__init__": continue
            assert BASE_DIR.joinpath('Lib.'+name+'.html').exists()
        
        elif entry.is_dir() and entry.joinpath('__init__.py').exists(): # Package
            assert BASE_DIR.joinpath('Lib.'+entry.name+'.html').exists()

    
