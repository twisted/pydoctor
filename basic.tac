from twisted.application import service
from twisted.application import internet

from pydoctor import server, model
from nevow import appserver

system = model.System()
b = system.defaultBuilder(system)
b.preprocessDirectory('pydoctor/test/basic')
for m in [b.analyseImports,
          b.extractDocstrings,
          b.finalStateComputations]:
    m()
system.options.projectname = 'basic'

root = server.EditingPyDoctorResource(system)

application = service.Application("pydoctor demo")

internet.TCPServer(
    8080,
    appserver.NevowSite(
        root
    )
).setServiceParent(application)
