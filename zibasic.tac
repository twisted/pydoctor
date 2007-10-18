from twisted.application import service
from twisted.application import internet

from pydoctor import server, zopeinterface
from nevow import appserver

system = zopeinterface.ZopeInterfaceSystem()
system.addDirectory('pydoctor/test/interfaceclass')
system.process()
system.options.projectname = 'basic'

root = server.EditingPyDoctorResource(system)

application = service.Application("pydoctor demo")

internet.TCPServer(
    8080,
    appserver.NevowSite(
        root
    )
).setServiceParent(application)
