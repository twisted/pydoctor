import ast
from textwrap import dedent
from typing import Any
from pydoctor import astutils

def test_parentage() -> None:
    tree = ast.parse('class f(b):...')
    astutils.Parentage().visit(tree)
    assert tree.body[0].parent == tree # type:ignore
    assert tree.body[0].body[0].parent == tree.body[0] # type:ignore
    assert tree.body[0].bases[0].parent == tree.body[0] # type:ignore

def test_get_assign_docstring_node() -> None:
    tree = ast.parse('var = 1\n\n\n"inline docs"')
    astutils.Parentage().visit(tree)
    assert astutils.get_str_value(astutils.get_assign_docstring_node(tree.body[0])) == "inline docs" # type:ignore

    tree = ast.parse('var:int = 1\n\n\n"inline docs"')
    astutils.Parentage().visit(tree)
    assert astutils.get_str_value(astutils.get_assign_docstring_node(tree.body[0])) == "inline docs" # type:ignore


def test_get_assign_docstring_node_not_in_body() -> None:
    src = dedent('''
    if True: pass
    else:
        v = True; 'inline docs'
    ''')
    tree = ast.parse(src)
    astutils.Parentage().visit(tree)
    assert astutils.get_str_value(astutils.get_assign_docstring_node(tree.body[0].orelse[0])) == "inline docs" # type:ignore

    src = dedent('''
    try:
        raise ValueError()
    except:
        v = True; 'inline docs'
    else:
        w = True; 'inline docs'      
    finally:
        x = True; 'inline docs'      
    ''')
    tree = ast.parse(src)
    astutils.Parentage().visit(tree)
    assert astutils.get_str_value(astutils.get_assign_docstring_node(tree.body[0].handlers[0].body[0])) == "inline docs" # type:ignore
    assert astutils.get_str_value(astutils.get_assign_docstring_node(tree.body[0].orelse[0])) == "inline docs" # type:ignore
    assert astutils.get_str_value(astutils.get_assign_docstring_node(tree.body[0].finalbody[0])) == "inline docs" # type:ignore


def test_is_old_school_namespace_package(subtests:Any) -> None:

    sources = {

        # True cases
        'from pkgutil import extend_path;__path__ = extend_path(__path__, __name__)': True, 
        'import pkg_resources;pkg_resources.declare_namespace(__name__)': True,
        'import pkg_resources;pkg_resources.declare_namespace(name=__name__)': True,
        '''__import__('pkg_resources').declare_namespace(__name__)''': True,
        '''__path__ = __import__('pkgutil').extend_path(__path__, __name__)''': True,
        'declare_namespace(__name__)': True,
        '__path__ = extend_path(__path__, __name__)': True,
        'declare_namespace(name=__name__)': True,
        '__path__ = extend_path(path=__path__, name=__name__)': True,
        '__path__: list[str] = extend_path(path=__path__, name=__name__)': True,
        'x.declare_namespace(__name__)': True,
        '__path__ = x.extend_path(__path__, __name__)': True,
        
        # False cases
        '''declare_namespace(__name__ + '._somethingelse')''': False,
        '''__path__ = extend_path(__path__, __name__ + '._somethingelse')''': False,
        '''__path__ = extend_path(somethingelse, __name__)''': False,
        '''declare_namespace(__name__, somethingelse)''': False,
        '''__path__ = extend_path(__path__, __name__, somethingelse)''': False,
        'declare_namespace()': False,
        'declare_namespace()(__name__)': False,
        '__path__ = extend_path(__name__)': False,
        '__path__ = somethingelse': False,
        '__path__ = somethingelse()()': False,
    }

    for src, expected in sources.items():
        with subtests.test(msg="old school namespace packages", src=src):
            tree = ast.parse(dedent(src))
            assert astutils.is_old_school_namespace_package(tree) == expected