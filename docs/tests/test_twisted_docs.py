#
# Run tests after Twisted's the documentation is executed.
#
# These tests are designed to be executed inside tox, after bin/admin/build-apidocs.
# Alternatively this can be excuted manually from the project root folder like:
#   pytest docs/tests/test_twisted_docs.py

from . import get_toxworkdir_subdir

BASE_DIR = get_toxworkdir_subdir('twisted-apidocs-build')

# Test for https://github.com/twisted/pydoctor/issues/428
def test_IPAddress_implementations() -> None:
    """
    This test ensure all important subclasses of IAddress show up in the IAddress class page documentation.
    """

    show_up = ['twisted.internet.address.IPv4Address', 
        'twisted.internet.address.IPv6Address', 
        'twisted.internet.address.HostnameAddress', 
        'twisted.internet.address.UNIXAddress']

    with open(BASE_DIR / 'twisted.internet.interfaces.IAddress.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in show_up), page
