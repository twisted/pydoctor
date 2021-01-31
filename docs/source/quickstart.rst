Quick start
===========

Installation
------------

Pydoctor can be installed from PyPI::

   $ pip install -U pydoctor[rst]

*This will also install docutils*. 

Alternatively, you can install pydoctor without reStructuredText 
support, only Epytext will be recognized::

   $ pip install -U pydoctor

Example
-------

The following example uses all most common options to generate ``pydoctor``'s own 
API docs under the ``docs/api`` folder. It will add a link to the project website 
in all pages header, show a link to source code aside every documented elements 
and resolve links to standard library objects.

The result looks like `this <api/pydoctor.html>`_. 

::

    pydoctor \
        --project-name=pydoctor \
        --project-version=1.2.0 \
        --project-url=https://github.com/twisted/pydoctor/ \
        --html-viewsource-base=https://github.com/twisted/pydoctor/tree/20.7.2 \
        --make-html \
        --html-output=docs/api \
        --project-base-dir="$(pwd)" \
        --docformat=epytext \
        --intersphinx=https://docs.python.org/3/objects.inv \
        ./pydoctor

.. note:: This example assume that you have cloned and installed ``pydoctor`` 
    and you are running the ``pydoctor`` build from Unix and the current directory 
    is the root folder of the Python project.

.. warning:: The ``--html-viewsource-base`` argument should point to a tag or a 
    commit SHA rather than a branch since line numbers are not going to match otherwise 
    when commits are added to the branch after the documentation has been published.

Publish your documentation
--------------------------

Output files are static HTML pages without no extra server-side support.

Here is a `GitHub action example <publish-github-action.html>`_ to automatically 
publish your API documentation to your default GitHub pages website.