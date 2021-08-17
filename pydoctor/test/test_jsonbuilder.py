from pydoctor.test import CapSys
from pydoctor.test.test_astbuilder import fromText
from pydoctor import jsonbuilder, docspec, visitor, model

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
    
    docspec_mod.walk(docspec.PrintVisitor())

    captured = capsys.readouterr().out

    assert captured.strip() == """mod:14: mod.C.method_both is both classmethod and staticmethod
:0 - Module (MODULE): mod 
| :2 - Class (CLASS): mod.C 
| | :3 - Function (METHOD): mod.C.method_undecorated 
| | :6 - Function (STATIC_METHOD): mod.C.method_static 
| | :10 - Function (CLASS_METHOD): mod.C.method_class 
| | :14 - Function (METHOD): mod.C.method_both"""

def test_dump_system(capsys: CapSys) -> None:
    systemcls = model.System
    system = systemcls()
    pack = fromText('''
    """regular module docstring

    @var b: doc for b
    """

    __docformat__ = 'epytext'
    __all__ = ['C']
    class C:
        """regular class docstring"""

        d = None
        """inline doc for d"""

        f = None
        """inline doc for f"""

        def __init__(self):
            self.a = 1
            """inline doc for a"""

            """not a docstring"""

            self._b = 2
            """inline doc for _b"""

            x = -1
            """not a docstring"""

            self.c = 3
            """inline doc for c"""

            self.d = 4

            self.e = 5
        """not a docstring"""

        def f():
            """duplicate name"""
            pass

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
    
    class Base:
        def base_method():
            """Base method docstring."""

    class Sub(Base):
        def sub_method():
            """Sub method docstring."""

        def __init__(self):
            self.base_method = wrap_method(self.base_method)
            """Overriding the docstring is not supported."""
            self.sub_method = wrap_method(self.sub_method)
            """Overriding the docstring is not supported."""

    ''', modname='pack', is_package=True, system=system)
    mod_b = fromText('''
    def f(): pass
    ''', modname='b', parent_name='pack', system=system)
    mod_c = fromText('''
    from pack import b
    f = b.f
    ''', modname='c', system=system)

    data = system.dump()
    assert data is not None
    data['buildtime'] = '2017-02-15T20:26:08.937881'
    assert data == {
    'buildtime': '2017-02-15T20:26:08.937881',
    'docformat': 'epytext',
    'htmlsourcebase': None,
    'intersphinx': [],
    'projectbasedirectory': 'None',
    'projectname': 'my project',
    'projecturl': None,
    'projectversion': '',
    'rootobjects': [{'all': ['C'],
                    'docformat': 'epytext',
                    'docstring': 'regular module docstring\n'
                                '\n'
                                '@var b: doc for b',
                    'kind': 'PACKAGE',
                    'location': {'filename': '',
                                'lineno': 0},
                    'members': [{'docformat': 'epytext',
                                'docstring': None,
                                'kind': 'MODULE',
                                'location': {'filename': '',
                                                'lineno': 0},
                                'members': [{'args': [],
                                                'decorators': None,
                                                'docstring': None,
                                                'kind': 'FUNCTION',
                                                'location': {'filename': '',
                                                            'lineno': 2},
                                                'modifiers': [],
                                                'name': 'f',
                                                'return_type': None,
                                                'type': 'function'}],
                                'name': 'b',
                                'type': 'module'},
                                {'bases': [],
                                'decorators': None,
                                'docstring': 'regular class docstring',
                                'kind': 'CLASS',
                                'location': {'filename': '',
                                                'lineno': 9},
                                'members': [{'datatype': 'int\n',
                                                'docstring': 'inline doc for d',
                                                'kind': 'INSTANCE_VARIABLE',
                                                'location': {'filename': '',
                                                            'lineno': 12},
                                                'name': 'd',
                                                'type': 'data'},
                                            {'args': [],
                                                'decorators': None,
                                                'docstring': 'duplicate name',
                                                'kind': 'METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 38},
                                                'modifiers': [],
                                                'name': 'f',
                                                'return_type': None,
                                                'type': 'function'},
                                            {'args': [{'name': 'self',
                                                        'type': 'POSITIONAL_OR_KEYWORD'}],
                                                'decorators': None,
                                                'docstring': None,
                                                'kind': 'METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 18},
                                                'modifiers': [],
                                                'name': '__init__',
                                                'return_type': None,
                                                'type': 'function'},
                                            {'datatype': 'int\n',
                                                'docstring': 'inline doc for a',
                                                'kind': 'INSTANCE_VARIABLE',
                                                'location': {'filename': '',
                                                            'lineno': 19},
                                                'name': 'a',
                                                'type': 'data'},
                                            {'datatype': 'int\n',
                                                'docstring': 'inline doc for _b',
                                                'kind': 'INSTANCE_VARIABLE',
                                                'location': {'filename': '',
                                                            'lineno': 24},
                                                'name': '_b',
                                                'type': 'data'},
                                            {'datatype': 'int\n',
                                                'docstring': 'inline doc for c',
                                                'kind': 'INSTANCE_VARIABLE',
                                                'location': {'filename': '',
                                                            'lineno': 30},
                                                'name': 'c',
                                                'type': 'data'},
                                            {'datatype': 'int\n',
                                                'docstring': None,
                                                'kind': 'INSTANCE_VARIABLE',
                                                'location': {'filename': '',
                                                            'lineno': 35},
                                                'name': 'e',
                                                'type': 'data'},
                                            {'args': [],
                                                'decorators': None,
                                                'docstring': None,
                                                'kind': 'METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 42},
                                                'modifiers': [],
                                                'name': 'method_undecorated',
                                                'return_type': None,
                                                'type': 'function'},
                                            {'args': [],
                                                'decorators': ['staticmethod\n'],
                                                'docstring': None,
                                                'kind': 'STATIC_METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 45},
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
                                                            'lineno': 49},
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
                                                            'lineno': 53},
                                                'modifiers': [],
                                                'name': 'method_both',
                                                'return_type': None,
                                                'type': 'function'}],
                                'name': 'C',
                                'type': 'class'},
                                {'bases': [],
                                'decorators': None,
                                'docstring': None,
                                'kind': 'CLASS',
                                'location': {'filename': '',
                                                'lineno': 58},
                                'members': [{'args': [],
                                                'decorators': None,
                                                'docstring': 'Base method '
                                                            'docstring.',
                                                'kind': 'METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 59},
                                                'modifiers': [],
                                                'name': 'base_method',
                                                'return_type': None,
                                                'type': 'function'}],
                                'name': 'Base',
                                'type': 'class'},
                                {'bases': ['Base'],
                                'decorators': None,
                                'docstring': None,
                                'kind': 'CLASS',
                                'location': {'filename': '',
                                                'lineno': 62},
                                'members': [{'args': [],
                                                'decorators': None,
                                                'docstring': 'Sub method '
                                                            'docstring.',
                                                'kind': 'METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 63},
                                                'modifiers': [],
                                                'name': 'sub_method',
                                                'return_type': None,
                                                'type': 'function'},
                                            {'args': [{'name': 'self',
                                                        'type': 'POSITIONAL_OR_KEYWORD'}],
                                                'decorators': None,
                                                'docstring': None,
                                                'kind': 'METHOD',
                                                'location': {'filename': '',
                                                            'lineno': 66},
                                                'modifiers': [],
                                                'name': '__init__',
                                                'return_type': None,
                                                'type': 'function'}],
                                'name': 'Sub',
                                'type': 'class'}],
                    'name': 'pack'},
                    {'docstring': None,
                    'kind': 'MODULE',
                    'location': {'filename': '',
                                'lineno': 0},
                    'members': [{'docstring': None,
                                'kind': 'INDIRECTION',
                                'location': {'filename': '',
                                                'lineno': 0},
                                'name': 'b',
                                'type': 'data',
                                'value': 'pack.b'},
                                {'docstring': None,
                                'kind': 'INDIRECTION',
                                'location': {'filename': '',
                                                'lineno': 0},
                                'name': 'f',
                                'type': 'data',
                                'value': 'pack.b.f'}],
                    'name': 'c'}]
    }
    
    system2 = systemcls()
    system2.load(data)
    data2 = system2.dump()
    assert data2 is not None
    assert sorted(data2) == sorted(data)
