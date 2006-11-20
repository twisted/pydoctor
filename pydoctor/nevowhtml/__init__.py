from pydoctor import model, twisted, epydoc2stan

from nevow import loaders, tags, page, flat, inevow
from zope.interface import implements

from pydoctor.nevowhtml.writer import NevowWriter

def _hack_nevow():
    from nevow.flat.flatstan import serialize
    from nevow.flat import registerFlattener
    def PrecompiledSlotSerializer(original, context):
        """
        Serialize a pre-compiled slot.

        Return the serialized value of the slot or raise a KeyError if it has no
        value.
        """
        # Precompilation should _not_ be happening at this point, but Nevow is very
        # sloppy about precompiling multiple times, so sometimes we are in a
        # precompilation context.  In this case, there is nothing to do, just
        # return the original object.  The case which seems to exercise this most
        # often is the use of a pattern as the stan document given to the stan
        # loader.  The pattern has already been precompiled, but the stan loader
        # precompiles it again.  This case should be eliminated by adding a loader
        # for precompiled documents.
        if context.precompile:
            warnings.warn(
                "[v0.9.9] Support for multiple precompilation passes is deprecated.",
                PendingDeprecationWarning)
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
