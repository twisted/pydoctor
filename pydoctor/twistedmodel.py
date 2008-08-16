"""Support for a few things specific to documenting Twisted."""

from pydoctor import model, ast_pp, zopeinterface

class TwistedModuleVisitor(zopeinterface.ZopeInterfaceModuleVisitor):

    def visitCallFunc_twisted_python_util_moduleMovedForSplit(self, funcName, node):
        # XXX this is rather fragile...
        origModuleName, newModuleName, moduleDesc, \
                        projectName, projectURL, globDict = node.args
        moduleDesc = ast_pp.pp(moduleDesc)[1:-1]
        projectName = ast_pp.pp(projectName)[1:-1]
        projectURL = ast_pp.pp(projectURL)[1:-1]
        modoc = """
%(moduleDesc)s

This module is DEPRECATED. It has been split off into a third party
package, Twisted %(projectName)s. Please see %(projectURL)s.

This is just a place-holder that imports from the third-party %(projectName)s
package for backwards compatibility. To use it, you need to install
that package.
""" % {'moduleDesc': moduleDesc,
       'projectName': projectName,
       'projectURL': projectURL}
        self.builder.current.docstring = modoc


class TwistedASTBuilder(zopeinterface.ZopeInterfaceASTBuilder):
    ModuleVistor = TwistedModuleVisitor

class TwistedSystem(zopeinterface.ZopeInterfaceSystem):
    defaultBuilder = TwistedASTBuilder

    def privacyClass(self, obj):
        o = obj
        while o:
            if o.fullName() == 'twisted.words.xish.yappsrt':
                return model.PrivacyClass.HIDDEN
            if isinstance(o, model.Package) and o.name == 'test':
                return model.PrivacyClass.HIDDEN
            o = o.parent
        return super(TwistedSystem, self).privacyClass(obj)

