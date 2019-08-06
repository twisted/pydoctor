from __future__ import print_function

import inspect
import textwrap

from pydoctor import astbuilder, model


def fromText(text, modname='<test>', system=None,
             buildercls=None,
             systemcls=model.System):
    if system is None:
        _system = systemcls()
    else:
        _system = system
    if buildercls is None:
        buildercls = _system.defaultBuilder
    builder = buildercls(_system)
    mod = builder.pushModule(modname, None)
    builder.popModule()
    ast = astbuilder.parse(textwrap.dedent(text))
    builder.processModuleAST(ast, mod)
    mod = _system.allobjects[modname]
    mod.ast = ast
    mod.state = model.PROCESSED
    return mod

def test_simple():
    src = '''
    def f():
        """This is a docstring."""
    '''
    mod = fromText(src)
    assert len(mod.contents) == 1
    func, = mod.contents.values()
    assert func.fullName() == '<test>.f'
    assert func.docstring == """This is a docstring."""


def test_function_argspec():
    # we don't compare the defaults part of the argspec directly any
    # more because inspect.getargspec returns the actual objects that
    # are the defaults where as the ast stuff always gives strings
    # representing those objects
    src = textwrap.dedent('''
    def f((a,z), b=3, *c, **kw):
        pass
    ''')
    mod = fromText(src)
    docfunc, = mod.contents.values()
    ns = {}
    exec(src, ns)
    realf = ns['f']
    inspectargspec = inspect.getargspec(realf)
    assert tuple(inspectargspec[:-1]) == tuple(docfunc.argspec[:-1])
    assert docfunc.argspec[-1] == ('3',)

def test_class():
    src = '''
    class C:
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src)
    assert len(mod.contents) == 1
    cls, = mod.contents.values()
    assert cls.fullName() == '<test>.C'
    assert cls.docstring == None
    assert len(cls.contents) == 1
    func, = cls.contents.values()
    assert func.fullName() == '<test>.C.f'
    assert func.docstring == """This is a docstring."""


def test_class_with_base():
    src = '''
    class C:
        def f():
            """This is a docstring."""
    class D(C):
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src)
    assert len(mod.contents) == 2
    clsC, clsD = mod.orderedcontents
    assert clsC.fullName() == '<test>.C'
    assert clsC.docstring == None
    assert len(clsC.contents) == 1

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 1
    base, = clsD.bases
    assert base == '<test>.C'

def test_follow_renaming():
    src = '''
    class C: pass
    D = C
    class E(D): pass
    '''
    mod = fromText(src)
    C = mod.contents['C']
    E = mod.contents['E']
    assert E.baseobjects == [C], E.baseobjects

def test_class_with_base_from_module():
    src = '''
    from X.Y import A
    from Z import B as C
    class D(A, C):
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src)
    assert len(mod.contents) == 1
    clsD, = mod.contents.values()

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 2
    base1, base2 = clsD.bases
    assert base1 == 'X.Y.A'
    assert base2 == 'Z.B'

    src = '''
    import X
    import Y.Z as M
    class D(X.A, X.B.C, M.C):
        def f():
            """This is a docstring."""
    '''
    mod = fromText(src)
    assert len(mod.contents) == 1
    clsD, = mod.contents.values()

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 3
    base1, base2, base3 = clsD.bases
    assert base1 == 'X.A', base1
    assert base2 == 'X.B.C', base2
    assert base3 == 'Y.Z.C', base3

def test_aliasing():
    def addsrc(system):
        src_a = '''
        class A:
            pass
        '''
        src_b = '''
        from a import A as B
        '''
        src_c = '''
        from b import B
        class C(B):
            pass
        '''
        fromText(src_a, 'a', system)
        fromText(src_b, 'b', system)
        fromText(src_c, 'c', system)

    system = model.System()
    addsrc(system)
    assert system.allobjects['c.C'].bases == ['a.A']

def test_more_aliasing():
    def addsrc(system):
        src_a = '''
        class A:
            pass
        '''
        src_b = '''
        from a import A as B
        '''
        src_c = '''
        from b import B as C
        '''
        src_d = '''
        from c import C
        class D(C):
            pass
        '''
        fromText(src_a, 'a', system)
        fromText(src_b, 'b', system)
        fromText(src_c, 'c', system)
        fromText(src_d, 'd', system)

    system = model.System()
    addsrc(system)
    assert system.allobjects['d.D'].bases == ['a.A']

def test_aliasing_recursion():
    system = model.System()
    src = '''
    class C:
        pass
    from mod import C
    class D(C):
        pass
    '''
    mod = fromText(src, 'mod', system)
    assert mod.contents['D'].bases == ['mod.C'], mod.contents['D'].bases

def test_subclasses():
    src = '''
    class A:
        pass
    class B(A):
        pass
    '''
    system = fromText(src).system
    assert (system.allobjects['<test>.A'].subclasses ==
            [system.allobjects['<test>.B']])

def test_inherit_names():
    src = '''
    class A:
        pass
    class A(A):
        pass
    '''
    mod = fromText(src)
    assert [b.name for b in mod.contents['A'].allbases()] == ['A 0']

def test_nested_class_inheriting_from_same_module():
    src = '''
    class A:
        pass
    class B:
        class C(A):
            pass
    '''
    fromText(src)

def test_all_recognition():
    mod = fromText('''
    def f():
        pass
    __all__ = ['f']
    ''')
    astbuilder.findAll(mod.ast, mod)
    assert mod.all == ['f']

def test_all_in_class_non_recognition():
    mod = fromText('''
    class C:
        __all__ = ['f']
    ''')
    astbuilder.findAll(mod.ast, mod)
    assert mod.all is None

def test_classmethod():
    mod = fromText('''
    class C:
        @classmethod
        def f(klass):
            pass
    ''')
    assert mod.contents['C'].contents['f'].kind == 'Class Method'
    mod = fromText('''
    class C:
        def f(klass):
            pass
        f = classmethod(f)
    ''')
    assert mod.contents['C'].contents['f'].kind == 'Class Method'

def test_classdecorator():
    mod = fromText('''
    def cd(cls):
        pass
    @cd
    class C:
        pass
    ''', modname='mod')
    C = mod.contents['C']
    assert C.decorators == [(('cd', 'mod.cd', mod.contents['cd']), None)], \
      C.decorators


def test_classdecorator_with_args():
    mod = fromText('''
    def cd(): pass
    class A: pass
    @cd(A)
    class C:
        pass
    ''', modname='test')
    cd = mod.contents['cd']
    A = mod.contents['A']
    C = mod.contents['C']
    assert C.decorators == [(('cd', 'test.cd', cd), [('A', 'test.A', A)])], \
      C.decorators


def test_import_star():
    mod_a = fromText('''
    def f(): pass
    ''', modname='a')
    mod_b = fromText('''
    from a import *
    ''', modname='b', system=mod_a.system)
    assert mod_b.resolveName('f') == mod_a.contents['f']
