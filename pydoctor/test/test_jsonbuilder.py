from pydoctor.test import CapSys
from pydoctor.test.test_astbuilder import fromText
from pydoctor import jsonbuilder, docspec, visitor

def test_dump_module(capsys: CapSys) -> None:
    
    mod = fromText('''
    class C:
        def method_undecorated():
            pass

        @staticmethod
        def method_static():
            pass

        @classmethod
        def method_class(cls):
            pass

        @staticmethod
        @classmethod
        def method_both():
            pass
    ''', modname='mod')

    serializer = jsonbuilder.JSONSerializer()

    serializer.processModule(mod)

    assert len(serializer.modules_spec) == 1
    docspec_mod = serializer.modules_spec.pop()
    
    visitor.walk(docspec_mod, docspec.PrintVisitor(), 
        get_children=lambda ob: getattr(ob, 'members', []))
        
    captured = capsys.readouterr().out

    assert captured.strip() == """mod:14: mod.C.method_both is both classmethod and staticmethod
:0 - Module (MODULE): mod 
| :2 - Class (CLASS): mod.C 
| | :3 - Function (METHOD): mod.C.method_undecorated 
| | :6 - Function (STATIC_METHOD): mod.C.method_static 
| | :10 - Function (CLASS_METHOD): mod.C.method_class 
| | :14 - Function (METHOD): mod.C.method_both"""

def test_dump_system(capsys: CapSys) -> None:

    mod = fromText('''
    class C:
        def method_undecorated():
            pass

        @staticmethod
        def method_static():
            pass

        @classmethod
        def method_class(cls):
            pass

        @staticmethod
        @classmethod
        def method_both():
            pass
    ''', modname='mod')

    data = jsonbuilder.dump_system(mod.system)
    data['options'] = {}
    data['buildtime'] = '2017-02-15T20:26:08.937881'
    assert data == {
                'buildtime': '2017-02-15T20:26:08.937881',
                'options': {},
                'projectname': 'my project',
                'rootobjects': [{'docstring': None,
                                'kind': 'MODULE',
                                'location': {'filename': '',
                                            'lineno': 0},
                                'members': [{'bases': [],
                                            'decorators': None,
                                            'docstring': None,
                                            'kind': 'CLASS',
                                            'location': {'filename': '',
                                                            'lineno': 2},
                                            'members': [{'args': [],
                                                            'decorators': None,
                                                            'docstring': None,
                                                            'kind': 'METHOD',
                                                            'location': {'filename': '',
                                                                        'lineno': 3},
                                                            'modifiers': [],
                                                            'name': 'method_undecorated',
                                                            'return_type': None,
                                                            'type': 'function'},
                                                        {'args': [],
                                                            'decorators': ['staticmethod\n'],
                                                            'docstring': None,
                                                            'kind': 'STATIC_METHOD',
                                                            'location': {'filename': '',
                                                                        'lineno': 6},
                                                            'modifiers': [],
                                                            'name': 'method_static',
                                                            'return_type': None,
                                                            'type': 'function'},
                                                        {'args': [{'name': 'cls',
                                                                    'type': 'POSITIONAL_OR_KEYWORD'}],
                                                            'decorators': ['classmethod\n'],
                                                            'docstring': None,
                                                            'kind': 'CLASS_METHOD',
                                                            'location': {'filename': '',
                                                                        'lineno': 10},
                                                            'modifiers': [],
                                                            'name': 'method_class',
                                                            'return_type': None,
                                                            'type': 'function'},
                                                        {'args': [],
                                                            'decorators': ['staticmethod\n',
                                                                        'classmethod\n'],
                                                            'docstring': None,
                                                            'kind': 'METHOD',
                                                            'location': {'filename': '',
                                                                        'lineno': 14},
                                                            'modifiers': [],
                                                            'name': 'method_both',
                                                            'return_type': None,
                                                            'type': 'function'}],
                                            'name': 'C',
                                            'type': 'class'}],
                                'name': 'mod'}],
                'sourcebase': None,
            }
    
    data2 = jsonbuilder.dump_system(jsonbuilder.load_system(data))
    data2['options'] = {}
    assert data2 == data
