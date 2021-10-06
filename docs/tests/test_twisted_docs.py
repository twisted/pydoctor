#
# Run tests after Twisted's the documentation is executed.
#
# These tests are designed to be executed inside tox, after bin/admin/build-apidocs.
#

import pathlib
import os
import pytest

BASE_DIR = pathlib.Path(os.environ.get('TOX_WORK_DIR', os.getcwd())) / 'twisted-apidocs-build'

# Failling test for https://github.com/twisted/pydoctor/issues/428
@pytest.mark.xfail
def test_IPAddress_implementations() -> None:
    """
    There is a flaw in the logic, currently.
    """

    implementations_that_currently_do_not_show_up = ['twisted.internet.address.IPv4Address', 
        'twisted.internet.address.IPv6Address', 
        'twisted.internet.address.HostnameAddress', 
        'twisted.internet.address.UNIXAddress']

    with open(BASE_DIR / 'twisted.internet.interfaces.IAddress.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in implementations_that_currently_do_not_show_up), page
