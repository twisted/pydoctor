from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage
from pydoctor import server
from nevow import context, testutil, appserver, flat, inevow
from twisted.internet.defer import maybeDeferred

def deferredResult(*args):
    hack = []
    maybeDeferred(*args).addCallback(lambda x:hack.append(x))
    return hack[0]

def getTextOfPage(root, page, args=None):
    """This perpetrates several awful hacks."""
    r = testutil.FakeRequest(args=args)
    r.postpath = [page]
    ctx = context.RequestContext(tag=r)
    pageContext = deferredResult(appserver.NevowSite(root).getPageContextForRequestContext, ctx)
    while 1:
        html = deferredResult(pageContext.tag.renderHTTP, pageContext)
        if isinstance(html, str):
            return r.v + html
        res = inevow.IResource(html)
        pageContext = context.PageContext(tag=res, parent=pageContext)

def test_simple():
    m = fromText('''
    """This is a docstring!"""
    class C:
        pass
    ''', modname="mod")
    root = server.PyDoctorResource(m.system)
    assert 'This is a docstring!' in getTextOfPage(root, 'mod.html')

def test_edit_renders_ok():
    system = processPackage('localimporttest')
    root = server.EditingPyDoctorResource(system)
    args = {'ob':['localimporttest.mod1.C']}
    result = getTextOfPage(root, 'edit', args=args)
    # very weak, but it's an assert that things didn't explode
    assert 'textarea' in result

    args = {'ob':['does.not.exist']}
    result = getTextOfPage(root, 'edit', args=args)
    assert 'An error occurred' in result
