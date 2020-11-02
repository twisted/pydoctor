Development
===========

.. imclude:: ../../CONTRINUTING.rst

Design Notes
------------

I guess I've always been interested in more-or-less static analysis of
Python code and have over time developed some fairly strong opinions
on the Right Way (tm) to do it.

The first of these is that pydoctor works on an entire *system* of
packages and modules, not just a .py file at a time.

The second, and this only struck me with full force as I have written
pydoctor, is that it's much the best approach to proceed
incrementally, and outside-in.  First, you scan the directory
structure to and compute the package/module structure, then parse each
module, then do some analysis on what you've found, then generate
html.

It's extremely handy to be able to pickle a system in between each
step.

Finally, pydoctor should never crash, no matter what code you feed it
(this seems a basic idea for a documentation generator, but it's not
that universally applied, it seems).  Missing information is OK,
crashing out is not.  This probably isn't as true as it should be at
the moment.

