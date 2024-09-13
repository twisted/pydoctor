import ast
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
