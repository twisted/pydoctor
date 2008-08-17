from twisted.application import service
from twisted.application import internet

from pydoctor import server, model
from nevow import appserver

system = model.System()
system.addPackage('pydoctor/test/testpackages/basic')
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
