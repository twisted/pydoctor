import sys, textwrap, inspect
from pydoctor import model

def test_simple():
    src = '''
    def f():
        """This is a docstring."""
    '''
    mod = model.fromText(textwrap.dedent(src))
    assert len(mod.contents) == 1
    func, = mod.contents.values()
    assert func.fullName() == '<test>.f'
    assert func.docstring == """This is a docstring."""

def test_function_argspec():
    # we don't compare the defaults part of the argspec directly any
    # more because inspect.getargspec returns the actual objects that
    # are the defaults where as the ast stuff always gives strings
    # representing those objects
    src = '''
    def f((a,z), b=3, *c, **kw):
        pass
    '''
    src = textwrap.dedent(src)
    mod = model.fromText(src)
    docfunc, = mod.contents.values()
    ns = {}
    exec src in ns
    realf = ns['f']
    inspectargspec = inspect.getargspec(realf)
    assert inspectargspec[:-1] == docfunc.argspec[:-1]
    assert docfunc.argspec[-1] == ('3',)

def test_class():
    src = '''
    class C:
        def f():
            """This is a docstring."""
    '''
    mod = model.fromText(textwrap.dedent(src))
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
    mod = model.fromText(textwrap.dedent(src))
    assert len(mod.contents) == 2
    clsC, clsD = mod.contents.values()
    assert clsC.fullName() == '<test>.C'
    assert clsC.docstring == None
    assert len(clsC.contents) == 1

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 1
    base, = clsD.bases
    assert base == '<test>.C'

def test_class_with_base_from_module():
    src = '''
    from X.Y import A
    from Z import B as C
    class D(A, C):
        def f():
            """This is a docstring."""
    '''
    mod = model.fromText(textwrap.dedent(src))
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
    mod = model.fromText(textwrap.dedent(src))
    assert len(mod.contents) == 1
    clsD, = mod.contents.values()

    assert clsD.fullName() == '<test>.D'
    assert clsD.docstring == None
    assert len(clsD.contents) == 1

    assert len(clsD.bases) == 3
    base1, base2, base3 = clsD.bases
    assert base1 == 'X.A'
    assert base2 == 'X.B.C'
    assert base3 == 'Y.Z.C'

def test_ordering():
    src = '''
    def f():
        class A(B):
            pass
    from X import Y as B
    '''
    mod = model.fromText(textwrap.dedent(src))
    A = mod.system.allobjects['<test>.f.A']
    assert A.bases == ['X.Y']

def test_local_import():
    src = '''
    class B:
        pass
    def f():
        from X import Y as B
        class A(B):
            pass
    class D(B):
        pass
    '''
    mod = model.fromText(textwrap.dedent(src))

    A = mod.system.allobjects['<test>.f.A']
    assert A.bases == ['X.Y']

    D = mod.system.allobjects['<test>.D']
    assert D.bases == ['<test>.B']

def test_aliasing():
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
    system = model.System()
    model.fromText(textwrap.dedent(src_a), 'a', system)
    model.fromText(textwrap.dedent(src_b), 'b', system)
    model.fromText(textwrap.dedent(src_c), 'c', system)
    assert system.allobjects['c.C'].bases == ['b.B']
    system.resolveAliases()
    assert system.allobjects['c.C'].bases == ['a.A']

def test_more_aliasing():
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
    system = model.System()
    model.fromText(textwrap.dedent(src_a), 'a', system)
    model.fromText(textwrap.dedent(src_b), 'b', system)
    model.fromText(textwrap.dedent(src_c), 'c', system)
    model.fromText(textwrap.dedent(src_d), 'd', system)
    assert system.allobjects['d.D'].bases == ['c.C']
    system.resolveAliases()
    assert system.allobjects['d.D'].bases == ['a.A']

def test_subclasses():
    src = '''
    class A:
        pass
    class B(A):
        pass
    '''
    system = model.fromText(textwrap.dedent(src)).system
    assert (system.allobjects['<test>.A'].subclasses ==
            [system.allobjects['<test>.B']])
