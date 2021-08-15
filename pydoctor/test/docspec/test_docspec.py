from pathlib import Path
from pydoctor.test import CapSys

from pydoctor import docspec

def test_load_simple_module() -> None:

    here = Path(__file__).parent

    docspec_mod = docspec.load_module((here / 'testjsonfiles' / 'simple.json').open('r'))

    assert isinstance(docspec_mod, docspec.Module)
    assert docspec_mod.kind is docspec.ApiObject.Kind.MODULE
    assert docspec_mod.docstring == 'summary'

    test = docspec.get_member(docspec_mod, 'test') 
    assert isinstance(test, docspec.Data)
    assert test.kind is docspec.ApiObject.Kind.VARIABLE
    assert test.docstring == 'summary'
    assert test.datatype == 'Union[str, bytes]'
    assert test.value == '"1"'

def test_visitor(capsys: CapSys) -> None:
    
    here = Path(__file__).parent

    docspec_mod = docspec.load_module((here / 'testjsonfiles' / 'long.json').open('r'))

    assert isinstance(docspec_mod, docspec.Module)

    visitor = docspec.PrintVisitor()
    docspec_mod.walk(visitor)
    captured = capsys.readouterr().out
    assert captured == """test.py:1 - Module (MODULE): mod (doc: 'summary')
| test.py:1 - Data (VARIABLE): mod.test (doc: 'summary')
| test.py:2 - Data (VARIABLE): mod.test2 (doc: 'summary2')
| test.py:3 - Data (VARIABLE): mod.test3 (doc: 'summary3')
"""
    
    predicate = lambda ob: ob.name not in ['test2']
    filter_visitor = docspec.FilterVisitor(predicate)
    docspec_mod.walk(filter_visitor)
    docspec_mod.walk(visitor)
    captured = capsys.readouterr().out
    assert captured == """test.py:1 - Module (MODULE): mod (doc: 'summary')
| test.py:1 - Data (VARIABLE): mod.test (doc: 'summary')
| test.py:3 - Data (VARIABLE): mod.test3 (doc: 'summary3')
"""

def test_load_function(capsys: CapSys) -> None:
    
    here = Path(__file__).parent

    docspec_mod = docspec.load_module((here / 'testjsonfiles' / 'function.json').open('r'))

    assert isinstance(docspec_mod, docspec.Module)

    visitor = docspec.PrintVisitor()
    docspec_mod.walk(visitor)
    captured = capsys.readouterr().out
    assert captured == """test.py:1 - Module (MODULE): mod (doc: 'summary')
| test.py:1 - Function (FUNCTION): mod.test (doc: 'summary')
"""

