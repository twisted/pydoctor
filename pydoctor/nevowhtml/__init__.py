from pydoctor import model, twisted, epydoc2stan

from nevow import loaders, tags, page, flat, inevow
from zope.interface import implements

from pydoctor.nevowhtml.writer import NevowWriter

def _hack_nevow():
    from nevow.flat.flatstan import serialize
    from nevow.flat import registerFlattener
    def PrecompiledSlotSerializer(original, context):
        if context.precompile:
            return original
        try:
            data = context.locateSlotData(original.name)
        except KeyError:
            if original.default is None:
                raise
            data = original.default
        return serialize(data, context)
    from nevow.stan import _PrecompiledSlot
    registerFlattener(PrecompiledSlotSerializer, _PrecompiledSlot)

_hack_nevow()
