This is 'pydoctor', an API documentation generator that works by
static analysis.

It was written primarily to replace epydoc for the purposes of the
Twisted project as epydoc has difficulties with zope.interface.  If it
happens to work for your code too, that's a nice bonus at this stage :)

pydoctor puts a fair bit of effort into resolving imports and
computing inheritance hierarchies and, as it aims at documenting
Twisted, knows about zope.interface's declaration API and can present
information about which classes implement which interface, and vice
versa.

The default HTML generator uses Nevow, which means that it requires
Twisted too.  It requires Nevow 0.9.18 or newer -- your Nevow is new
enough if "from nevow import page" succeeds.

There are some more notes in the doc/ subdirectory.
