This is 'pydoctor', an API documentation generator that works by
static analysis.

It was written primarily to replace epydoc for the purposes of the
Twisted project as epydoc has difficulties with zope.interface.  If it
happens to work for your code too, that's a nice bonus :)

pydoctor puts a fair bit of effort into resolving imports and
computing inheritance hierarchies and, as it aims at documenting
Twisted, knows about zope.interface's declaration API and can present
information about which classes implement which interface, and vice
versa.

The default HTML generator requires Twisted.

There are some more notes in the doc/ subdirectory.


Sphinx Integration
------------------

HTML generator will also generate a Sphinx objects inventory using the
following mapping:

* packages, modules -> py:mod:
* classes -> py:class:
* functions -> py:func:
* methods -> py:meth:
* attributes -> py:attr:

Configure Sphinx intersphinx extension:

    intersphinx_mapping = {
        'pydoctor': ('http://domain.tld/api', None),
    }

Use external references::

    :py:func:`External API <pydoctor:pydoctor.model.Documentable.reparent>`

    :py:mod:`pydoctor:pydoctor`
    :py:mod:`pydoctor:pydoctor.model`
    :py:func:`pydoctor:pydoctor.driver.getparser`
    :py:class:`pydoctor:pydoctor.model.Documentable`
    :py:meth:`pydoctor:pydoctor.model.Documentable.reparent`
    :py:attr:`pydoctor:pydoctor.model.Documentable.kind`

It can link to external API documentation using Sphinx objects inventory using
the following cumulative configuration option::

    --intersphinx=http://sphinx-doc.org/objects.inv
