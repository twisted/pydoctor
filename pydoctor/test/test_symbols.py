from textwrap import dedent
import ast

from pydoctor import symbols, astutils

def getScope(text:str) -> symbols.Scope:
    mod = ast.parse(dedent(text))
    return symbols.buildSymbols(mod)

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
    assert isinstance(constraint, symbols.ExceptHandlerConstraint)
    assert constraint.types == ['ModuleNotFoundError']

    greetstmt1, greetstmt2, greetstmt3 = scope.symbols['greet_os'].statements

    constraint1, = greetstmt1.constraints
    constraint2a, constraint2b, = greetstmt2.constraints
    constraint3a, constraint3b, = greetstmt3.constraints
    
    assert isinstance(constraint1, symbols.IfConstraint)
    assert isinstance(constraint2a, symbols.ElseConstraint)
    assert isinstance(constraint2b, symbols.IfConstraint)
    assert isinstance(constraint3a, symbols.ElseConstraint)
    assert isinstance(constraint3b, symbols.ElseConstraint)

def test_symbols_method() -> None:
    src = '''
    class C:
        def f(self, a, b:int=3, *ag, **kw):
            self.a, self.b = a,b
            self.d = dict(**kw)
    '''

    mod_scope = getScope(src)
    class_scope = mod_scope['C'][0]
    assert isinstance(class_scope, symbols.Scope)
    func_scope = class_scope['f'][0]
    assert isinstance(func_scope, symbols.Scope)

    assert isinstance(func_scope['self'][0], symbols.Arguments)
    assert isinstance(func_scope['a'][0], symbols.Arguments)
    assert isinstance(func_scope['b'][0], symbols.Arguments)
    assert isinstance(func_scope['ag'][0], symbols.Arguments)
    assert isinstance(func_scope['kw'][0], symbols.Arguments)

    assert func_scope['self.d']
    assert func_scope['self.a']
    assert func_scope['self.b']

def test_del_statement() -> None:
    src = '''
    f = Factory()
    rand = f.rand
    del f    
    '''

    mod_scope = getScope(src)
    stmts = mod_scope['f']
    assert len(stmts) == 2
    _, delstmt = stmts
    assert delstmt is symbols.filter_stmts_by_type(mod_scope['f'], symbols.Deletion)[0]

def test_global_nonlocal() -> None:
    src = '''
    v = Tue
    def f(a:int, b:int, c:bool) -> int:
        global v 
        if c:
            v = c
        d = False
        def g(a,b) -> int:
            nonlocal d
            d = a*b
            return 
        g(a,b)
        return d
    '''
