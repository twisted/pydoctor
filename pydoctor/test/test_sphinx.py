"""
Tests for Sphinx integration.
"""
from __future__ import print_function

import datetime
import io
import string
import zlib
from contextlib import closing

import cachecontrol
import pytest
import requests
from pydoctor import model, sphinx
from urllib3 import HTTPResponse

from hypothesis import given, settings
from hypothesis import strategies as st


class PersistentBytesIO(io.BytesIO):
    """
    A custom BytesIO which keeps content after file is closed.
    """
    def close(self):
        """
        Close, but keep the memory buffer and seek position.
        """
        pass



def make_SphinxInventoryWithLog(factory=sphinx.SphinxInventory):
    """
    Return a SphinxInventory with patched log.
    """
    log = []
    def msg(section, msg, thresh=0):
        """
        Partial implementation of pydoctor.model.System.msg
        """
        log.append((section, msg, thresh))

    inventory = factory(logger=msg)
    return (inventory, log)


def test_writer_initialization():
    """
    Is initialized with logger and project name.
    """
    logger = object()
    name = object()

    sut = sphinx.SphinxInventoryWriter(logger=logger, project_name=name)

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
    sut = sphinx.SphinxInventoryWriter(logger=logger, project_name=project_name)
    output = PersistentBytesIO()
    sut._openFileForWriting = lambda path: closing(output)

    sut.generate(subjects=[], basepath='base-path')

    expected_log = [(
        'sphinx',
        'Generating objects inventory at base-path/objects.inv',
        0
        )]
    assert expected_log == log

    expected_ouput = b"""# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
x\x9c\x03\x00\x00\x00\x00\x01"""
    assert expected_ouput == output.getvalue()



def test_generateContent():
    """
    Return a string with inventory for all  targeted objects, recursive.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')
    system = model.System()
    root1 = model.Package(system, 'package1')
    root2 = model.Package(system, 'package2')
    child1 = model.Package(system, 'child1', parent=root2)
    system.addObject(child1)
    subjects = [root1, root2]

    result = sut._generateContent(subjects)

    expected_result = (
        b'package1 py:module -1 package1.html -\n'
        b'package2 py:module -1 package2.html -\n'
        b'package2.child1 py:module -1 package2.child1.html -\n'
        )
    assert expected_result == result


def test_generateLine_package():
    """
    Check inventory for package.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')

    result = sut._generateLine(
        model.Package('ignore-system', 'package1'))

    assert 'package1 py:module -1 package1.html -\n' == result


def test_generateLine_module():
    """
    Check inventory for module.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')

    result = sut._generateLine(
        model.Module('ignore-system', 'module1'))

    assert 'module1 py:module -1 module1.html -\n' == result


def test_generateLine_class():
    """
    Check inventory for class.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')

    result = sut._generateLine(
        model.Class('ignore-system', 'class1'))

    assert 'class1 py:class -1 class1.html -\n' == result


def test_generateLine_function():
    """
    Check inventory for function.

    Functions are inside a module.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')
    parent = model.Module('ignore-system', 'module1')

    result = sut._generateLine(
        model.Function('ignore-system', 'func1', parent))

    assert 'module1.func1 py:function -1 module1.html#func1 -\n' == result


def test_generateLine_method():
    """
    Check inventory for method.

    Methods are functions inside a class.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')
    parent = model.Class('ignore-system', 'class1')

    result = sut._generateLine(
        model.Function('ignore-system', 'meth1', parent))

    assert 'class1.meth1 py:method -1 class1.html#meth1 -\n' == result


def test_generateLine_attribute():
    """
    Check inventory for attributes.
    """
    sut = sphinx.SphinxInventoryWriter(logger=object(),
                                       project_name='project_name')
    parent = model.Class('ignore-system', 'class1')

    result = sut._generateLine(
        model.Attribute('ignore-system', 'attr1', parent))

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
    sut, log = make_SphinxInventoryWithLog(
        lambda **kwargs: sphinx.SphinxInventoryWriter(
                                    project_name='project_name', **kwargs)
        )

    result = sut._generateLine(
        UnknownType('ignore-system', 'unknown1'))

    assert 'unknown1 py:obj -1 unknown1.html -\n' == result



def test_getPayload_empty():
    """
    Return empty string.
    """
    sut = sphinx.SphinxInventory(logger=object())
    content = b"""# Sphinx inventory version 2
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
    payload = u"first_line\nsecond line\nit's a snake: \U0001F40D"
    sut = sphinx.SphinxInventory(logger=object())
    content = b"""# Ignored line
# Project: some-name
# Version: 2.0
# commented line.
%s""" % (zlib.compress(payload.encode('utf-8')),)

    result = sut._getPayload('http://base.ignore', content)

    assert payload == result


def test_getPayload_invalid_uncompress():
    """
    Return empty string and log an error when failing to uncompress data.
    """
    sut, log = make_SphinxInventoryWithLog()
    base_url = 'http://tm.tld'
    content = b"""# Project: some-name
# Version: 2.0
not-valid-zlib-content"""

    result = sut._getPayload(base_url, content)

    assert '' == result
    assert [(
        'sphinx', 'Failed to uncompress inventory from http://tm.tld', -1,
        )] == log


def test_getPayload_invalid_decode():
    """
    Return empty string and log an error when failing to uncompress data.
    """
    payload = b'\x80'
    sut, log = make_SphinxInventoryWithLog()
    base_url = 'http://tm.tld'
    content = b"""# Project: some-name
# Version: 2.0
%s""" % (zlib.compress(payload),)

    result = sut._getPayload(base_url, content)

    assert '' == result
    assert [(
        'sphinx', 'Failed to decode inventory from http://tm.tld', -1,
        )] == log


def test_getLink_not_found():
    """
    Return None if link does not exists.
    """
    sut = sphinx.SphinxInventory(logger=object())

    assert None is sut.getLink('no.such.name')


def test_getLink_found():
    """
    Return the link from internal state.
    """
    sut = sphinx.SphinxInventory(logger=object())
    sut._links['some.name'] = ('http://base.tld', 'some/url.php')

    assert 'http://base.tld/some/url.php' == sut.getLink('some.name')


def test_getLink_self_anchor():
    """
    Return the link with anchor as target name when link end with $.
    """
    sut = sphinx.SphinxInventory(logger=object())
    sut._links['some.name'] = ('http://base.tld', 'some/url.php#$')

    assert 'http://base.tld/some/url.php#some.name' == sut.getLink('some.name')


def test_update_functional():
    """
    Functional test for updating from an empty inventory.
    """
    payload = (
        b'some.module1 py:module -1 module1.html -\n'
        b'other.module2 py:module 0 module2.html Other description\n'
        )
    sut = sphinx.SphinxInventory(logger=object())
    # Patch URL loader to avoid hitting the system.
    content = b"""# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
%s""" % (zlib.compress(payload),)

    url = 'http://some.url/api/objects.inv'

    sut.update(sphinx.StubCache({url: content}), url)

    assert 'http://some.url/api/module1.html' == sut.getLink('some.module1')
    assert 'http://some.url/api/module2.html' == sut.getLink('other.module2')


def test_update_bad_url():
    """
    Log an error when failing to get base url from url.
    """
    sut, log = make_SphinxInventoryWithLog()

    sut.update(sphinx.StubCache({}), 'really.bad.url')

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

    sut.update(sphinx.StubCache({}), 'http://some.tld/o.inv')

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
    sut = sphinx.SphinxInventory(logger=object())

    result = sut._parseInventory('http://base.tld', '')

    assert {} == result


def test_parseInventory_single_line():
    """
    Return a dict with a single member.
    """
    sut = sphinx.SphinxInventory(logger=object())

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


maxAgeAmounts = st.integers() | st.just("\x00")
maxAgeUnits = st.sampled_from(tuple(sphinx._maxAgeUnits)) | st.just("\x00")


class TestParseMaxAge:
    """
    Tests for L{sphinx.parseMaxAge}
    """

    @given(
        amount=maxAgeAmounts,
        unit=maxAgeUnits,
    )
    def test_toTimedelta(self, amount, unit):
        """
        A parsed max age dictionary consists of valid arguments to
        L{datetime.timedelta}, and the constructed L{datetime.timedelta}
        matches the specification.
        """
        maxAge = "{}{}".format(amount, unit)
        try:
            parsedMaxAge = sphinx.parseMaxAge(maxAge)
        except sphinx.InvalidMaxAge:
            pass
        else:
            td = datetime.timedelta(**parsedMaxAge)
            converter = {
                's': 1,
                'm': 60,
                'h': 60 * 60,
                'd': 24 * 60 * 60,
                'w': 7 * 24 * 60 * 60
            }
            total_seconds = amount * converter[unit]
            assert pytest.approx(td.total_seconds()) == total_seconds


class ClosingBytesIO(io.BytesIO):
    """
    A L{io.BytesIO} instance that closes itself after all its data has
    been read.  This mimics the behavior of L{HTTPResponse} in the
    standard library.
    """

    def read(self, *args, **kwargs):
        data = super(ClosingBytesIO, self).read(*args, **kwargs)
        if self.tell() >= len(self.getvalue()):
            self.close()
        return data


def test_ClosingBytesIO():
    """
    L{ClosingBytesIO} closes itself when all its data has been read.
    """
    data = b'some data'
    cbio = ClosingBytesIO(data)

    buffer = [cbio.read(1)]

    assert not cbio.closed

    buffer.append(cbio.read())

    assert cbio.closed

    assert b''.join(buffer) == data


class TestIntersphinxCache:
    """
    Tests for L{sphinx.IntersphinxCache}
    """

    @pytest.fixture
    def send_returns(self, monkeypatch):
        """
        Return a function that patches
        L{requests.adapters.HTTPResponse.send} so that it returns the
        provided L{urllib3.Response}.
        """
        def send_returns(response):
            def send(self, request, **kwargs):
                return self.build_response(request, response)

            monkeypatch.setattr(
                requests.adapters.HTTPAdapter,
                "send",
                send,
            )

            return monkeypatch
        return send_returns

    def test_cache(self, tmpdir, send_returns):
        """
        L{IntersphinxCache.get} caches responses to the file system.
        """
        url = u"https://cache.example/objects.inv"
        content = b'content'

        send_returns(
            HTTPResponse(
                body=ClosingBytesIO(content),
                headers={
                    'date': 'Sun, 06 Nov 1994 08:49:37 GMT',
                },
                status=200,
                preload_content=False,
                decode_content=False,
            ),
        )

        loadsCache = sphinx.IntersphinxCache.fromParameters(
            sessionFactory=requests.Session,
            cachePath=str(tmpdir),
            maxAgeDictionary={"weeks": 1}
        )

        assert loadsCache.get(url) == content

        # Now the response contains different data that will not be
        # returned when the cache is enabled.
        send_returns(
            HTTPResponse(
                body=ClosingBytesIO(content * 2),
                headers={
                    'date': 'Sun, 06 Nov 1994 08:49:37 GMT',
                },
                status=200,
                preload_content=False,
                decode_content=False,
            ),

        )

        assert loadsCache.get(url) == content

        readsCacheFromFileSystem = sphinx.IntersphinxCache.fromParameters(
            sessionFactory=requests.Session,
            cachePath=str(tmpdir),
            maxAgeDictionary={"weeks": 1}
        )

        assert readsCacheFromFileSystem.get(url) == content

    def test_getRaisesException(self):
        """
        L{IntersphinxCache.get} returns L{None} if an exception is
        raised while C{GET}ing a URL and logs the exception.
        """
        loggedExceptions = []

        class _Logger:

            @staticmethod
            def exception(*args, **kwargs):
                loggedExceptions.append((args, kwargs))

        class _RaisesOnGet:

            @staticmethod
            def get(url):
                raise Exception()

        cache = sphinx.IntersphinxCache(session=_RaisesOnGet, logger=_Logger)

        assert cache.get(u"some url") is None

        assert len(loggedExceptions)


class TestStubCache:
    """
    Tests for L{sphinx.StubCache}.
    """

    def test_getFromCache(self):
        """
        L{sphinx.StubCache.get} returns its cached content for a URL.
        """
        url = u"url"
        content = b"content"

        cache = sphinx.StubCache({url: content})

        assert cache.get(url) is content

    def test_not_in_cache(self):
        """
        L{sphinx.StubCache.get} returns L{None} if it has no cached
        content for a URL.
        """
        cache = sphinx.StubCache({})

        assert cache.get(b"url") is None


@given(
    clearCache=st.booleans(),
    enableCache=st.booleans(),
    cacheDirectoryName=st.text(
        alphabet=sorted(set(string.printable) - set('\\/:*?"<>|\x0c\x0b\n')),
        min_size=3,             # Avoid ..
        max_size=32,            # Avoid upper length on path
    ),
    maxAgeAmount=maxAgeAmounts,
    maxAgeUnit=maxAgeUnits,
)
@settings(max_examples=700)
def test_prepareCache(
        tmpdir,
        clearCache,
        enableCache,
        cacheDirectoryName,
        maxAgeAmount,
        maxAgeUnit,
):
    """
    The cache directory is deleted when C{clearCache} is L{True}; an
    L{IntersphinxCache} is created with a session on which is mounted
    L{cachecontrol.CacheControlAdapter} for C{http} and C{https} URLs.
    """
    cacheDirectory = tmpdir.join("fakecache").ensure(dir=True)
    for child in cacheDirectory.listdir():
        child.remove()
    cacheDirectory.ensure(cacheDirectoryName)

    try:
        cache = sphinx.prepareCache(
            clearCache=clearCache,
            enableCache=enableCache,
            cachePath=str(cacheDirectory),
            maxAge="{}{}".format(maxAgeAmount, maxAgeUnit)
        )
    except sphinx.InvalidMaxAge:
        pass
    else:
        assert isinstance(cache, sphinx.IntersphinxCache)
        for scheme in ('https://', 'http://'):
            hasCacheControl = isinstance(
                cache._session.adapters[scheme],
                cachecontrol.CacheControlAdapter,
            )
            if enableCache:
                assert hasCacheControl
            else:
                assert not hasCacheControl

    if clearCache:
        assert not tmpdir.listdir()
