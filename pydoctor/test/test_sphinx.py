"""
Tests for Sphinx integration.
"""
from contextlib import closing
from StringIO import StringIO

from pydoctor import model
from pydoctor.sphinx import SphinxInventory


class PersistentStringIO(StringIO):
    """
    A custom stringIO which keeps content after file is closed.
    """
    def close(self):
        """
        Close, but keep the memory buffer and seek position.
        """
        if not self.closed:
            self.closed = True

    def getvalue(self):
        """
        Retrieve the entire contents of the "file" at any time even after
        the StringIO object's close() method is called.
        """
        if self.buflist:
            self.buf += ''.join(self.buflist)
            self.buflist = []
        return self.buf


def test_initialization():
    """
    Is initialized with logger and project name.
    """
    logger = object()
    name = object()

    sut = SphinxInventory(logger=logger, project_name=name)

    assert logger is sut.msg
    assert name is sut.project_name


def test_generate_empty_functional():
    """
    Functional test for index generation of empty API.

    Header is plain text while content is compressed.
    """
    project_name = 'some-name'
    log = []
    logger = lambda part, message: log.append((part, message))
    sut = SphinxInventory(logger=logger, project_name=project_name)
    output = PersistentStringIO()
    sut._openFileForWriting = lambda path: closing(output)

    sut.generate(subjects=[], basepath='base-path')

    expected_log = [(
        'sphinx',
        'Generating objects inventory at base-path/objects.inv'
        )]
    assert expected_log == log

    expected_ouput = """# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
x\x9c\x03\x00\x00\x00\x00\x01"""
    assert expected_ouput == output.getvalue()


def make_SphinxInventory():
    """
    Return a SphinxInventory.
    """
    return SphinxInventory(logger=object(), project_name='project_name')


def test_generateContent():
    """
    Return a string with inventory for all  targeted objects, recursive.
    """
    sut = make_SphinxInventory()
    system = model.System()
    root1 = model.Package(system, 'package1', 'docstring1')
    root2 = model.Package(system, 'package2', 'docstring2')
    child1 = model.Package(system, 'child1', 'docstring3', parent=root2)
    system.addObject(child1)
    subjects = [root1, root2]

    result = sut._generateContent(subjects)

    expected_result = (
        'package1 py:module -1 package1.html -\n'
        'package2 py:module -1 package2.html -\n'
        'package2.child1 py:module -1 package2.child1.html -\n'
        )
    assert expected_result == result


def test_generateLine_package():
    """
    Check inventory for package.
    """
    sut = make_SphinxInventory()

    result = sut._generateLine(
        model.Package('ignore-system', 'package1', 'ignore-docstring'))

    assert 'package1 py:module -1 package1.html -\n' == result


def test_generateLine_module():
    """
    Check inventory for module.
    """
    sut = make_SphinxInventory()

    result = sut._generateLine(
        model.Module('ignore-system', 'module1', 'ignore-docstring'))

    assert 'module1 py:module -1 module1.html -\n' == result


def test_generateLine_class():
    """
    Check inventory for class.
    """
    sut = make_SphinxInventory()

    result = sut._generateLine(
        model.Class('ignore-system', 'class1', 'ignore-docstring'))

    assert 'class1 py:class -1 class1.html -\n' == result


def test_generateLine_function():
    """
    Check inventory for function.

    Functions are inside a module.
    """
    sut = make_SphinxInventory()
    parent = model.Module('ignore-system', 'module1', 'docstring')

    result = sut._generateLine(
        model.Function('ignore-system', 'func1', 'ignore-docstring', parent))

    assert 'module1.func1 py:function -1 module1.html#func1 -\n' == result


def test_generateLine_method():
    """
    Check inventory for method.

    Methods are functions inside a class.
    """
    sut = make_SphinxInventory()
    parent = model.Class('ignore-system', 'class1', 'docstring')

    result = sut._generateLine(
        model.Function('ignore-system', 'meth1', 'ignore-docstring', parent))

    assert 'class1.meth1 py:method -1 class1.html#meth1 -\n' == result


def test_generateLine_attribute():
    """
    Check inventory for attributes.
    """
    sut = make_SphinxInventory()
    parent = model.Class('ignore-system', 'class1', 'docstring')

    result = sut._generateLine(
        model.Attribute('ignore-system', 'attr1', 'ignore-docstring', parent))

    assert 'class1.attr1 py:attribute -1 class1.html#attr1 -\n' == result


class UnknownType(model.Documentable):
    """
    Documentable type to help with testing.
    """


def test_generateLine_unknown():
    """
    When object type is uknown a message is logged and is handled as
    generic object.
    """
    log = []
    sut = make_SphinxInventory()
    sut.msg = lambda part, message: log.append((part, message))

    result = sut._generateLine(
        UnknownType('ignore-system', 'unknown1', 'ignore-docstring'))

    assert 'unknown1 py:obj -1 unknown1.html -\n' == result
