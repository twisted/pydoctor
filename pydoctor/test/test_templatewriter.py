from __future__ import print_function

import os
import shutil
import tempfile
from io import BytesIO

import pytest
from pydoctor import model, templatewriter
from pydoctor.templatewriter import pages, writer
from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage


def flatten(t):
    io = BytesIO()
    writer.flattenToFile(io, t)
    return io.getvalue().decode()


def getHTMLOf(ob):
    wr = templatewriter.TemplateWriter('')
    wr.system = ob.system
    f = BytesIO()
    wr.writeDocsForOne(ob, f)
    return f.getvalue().decode()

def test_simple():
    src = '''
    def f():
        """This is a docstring."""
    '''
    mod = fromText(src)
    v = getHTMLOf(mod.contents['f'])
    assert 'This is a docstring' in v

def test_empty_table():
    mod = fromText('')
    t = pages.ChildTable(pages.DocGetter(), mod, [])
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_nonempty_table():
    mod = fromText('def f(): pass')
    t = pages.ChildTable(pages.DocGetter(), mod, mod.orderedcontents)
    flattened = flatten(t)
    assert 'The renderer named' not in flattened

def test_rest_support():
    system = model.System()
    system.options.docformat = 'restructuredtext'
    system.options.verbosity = 4
    src = '''
    def f():
        """This is a docstring for f."""
    '''
    mod = fromText(src, system=system)
    html = getHTMLOf(mod.contents['f'])
    assert "<pre>" not in html

def test_document_code_in_init_module():
    system = processPackage("codeininit")
    html = getHTMLOf(system.allobjects['codeininit'])
    assert 'functionInInit' in html

def test_basic_package():
    system = processPackage("basic")
    targetdir = tempfile.mkdtemp()
    try:
        w = writer.TemplateWriter(targetdir)
        w.system = system
        system.options.htmlusesplitlinks = True
        system.options.htmlusesorttable = True
        w.prepOutputDirectory()
        root, = system.rootobjects
        w.writeDocsFor(root, False)
        w.writeModuleIndex(system)
        for ob in system.allobjects.values():
            if ob.documentation_location is model.DocLocation.OWN_PAGE:
                assert os.path.isfile(os.path.join(targetdir, ob.fullName() + '.html'))
        assert 'Package docstring' in open(os.path.join(targetdir, 'basic.html')).read()
    finally:
        shutil.rmtree(targetdir)

def test_hasdocstring():
    system = processPackage("basic")
    from pydoctor.templatewriter.summary import hasdocstring
    assert not hasdocstring(system.allobjects['basic._private_mod'])
    assert hasdocstring(system.allobjects['basic.mod.C.f'])
    sub_f = system.allobjects['basic.mod.D.f']
    assert hasdocstring(sub_f) and not sub_f.docstring


@pytest.mark.parametrize(
    'className',
    ['NewClassThatMultiplyInherits', 'OldClassThatMultiplyInherits'],
)
def test_multipleInheritanceNewClass(className):
    """
    A class that has multiple bases has all methods in its MRO
    rendered.
    """
    system = processPackage("multipleinheritance")

    cls = next(
        cls
        for cls in system.orderedallobjects
        if cls.name == className
    )

    html = getHTMLOf(cls)

    assert "methodA" in html
    assert "methodB" in html
