"""
Tests for Sphinx integration.
"""

import datetime
import io
import string
import zlib
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple, cast

import cachecontrol
import pytest
import requests
from urllib3 import HTTPResponse

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from . import CapLog, FixtureRequest, MonkeyPatch, TempPathFactory
from pydoctor import model, sphinx



class PydoctorLogger:
    """
    Partial implementation of pydoctor.model.System.msg() that records
    logged messages.
    """

    def __init__(self) -> None:
        self.messages: List[Tuple[str, str, int]] = []

    def __call__(self, section: str, msg: str, thresh: int = 0) -> None:
        self.messages.append((section, msg, thresh))


class PydoctorNoLogger:
    """
    Partial implementation of pydoctor.model.System.msg() that asserts
    if any message is logged.
    """

    def __call__(self, section: str, msg: str, thresh: int = 0) -> None:
        assert False


class InvReader(sphinx.SphinxInventory):
    _logger: PydoctorLogger


class InvWriter(sphinx.SphinxInventoryWriter):
    _logger: PydoctorLogger


@pytest.fixture
def inv_reader() -> InvReader:
    return InvReader(logger=PydoctorLogger())


@pytest.fixture
def inv_reader_nolog() -> sphinx.SphinxInventory:
    return sphinx.SphinxInventory(logger=PydoctorNoLogger())


def get_inv_writer_with_logger(name: str = 'project_name', version: str = '1.2') -> Tuple[InvWriter, PydoctorLogger]:
    """
    @return: Tuple of a Sphinx inventory writer connected to the logger.
    """
    logger = PydoctorLogger()
    writer = InvWriter(
        logger=logger,
        project_name=name,
        project_version=version,
        )
    return writer, logger


@pytest.fixture
def inv_writer_nolog() -> sphinx.SphinxInventoryWriter:
    """
    @return: A Sphinx inventory writer that is connected to a null logger.
    """
    return sphinx.SphinxInventoryWriter(
        logger=PydoctorNoLogger(),
        project_name='project_name',
        project_version='2.3.0',
        )


IGNORE_SYSTEM = cast(model.System, 'ignore-system')
"""Passed as a System when we don't want the system to be accessed."""


def test_generate_empty_functional() -> None:
    """
    Functional test for index generation of empty API.

    Header is plain text while content is compressed.
    """
    inv_writer, logger = get_inv_writer_with_logger(
        name='project-name',
        version='1.2.0rc1',
        )

    output = io.BytesIO()
    @contextmanager
    def openFileForWriting(path: str) -> Iterator[io.BytesIO]:
        yield output
    inv_writer._openFileForWriting = openFileForWriting # type: ignore[assignment]

    inv_writer.generate(subjects=[], basepath='base-path')

    inventory_path = Path('base-path') / 'objects.inv'
    expected_log = [(
        'sphinx',
        f'Generating objects inventory at {inventory_path}',
        0
        )]
    assert expected_log == logger.messages

    expected_ouput = b"""# Sphinx inventory version 2
# Project: project-name
# Version: 1.2.0rc1
# The rest of this file is compressed with zlib.
x\x9c\x03\x00\x00\x00\x00\x01"""
    assert expected_ouput == output.getvalue()



def test_generateContent(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Return a string with inventory for all  targeted objects, recursive.
    """

    system = model.System()
    root1 = model.Package(system, 'package1')
    root2 = model.Package(system, 'package2')
    child1 = model.Package(system, 'child1', parent=root2)
    system.addObject(child1)
    subjects = [root1, root2]

    result = inv_writer_nolog._generateContent(subjects)

    expected_result = (
        b'package1 py:module -1 package1.html -\n'
        b'package2 py:module -1 package2.html -\n'
        b'package2.child1 py:module -1 package2.child1.html -\n'
        )
    assert expected_result == result


def test_generateLine_package(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Check inventory for package.
    """

    result = inv_writer_nolog._generateLine(
        model.Package(IGNORE_SYSTEM, 'package1'))

    assert 'package1 py:module -1 package1.html -\n' == result


def test_generateLine_module(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Check inventory for module.
    """

    result = inv_writer_nolog._generateLine(
        model.Module(IGNORE_SYSTEM, 'module1'))

    assert 'module1 py:module -1 module1.html -\n' == result


def test_generateLine_class(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Check inventory for class.
    """

    result = inv_writer_nolog._generateLine(
        model.Class(IGNORE_SYSTEM, 'class1'))

    assert 'class1 py:class -1 class1.html -\n' == result


def test_generateLine_function(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Check inventory for function.

    Functions are inside a module.
    """

    parent = model.Module(IGNORE_SYSTEM, 'module1')

    result = inv_writer_nolog._generateLine(
        model.Function(IGNORE_SYSTEM, 'func1', parent))

    assert 'module1.func1 py:function -1 module1.html#func1 -\n' == result


def test_generateLine_method(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Check inventory for method.

    Methods are functions inside a class.
    """

    parent = model.Class(IGNORE_SYSTEM, 'class1')

    result = inv_writer_nolog._generateLine(
        model.Function(IGNORE_SYSTEM, 'meth1', parent))

    assert 'class1.meth1 py:method -1 class1.html#meth1 -\n' == result


def test_generateLine_attribute(inv_writer_nolog: sphinx.SphinxInventoryWriter) -> None:
    """
    Check inventory for attributes.
    """

    parent = model.Class(IGNORE_SYSTEM, 'class1')

    result = inv_writer_nolog._generateLine(
        model.Attribute(IGNORE_SYSTEM, 'attr1', parent))

    assert 'class1.attr1 py:attribute -1 class1.html#attr1 -\n' == result


class UnknownType(model.Documentable):
    """
    Documentable type to help with testing.
    """


def test_generateLine_unknown() -> None:
    """
    When object type is uknown a message is logged and is handled as
    generic object.
    """
    inv_writer, logger = get_inv_writer_with_logger()

    result = inv_writer._generateLine(
        UnknownType(IGNORE_SYSTEM, 'unknown1'))

    assert 'unknown1 py:obj -1 unknown1.html -\n' == result
    assert [(
        'sphinx',
        "Unknown type <class 'pydoctor.test.test_sphinx.UnknownType'> for unknown1.",
        -1
        )] == logger.messages


def test_getPayload_empty(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return empty string.
    """

    content = b"""# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
x\x9c\x03\x00\x00\x00\x00\x01"""

    result = inv_reader_nolog._getPayload('http://base.ignore', content)

    assert '' == result


def test_getPayload_content(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return content as string.
    """

    payload = "first_line\nsecond line\nit's a snake: \U0001F40D"
    content = b"""# Ignored line
# Project: some-name
# Version: 2.0
# commented line.
""" + zlib.compress(payload.encode('utf-8'))

    result = inv_reader_nolog._getPayload('http://base.ignore', content)

    assert payload == result


def test_getPayload_invalid_uncompress(inv_reader: InvReader) -> None:
    """
    Return empty string and log an error when failing to uncompress data.
    """
    base_url = 'http://tm.tld'
    content = b"""# Project: some-name
# Version: 2.0
not-valid-zlib-content"""

    result = inv_reader._getPayload(base_url, content)

    assert '' == result
    assert [(
        'sphinx', 'Failed to uncompress inventory from http://tm.tld', -1,
        )] == inv_reader._logger.messages


def test_getPayload_invalid_decode(inv_reader: InvReader) -> None:
    """
    Return empty string and log an error when failing to uncompress data.
    """
    payload = b'\x80'
    base_url = 'http://tm.tld'
    content = b"""# Project: some-name
# Version: 2.0
""" + zlib.compress(payload)

    result = inv_reader._getPayload(base_url, content)

    assert '' == result
    assert [(
        'sphinx', 'Failed to decode inventory from http://tm.tld', -1,
        )] == inv_reader._logger.messages


def test_getLink_not_found(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return None if link does not exists.
    """

    assert None is inv_reader_nolog.getLink('no.such.name')


def test_getLink_found(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return the link from internal state.
    """

    inv_reader_nolog._links['some.name'] = ('http://base.tld', 'some/url.php')

    assert 'http://base.tld/some/url.php' == inv_reader_nolog.getLink('some.name')


def test_getLink_self_anchor(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return the link with anchor as target name when link end with $.
    """

    inv_reader_nolog._links['some.name'] = ('http://base.tld', 'some/url.php#$')

    assert 'http://base.tld/some/url.php#some.name' == inv_reader_nolog.getLink('some.name')


def test_update_functional(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Functional test for updating from an empty inventory.
    """

    payload = (
        b'some.module1 py:module -1 module1.html -\n'
        b'other.module2 py:module 0 module2.html Other description\n'
        )
    # Patch URL loader to avoid hitting the system.
    content = b"""# Sphinx inventory version 2
# Project: some-name
# Version: 2.0
# The rest of this file is compressed with zlib.
""" + zlib.compress(payload)

    url = 'http://some.url/api/objects.inv'

    inv_reader_nolog.update({url: content}, url)

    assert 'http://some.url/api/module1.html' == inv_reader_nolog.getLink('some.module1')
    assert 'http://some.url/api/module2.html' == inv_reader_nolog.getLink('other.module2')


def test_update_bad_url(inv_reader: InvReader) -> None:
    """
    Log an error when failing to get base url from url.
    """

    inv_reader.update({}, 'really.bad.url')

    assert inv_reader._links == {}
    expected_log = [(
        'sphinx', 'Failed to get remote base url for really.bad.url', -1
        )]
    assert expected_log == inv_reader._logger.messages


def test_update_fail(inv_reader: InvReader) -> None:
    """
    Log an error when failing to get content from url.
    """

    inv_reader.update({}, 'http://some.tld/o.inv')

    assert inv_reader._links == {}
    expected_log = [(
        'sphinx',
        'Failed to get object inventory from http://some.tld/o.inv',
        -1,
        )]
    assert expected_log == inv_reader._logger.messages


def test_parseInventory_empty(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return empty dict for empty input.
    """

    result = inv_reader_nolog._parseInventory('http://base.tld', '')

    assert {} == result


def test_parseInventory_single_line(inv_reader_nolog: sphinx.SphinxInventory) -> None:
    """
    Return a dict with a single member.
    """

    result = inv_reader_nolog._parseInventory(
        'http://base.tld', 'some.attr py:attr -1 some.html De scription')

    assert {'some.attr': ('http://base.tld', 'some.html')} == result


def test_parseInventory_spaces() -> None:
    """
    Sphinx inventory lines always contain 5 values, separated by spaces.
    However, the first and fifth value can contain internal spaces.
    The parser must be able to tell apart separators from internal spaces.
    """

    # Space in first (name) column.
    assert sphinx._parseInventoryLine(
        'key function std:term -1 glossary.html#term-key-function -'
        ) == (
        'key function', 'std:term', -1, 'glossary.html#term-key-function', '-'
        )

    # Space in last (display name) column.
    assert sphinx._parseInventoryLine(
        'doctest-execution-context std:label -1 library/doctest.html#$ What’s the Execution Context?'
        ) == (
        'doctest-execution-context', 'std:label', -1, 'library/doctest.html#$', 'What’s the Execution Context?'
        )

    # Space in both first and last column.
    assert sphinx._parseInventoryLine(
        'async def std:label -1 reference/compound_stmts.html#async-def Coroutine function definition'
        ) == (
        'async def', 'std:label', -1, 'reference/compound_stmts.html#async-def', 'Coroutine function definition'
        )


def test_parseInventory_invalid_lines(inv_reader: InvReader) -> None:
    """
    Skip line and log an error.
    """

    base_url = 'http://tm.tld'
    content = (
        'good.attr py:attribute -1 some.html -\n'
        'missing.display.name py:attribute 1 some.html\n'
        'bad.attr bad format\n'
        'very.bad\n'
        '\n'
        'good.again py:module 0 again.html -\n'
        )

    result = inv_reader._parseInventory(base_url, content)

    assert {
        'good.attr': (base_url, 'some.html'),
        'good.again': (base_url, 'again.html'),
        } == result
    assert [
        (
            'sphinx',
            'Failed to parse line "missing.display.name py:attribute 1 some.html" for http://tm.tld',
            -1,
            ),
        (
            'sphinx',
            'Failed to parse line "bad.attr bad format" for http://tm.tld',
            -1,
            ),
        ('sphinx', 'Failed to parse line "very.bad" for http://tm.tld', -1),
        ('sphinx', 'Failed to parse line "" for http://tm.tld', -1),
        ] == inv_reader._logger.messages


def test_parseInventory_type_filter(inv_reader: InvReader) -> None:
    """
    Ignore entries that don't have a 'py:' type field.
    """

    base_url = 'https://docs.python.org/3'
    content = (
        'dict std:label -1 reference/expressions.html#$ Dictionary displays\n'
        'dict py:class 1 library/stdtypes.html#$ -\n'
        'dict std:2to3fixer 1 library/2to3.html#2to3fixer-$ -\n'
        )

    result = inv_reader._parseInventory(base_url, content)

    assert {
        'dict': (base_url, 'library/stdtypes.html#$'),
        } == result
    assert [] == inv_reader._logger.messages


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
    def test_toTimedelta(self, amount: int, unit: str) -> None:
        """
        A parsed max age dictionary consists of valid arguments to
        L{datetime.timedelta}, and the constructed L{datetime.timedelta}
        matches the specification.
        """
        maxAge = f"{amount}{unit}"
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
    been read.  This mimics the behavior of L{http.client.HTTPResponse} in the
    standard library.
    """

    def read(self, size: Optional[int] = None) -> bytes:
        data = super().read(size)
        if self.tell() >= len(self.getvalue()):
            self.close()
        return data


def test_ClosingBytesIO() -> None:
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
    def send_returns(self, monkeypatch: MonkeyPatch) -> Callable[[HTTPResponse], MonkeyPatch]:
        """
        Return a function that patches
        L{requests.adapters.HTTPAdapter.send} so that it returns the
        provided L{requests.Response}.
        """
        def send_returns(urllib3_response: HTTPResponse) -> MonkeyPatch:
            def send(
                    self: requests.adapters.HTTPAdapter,
                    request: requests.PreparedRequest,
                    **kwargs: object
                    ) -> requests.Response:
                response: requests.Response
                response = self.build_response(request, urllib3_response)
                return response

            monkeypatch.setattr(
                requests.adapters.HTTPAdapter,
                "send",
                send,
            )

            return monkeypatch
        return send_returns

    def test_cache(self, tmp_path: Path, send_returns: Callable[[HTTPResponse], None]) -> None:
        """
        L{IntersphinxCache.get} caches responses to the file system.
        """
        url = "https://cache.example/objects.inv"
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
            cachePath=str(tmp_path),
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
            cachePath=str(tmp_path),
            maxAgeDictionary={"weeks": 1}
        )

        assert readsCacheFromFileSystem.get(url) == content

    def test_getRaisesException(self, caplog: CapLog) -> None:
        """
        L{IntersphinxCache.get} returns L{None} if an exception is
        raised while C{GET}ing a URL and logs the exception.
        """

        class _TestException(Exception):
            pass

        class _RaisesOnGet:

            @staticmethod
            def get(url: str) -> bytes:
                raise _TestException()

        session = cast(requests.Session, _RaisesOnGet)
        cache = sphinx.IntersphinxCache(session=session)

        assert cache.get("some url") is None

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert caplog.records[0].exc_info is not None
        assert caplog.records[0].exc_info[0] is _TestException


@pytest.fixture(scope='module')
def cacheDirectory(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Path:
    name = request.module.__name__.split('.')[-1]
    return tmp_path_factory.mktemp(f'{name}-cache')

@given(
    clearCache=st.booleans(),
    enableCache=st.booleans(),
    cacheDirectoryName=st.text(
        alphabet=sorted(set(string.printable) - set('\\/:*?"<>|\x0c\x0b\t\r\n')),
        min_size=1,
        max_size=32,            # Avoid upper length on path
    ),
    maxAgeAmount=maxAgeAmounts,
    maxAgeUnit=maxAgeUnits,
)
@settings(max_examples=700, deadline=None)
def test_prepareCache(
        cacheDirectory: Path,
        clearCache: bool,
        enableCache: bool,
        cacheDirectoryName: str,
        maxAgeAmount: int,
        maxAgeUnit: str,
) -> None:
    """
    The cache directory is deleted when C{clearCache} is L{True}; an
    L{IntersphinxCache} is created with a session on which is mounted
    C{cachecontrol.CacheControlAdapter} for C{http} and C{https} URLs.
    """

    # Windows doesn't like paths ending in a space or dot.
    assume(cacheDirectoryName[-1] not in '. ')

    # These DOS device names still have special meaning in modern Windows.
    assume(cacheDirectoryName.upper() not in {'CON', 'PRN', 'AUX', 'NUL'})
    assume(not cacheDirectoryName.upper().startswith('COM'))
    assume(not cacheDirectoryName.upper().startswith('LPT'))

    cacheDirectory.mkdir(exist_ok=True)
    for child in cacheDirectory.iterdir():
        child.unlink()
    with open(cacheDirectory / cacheDirectoryName, 'w'):
        pass

    try:
        cache = sphinx.prepareCache(
            clearCache=clearCache,
            enableCache=enableCache,
            cachePath=str(cacheDirectory),
            maxAge=f"{maxAgeAmount}{maxAgeUnit}"
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
        assert not cacheDirectory.exists()
