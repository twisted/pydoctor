"""
Tests for Sphinx integration.
"""
from contextlib import closing
from StringIO import StringIO
import zlib

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


def make_SphinxInventory(logger=object()):
    """
    Return a SphinxInventory.
    """
    return SphinxInventory(logger=logger, project_name='project_name')


def make_SphinxInventoryWithLog():
    """
    Return a SphinxInventory with patched log.
    """
    log = []
    def msg(section, msg, thresh=0):
        """
        Partial implementation of pydoctor.model.System.msg
        """
        log.append((section, msg, thresh))

    inventory = make_SphinxInventory(logger=msg)
    return (inventory, log)


def test_initialization():
    """
    Is initialized with logger and project name.
    """
    logger = object()
    name = object()

    sut = SphinxInventory(logger=logger, project_name=name)

    assert logger is sut.info
    assert name is sut.project_name


def test_generate_empty_functional():
    """
    Functional test for index generation of empty API.

    Header is plain text while content is compressed.
    """
    project_name = 'some-name'
    log = []
    logger = lambda section, message, thresh=0: log.append((
        section, message, thresh))
    sut = SphinxInventory(logger=logger, project_name=project_name)
    output = PersistentStringIO()
    sut._openFileForWriting = lambda path: closing(output)

    sut.generate(subjects=[], basepath='base-path')

    expected_log = [(
        'sphinx',
        'Generating objects inventory at base-path/objects.inv',
        0
        )]
    assert expected_log == log

    expected_ouput = """# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
x\x9c\x03\x00\x00\x00\x00\x01"""
    assert expected_ouput == output.getvalue()



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
    sut, log = make_SphinxInventoryWithLog()

    result = sut._generateLine(
        UnknownType('ignore-system', 'unknown1', 'ignore-docstring'))

    assert 'unknown1 py:obj -1 unknown1.html -\n' == result



def test_getPayload_empty():
    """
    Return empty string.
    """
    sut = make_SphinxInventory()
    content = """# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
x\x9c\x03\x00\x00\x00\x00\x01"""

    result = sut._getPayload('http://base.ignore', content)

    assert '' == result


def test_getPayload_content():
    """
    Return content as string.
    """
    payload = 'first_line\nsecond line'
    sut = make_SphinxInventory()
    content = """# Ignored line
# Project: some-name
# Version: 2.0
# commented line.
%s""" % (zlib.compress(payload),)

    result = sut._getPayload('http://base.ignore', content)

    assert payload == result


def test_getPayload_invalid():
    """
    Return empty string and log an error when failing to uncompress data.
    """
    sut, log = make_SphinxInventoryWithLog()
    base_url = 'http://tm.tld'
    content = """# Project: some-name
# Version: 2.0
not-valid-zlib-content"""

    result = sut._getPayload(base_url, content)

    assert '' == result
    assert [(
        'sphinx', 'Failed to uncompress inventory from http://tm.tld', -1,
        )] == log


def test_getLink_not_found():
    """
    Return None if link does not exists.
    """
    sut = make_SphinxInventory()

    assert None is sut.getLink('no.such.name')


def test_getLink_found():
    """
    Return the link from internal state.
    """
    sut = make_SphinxInventory()
    sut._links['some.name'] = ('http://base.tld', 'some/url.php')

    assert 'http://base.tld/some/url.php' == sut.getLink('some.name')


def test_getLink_self_anchor():
    """
    Return the link with anchor as target name when link end with $.
    """
    sut = make_SphinxInventory()
    sut._links['some.name'] = ('http://base.tld', 'some/url.php#$')

    assert 'http://base.tld/some/url.php#some.name' == sut.getLink('some.name')


def test_update_functional():
    """
    Functional test for updating from an empty inventory.
    """
    payload = (
        'some.module1 py:module -1 module1.html -\n'
        'other.module2 py:module 0 module2.html Other description\n'
        )
    sut = make_SphinxInventory()
    # Patch URL loader to avoid hitting the system.
    content = """# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
%s""" % (zlib.compress(payload),)
    sut._getURL = lambda _: content

    sut.update('http://some.url/api/objects.inv')

    assert 'http://some.url/api/module1.html' == sut.getLink('some.module1')
    assert 'http://some.url/api/module2.html' == sut.getLink('other.module2')


def test_update_bad_url():
    """
    Log an error when failing to get base url from url.
    """
    sut, log = make_SphinxInventoryWithLog()

    sut.update('really.bad.url')

    assert sut._links == {}
    expected_log = [(
        'sphinx', 'Failed to get remote base url for really.bad.url', -1
        )]
    assert expected_log == log


def test_update_fail():
    """
    Log an error when failing to get content from url.
    """
    sut, log = make_SphinxInventoryWithLog()
    sut._getURL = lambda _: None

    sut.update('http://some.tld/o.inv')

    assert sut._links == {}
    expected_log = [(
        'sphinx',
        'Failed to get object inventory from http://some.tld/o.inv',
        -1,
        )]
    assert expected_log == log


def test_parseInventory_empty():
    """
    Return empty dict for empty input.
    """
    sut = make_SphinxInventory()

    result = sut._parseInventory('http://base.tld', '')

    assert {} == result


def test_parseInventory_single_line():
    """
    Return a dict with a single member.
    """
    sut = make_SphinxInventory()

    result = sut._parseInventory(
        'http://base.tld', 'some.attr py:attr -1 some.html De scription')

    assert {'some.attr': ('http://base.tld', 'some.html')} == result


def test_parseInventory_invalid_lines():
    """
    Skip line and log an error.
    """
    sut, log = make_SphinxInventoryWithLog()
    base_url = 'http://tm.tld'
    content = (
        'good.attr py:attribute -1 some.html -\n'
        'bad.attr bad format\n'
        'very.bad\n'
        '\n'
        'good.again py:module 0 again.html -\n'
        )

    result = sut._parseInventory(base_url, content)

    assert {
        'good.attr': (base_url, 'some.html'),
        'good.again': (base_url, 'again.html'),
        } == result
    assert [
        (
            'sphinx',
            'Failed to parse line "bad.attr bad format" for http://tm.tld',
            -1,
            ),
        ('sphinx', 'Failed to parse line "very.bad" for http://tm.tld', -1),
        ('sphinx', 'Failed to parse line "" for http://tm.tld', -1),
        ] == log
