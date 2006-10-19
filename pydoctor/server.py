from nevow.inevow import IResource
from nevow.rend import ChildLookupMixin
from nevow.static import File
from zope.interface import implements
from pydoctor import nevowhtml

class PyDoctorResource(ChildLookupMixin):
    implements(IResource)

    def __init__(self, system):
        self.system = system
        self.putChild('apidocs.css', File(nevowhtml.sibpath(__file__, 'templates/apidocs.css')))
        index = nevowhtml.IndexPage(None, self.system)
        self.putChild('', index)
        self.putChild('index.html', index)

    def childFactory(self, ctx, name):
        if not name.endswith('.html'):
            return None
        name = name[0:-5]
        if name not in self.system.allobjects:
            return None
        obj = self.system.allobjects[name]
        d = nevowhtml.__dict__
        for c in obj.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in d:
                pclass = d[n]
                break
        else:
            pclass = nevowhtml.CommonPage
        return pclass(None, obj)

    def renderHTTP(self, ctx):
        return nevowhtml.IndexPage(None, self.system).renderHTTP(ctx)


def resourceForPickleFile(pickleFilePath, configFilePath=None):
    import cPickle
    system = cPickle.load(open(pickleFilePath, 'rb'))
    from pydoctor.driver import getparser, readConfigFile
    if configFilePath is not None:
        system.options, _ = getparser().parse_args(['-c', configFilePath])
        readConfigFile(system.options)
    else:
        system.options, _ = getparser().parse_args([])
    return PyDoctorResource(system)
