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
    This test ensures all important subclasses of IAddress show up in the IAddress class page documentation.
    """

    show_up = ['twisted.internet.address.IPv4Address', 
        'twisted.internet.address.IPv6Address', 
        'twisted.internet.address.HostnameAddress', 
        'twisted.internet.address.UNIXAddress']

    with open(BASE_DIR / 'twisted.internet.interfaces.IAddress.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in show_up), page

# Test for https://github.com/twisted/pydoctor/issues/505
def test_web_template_api() -> None:
    """
    This test ensures all important members of the twisted.web.template 
    module are documented at the right place
    """

    exists = ['twisted.web.template.Tag.html', 
        'twisted.web.template.slot.html', 
        'twisted.web.template.Comment.html', 
        'twisted.web.template.CDATA.html',
        'twisted.web.template.CharRef.html',
        'twisted.web.template.TagLoader.html',
        'twisted.web.template.XMLString.html',
        'twisted.web.template.XMLFile.html',
        'twisted.web.template.Element.html',]
    for e in exists:
        assert (BASE_DIR / e).exists(), f"{e} not found"
    
    show_up = [
        'twisted.web.template.renderer',
        'twisted.web.template.flatten',
        'twisted.web.template.flattenString', 
        'twisted.web.template.renderElement']

    with open(BASE_DIR / 'twisted.web.template.html') as stream:
        page = stream.read()
        assert all(impl in page for impl in show_up), page
