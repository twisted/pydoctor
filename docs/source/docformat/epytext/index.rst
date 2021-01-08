Epytext
-------

Read the `epytext syntax reference <http://epydoc.sourceforge.net/manual-epytext.html>`_.

Check the :doc:`Epytext API Demo <./demo/index>`.

The epytext support has been herited from the ``epydoc`` software.
All markup should work except the indexed terms ``X{}`` tag, which has been removed.


Fields
^^^^^^

As a reminder, here are some of the supported *epytext* fields:

    - ``@cvar foo:``
    - ``@ivar foo:``
    - ``@var foo:``
    - ``@note``
    - ``@param bar:`` (synonym: ``@arg bar:``)
    - ``@type bar: C{list}``
    - ``@return:`` (synonym: ``@returns:``)
    - ``@rtype:`` (synonym: ``@returntype:``)
    - ``@raise ValueError:`` (synonym: ``@raises ValueError:``)
    - ``@see:`` (synonym: ``@seealso:``)
    - And more
