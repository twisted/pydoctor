from pydoctor import extensions, deprecate

def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
    r.register_astbuilder_visitors(deprecate.ModuleVisitor)
