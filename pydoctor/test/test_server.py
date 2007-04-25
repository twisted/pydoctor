from pydoctor.test.test_astbuilder import fromText
from pydoctor.test.test_packages import processPackage
from pydoctor import server
from nevow import context, testutil, appserver, flat, inevow
from twisted.internet.defer import maybeDeferred

def deferredResult(*args):
    hack = []
    err = []
    def cb(x):
        hack.append(x)
    def eb(f):
        err.append(f)
    maybeDeferred(*args).addCallbacks(cb, eb)
    if hack:
        return hack[0]
    elif err:
        f = err[0]
        raise f.type, f.value, f.tb
    else:
        assert 0, "time to start using trial..."

def getTextOfPage(root, page, args=None, return_request=False):
    """This perpetrates several awful hacks."""
    if args is not None:
        args_ = {}
        for k, v in args.iteritems():
            args_[k] = [v]
        args = args_
    r = testutil.FakeRequest(args=args)
    r.postpath = [page]
    ctx = context.RequestContext(tag=r)
    pageContext = deferredResult(appserver.NevowSite(root).getPageContextForRequestContext, ctx)
    while 1:
        html = deferredResult(pageContext.tag.renderHTTP, pageContext)
        if isinstance(html, str):
            if return_request:
                return r.v + html, r
            else:
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
    args = {'ob':'localimporttest.mod1.C'}
    result = getTextOfPage(root, 'edit', args=args)
    # very weak, but it's an assert that things didn't explode
    assert 'textarea' in result

    args = {'ob':'does.not.exist'}
    result = getTextOfPage(root, 'edit', args=args)
    assert 'An error occurred' in result

def performEdit(root, ob, newDocstring):
    args = {'ob':ob.fullName(), 'docstring':newDocstring,
            'action':'Submit'}
    result, r = getTextOfPage(root, 'edit', args=args, return_request=True)
    assert not result
    assert ob.fullName() in r.redirected_to

def test_edit():
    system = processPackage('localimporttest')
    root = server.EditingPyDoctorResource(system)

    ob = system.allobjects['localimporttest.mod1.C']
    docstring = root.currentDocstringForObject(ob)
    assert docstring == ob.docstring

    newDocstring = '"""This *is* a docstring"""'
    performEdit(root, ob, newDocstring)
    docstring = root.currentDocstringForObject(ob)
    assert docstring == eval(newDocstring)
    assert ob.docstring != docstring

    result = getTextOfPage(root, 'localimporttest.mod1.C.html')
    assert eval(newDocstring) in result

    result = getTextOfPage(root, 'localimporttest.mod1.html')
    assert eval(newDocstring) in result

def test_edit_direct():
    system = processPackage('localimporttest')
    root = server.EditingPyDoctorResource(system)

    ob = system.allobjects['localimporttest.mod1.C']
    docstring = root.currentDocstringForObject(ob)
    assert docstring == ob.docstring

    newDocstring = '"""This *is* a docstring"""'
    root.newDocstring('xxx', ob, ob, newDocstring)
    docstring = root.currentDocstringForObject(ob)
    assert docstring == eval(newDocstring)
    assert ob.docstring != docstring

def test_diff():
    system = processPackage('localimporttest')
    root = server.EditingPyDoctorResource(system)

    ob = system.allobjects['localimporttest.mod1.C']

    performEdit(root, ob, repr("This *is* a docstring"))

    args = {'ob':ob.fullName(), 'revA':'0', 'revB':'1'}
    difftext = getTextOfPage(root, 'diff', args)
    assert "*is*" in difftext
