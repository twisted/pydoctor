import ast
from textwrap import dedent
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

