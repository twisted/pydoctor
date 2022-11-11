# TODO: skip if astroid is not installed.
import ast
import pytest
from typing import Type

from pydoctor import model
from .test_astbuilder import systemcls_param, fromText

import astroid.helpers

@pytest.mark.xfail
def test_astroid_augmented_assigment_list_and_tuple() -> None:
    """
    See https://github.com/PyCQA/astroid/issues/1865
    """
    mod = astroid.parse('''
    l = []
    l += (1,2)
    ''')

    assignment, augmented_assigment = mod.getattr('l')
    assert astroid.helpers.safe_infer(augmented_assigment).as_string() == '[1,2]'
    # We get AssertionError: assert Uninferable == '[1,2]'

def test_all_transforms() -> None:
    systemcls = model.System

    system = systemcls(model.Options.from_args(['--use-inference']))
    assert system.options.useinference == True
    assert 'pydoctor.extensions._inference' in system.extensions

    mod = fromText(''' 
    all1 = ['foo', 'bar']
    all2 = ['buz']
    __all__ = ['thing']
    __all__.extend(all1)
    __all__.append(all2[0])
    ''', modname='mod', system=system)
    assert 'mod' in system.allobjects

    assert mod.nodes.astroid.as_string().splitlines()[-3:-1] == [
        '__all__ += all1',
        '__all__ += [all2[0]]'
    ]


    # Unfortunately, since astroid uses a singleton to manage the environment,
    # this affects all other systems as well.
    system2 = systemcls()
    assert system2.options.useinference == False
    assert 'pydoctor.extensions._inference' not in system2.extensions

    mod = fromText(''' 
    all1 = ['foo', 'bar']
    all2 = ['buz']
    __all__ = ['thing']
    __all__.extend(all1)
    __all__.append(all2[0])
    ''', modname='mod', system=system2)

    assert mod.nodes.astroid.as_string().splitlines()[-3:-1] == [
        '__all__ += all1',
        '__all__ += [all2[0]]'
    ]

@pytest.mark.parametrize(['line'], 
    [("__all__ = ['f'] + mod_all",),  
     ("__all__ = ['f']; __all__ += mod_all",),
     ("__all__ = list(['f'] + mod_all)",),
     ("__all__ = ['f']; __all__.extend(mod_all)",),
     ("__all__ = ['f']; __all__.append(mod_all[0])",),
     ("__all__ = ['f']; __all__.append('g')",)])
def test_all_recognition_complex_one_line(line:str) -> None:
    """
    The value assigned to __all__ is correctly inferred when 
    it's built from binary operation '+' or augmented assigments '+='.
    As well as understands `__all__.extend()` and `__all__.append()`.
    """
    
    systemcls = model.System
    system = systemcls(model.Options.from_args(['--use-inference']))
    builder = system.systemBuilder(system)
    
    builder.addModuleString(f'''
    from .mod import *
    from .mod import __all__ as mod_all
    {line}

    def f():
        pass
    ''', modname='top', is_package=True)

    builder.addModuleString('''
    def g():
        pass
    __all__ = ['g']
    ''', modname='mod', parent_name='top')

    builder.buildModules()
    
    top = system.rootobjects[0]

    assert top.all == ['f', 'g']


def test_all_recognition_complex_augassign():
    systemcls = model.System
    system = systemcls(model.Options.from_args(['--use-inference']))
    builder = system.systemBuilder(system)

    builder.addModuleString('''
    from mod2 import __all__ as _l
    __all__ = ['f'] 
    __all__ += ['k']
    __all__ += _l

    ''', modname='mod1')

    builder.addModuleString('''
    __all__ = ['i', 'j']
    ''', modname='mod2')

    builder.buildModules()

    mod1, mod2 = system.rootobjects

    assert list(mod2.all) == ['i', 'j']
    assert list(mod1.all) == ['f', 'k', 'i', 'j']

def test_all_recognition_complex_extend():

    systemcls = model.System
    system = systemcls(model.Options.from_args(['--use-inference']))
    builder = system.systemBuilder(system)

    builder.addModuleString('''
    from mod2 import __all__ as _l
    from mod3 import __all__ as _l3
    __all__ = ['f', 'k']
    __all__.extend(_l)
    __all__.extend(_l3)
    ''', modname='mod1')

    builder.addModuleString('''
    __all__ = ['i']
    ''', modname='mod2')

    builder.addModuleString('''
    __all__ = ['j']
    ''', modname='mod3')

    builder.buildModules()

    mod1,_,_ = system.rootobjects

    assert list(mod1.all) == ['f', 'k', 'i', 'j']

def test_real_life_complex_append():

    src = '''
    __all__ = []
    __all__.append("default")
    __all__.append("select")
    __all__.append("poll")
    __all__.append("epoll")
    __all__.append("kqueue")
    __all__.append("cf")
    __all__.append("asyncio")
    __all__.append("wx")
    __all__.append("gi")
    __all__.append("gtk3")
    __all__.append("gtk2")
    __all__.append("glib2")
    __all__.append("win32er")
    __all__.append("iocp")

    '''

    systemcls = model.System
    system = systemcls(model.Options.from_args(['--use-inference']))
    mod = fromText(src, modname='test', system=system)
    astr = mod.nodes.astroid
    
    assert 'append' not in astr.as_string(), astr.as_string()

    expected = '''    
__all__ = []
__all__ += ['default']
__all__ += ['select']
__all__ += ['poll']
__all__ += ['epoll']
__all__ += ['kqueue']
__all__ += ['cf']
__all__ += ['asyncio']
__all__ += ['wx']
__all__ += ['gi']
__all__ += ['gtk3']
__all__ += ['gtk2']
__all__ += ['glib2']
__all__ += ['win32er']
__all__ += ['iocp']'''

    assert ast.dump(ast.parse(astr.as_string())) == ''

    defs = astr.getattr('__all__')
    assert len(defs) == 15
    assert list(defs[-1].infer()) == 15
    assert len(list(astr.igetattr('__all__ '))) ==  15

    assert mod.all is not None