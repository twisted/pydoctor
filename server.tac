from twisted.application import service
from twisted.application import internet

from nevow import appserver
from pydoctor.server import resourceForPickleFile

pickleFile = 'nevow-system.pickle'

root = resourceForPickleFile(pickleFile, 'mynevow.cfg')

application = service.Application("pydoctor demo")

internet.TCPServer(
    8080,
    appserver.NevowSite(
        root
    )
).setServiceParent(application)
