from pydoctor import extensions, zopeinterface

class ModuleMixin(extensions.ModuleMixin, zopeinterface.ZopeInterfaceModule):
    ...
class ClassMixin(extensions.ClassMixin, zopeinterface.ZopeInterfaceClass):
    ...
class FunctionMixin(extensions.FunctionMixin, zopeinterface.ZopeInterfaceFunction):
    ...
class AttributeMixin(extensions.AttributeMixin, zopeinterface.ZopeInterfaceAttribute):
    ...

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_mixins(ModuleMixin, ClassMixin, FunctionMixin, AttributeMixin)
    r.register_astbuilder_visitors(zopeinterface.ZopeInterfaceModuleVisitor)
    r.register_post_processor(zopeinterface.postProcess)
