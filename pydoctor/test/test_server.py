from pydoctor.test.test_astbuilder import fromText
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

## doesn't work, as the module doesn't exist on disk, ho hum

## def test_edit_renders_ok():
##     m = fromText('''
##     """This is a docstring!"""
##     class C:
##         pass
##     ''', modname="mod")
##     root = server.EditingPyDoctorResource(m.system)
##     assert 'This is a docstring!' in getTextOfPage(root, 'edit', args=dict(ob=('mod',)))
