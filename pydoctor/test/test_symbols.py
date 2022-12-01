from textwrap import dedent
import ast

from pydoctor import astbuilder, astutils

def getScope(text:str) -> astbuilder.ScopeNode:
    mod = ast.parse(dedent(text))
    return astbuilder.fetchScopeSymbols(mod)

def test_symbols_module_level() -> None:
    src = '''
    from pydoctor.model import Class, Function as F
    import numpy as np, re, platform
    
    try:
        from foobar import FooBar
    except ModuleNotFoundError:
        class FooBar:
            """Stub for Foobar"""

    if platform.system() == 'Linux':
        def greet_os():
            print('Hello Tux!')
    elif platform.system() == 'Darwin':
        def greet_os():
            print('Hello Mac!')
    else:
        def greet_os():
            print('Hello Win!')

    '''

    scope = getScope(src)
    assert all(k in scope.symbols for k in ('Class', 'F', 'np', 're', 'FooBar', 'greet_os'))

    foostmt1, foostmt2 = scope.symbols['FooBar'].statements
    assert not foostmt1.constraints
    constraint, = foostmt2.constraints
    assert constraint.block is astbuilder.BlockType.EXCEPT_BLOCK
    cnode = constraint.node
    assert isinstance(cnode, ast.ExceptHandler)
    assert astutils.node2dottedname(cnode.type) == ['ModuleNotFoundError']

    greetstmt1, greetstmt2, greetstmt3 = scope.symbols['greet_os'].statements

    constraint1, = greetstmt1.constraints
    constraint2a, constraint2b, = greetstmt2.constraints
    constraint3a, constraint3b, = greetstmt3.constraints
    
    cnode = constraint1.node
    assert isinstance(cnode, ast.If)
    assert constraint1.block is astbuilder.BlockType.IF_BLOCK
    
    cnode = constraint2a.node
    assert isinstance(cnode, ast.If)
    assert constraint2a.block is astbuilder.BlockType.ELSE_BLOCK

    cnode = constraint2b.node
    assert isinstance(cnode, ast.If)
    assert constraint2b.block is astbuilder.BlockType.IF_BLOCK

    cnode = constraint3a.node
    assert isinstance(cnode, ast.If)
    assert constraint3a.block is astbuilder.BlockType.ELSE_BLOCK

    cnode = constraint3b.node
    assert isinstance(cnode, ast.If)
    assert constraint3a.block is astbuilder.BlockType.ELSE_BLOCK

def test_symbols_method() -> None:
    src = '''
    class C:
        def f(self, a, b:int=3, *ag, **kw):
            self.a, self.b = a,b
            self.d = dict(**kw)
    '''

    mod_scope = getScope(src)
    class_scope = mod_scope['C'][0]
    assert isinstance(class_scope, astbuilder.ScopeNode)
    func_scope = class_scope['f'][0]
    assert isinstance(func_scope, astbuilder.ScopeNode)

    assert isinstance(func_scope['self'][0].node, ast.arg)
    assert isinstance(func_scope['a'][0].node, ast.arg)
    assert isinstance(func_scope['b'][0].node, ast.arg)
    assert isinstance(func_scope['ag'][0].node, ast.arg)
    assert isinstance(func_scope['kw'][0].node, ast.arg)

    assert func_scope['self.d']
    assert func_scope['self.a']
    assert func_scope['self.b']