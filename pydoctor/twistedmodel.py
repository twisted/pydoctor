from pydoctor import model
from pydoctor import twisted

# this module now exists only for backward compatibility reasons.

class TwistedSystem(model.System):
    defaultBuilder = twisted.TwistedASTBuilder

TwistedClass = twisted.TwistedClass
