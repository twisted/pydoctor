Usage
=====

.. contents::

Most common options
-------------------

The following exemple uses all most common options to generate ``pydoctor``'s own API docs under the ``docs/api`` folder.
It will add a link to the project website in all pages header, show a link to source code aside every documented elements and resolve links to standard library objects.

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

.. note:: This exemple assume that you have cloned and installed ``pydoctor`` and you are running the ``pydoctor`` build from Unix and the current directory is the root folder of the Python project.

.. warning:: The ``--html-viewsource-base`` argument  should point to a tag or a commit SHA rather than a branch since line
    numbers aren't going to match otherwise when commits are added to the branch after the documentation has been published.

``__all__`` re-export
---------------------

A documented element which is defined in ``my_package.core.session`` module and included in the ``__all__`` special variable of ``my_package``
- in the ``__init__.py`` that it is imported into - will end up in the documentation of ``my_package``.

For instance, in the following exemple, the documentation of ``MyClass`` will be moved to the root package, ``my_package``.

::

  ├── CONTRIBUTING.rst
  ├── LICENSE.txt
  ├── README.rst
  ├── my_package
  │   ├── __init__.py     <-- Re-export `my_package.core.session.MyClass`
  │   ├── core                as `my_package.MyClass`
  │   │   ├── __init__.py
  │   │   ├── session.py  <-- Defines `MyClass`

The content of ``my_package/__init__.py`` includes::

  from .core.session import MyClass
  __all__ = ['MyClass', 'etc.']

Document part of your package
-----------------------------

Sometimes, only a couple classes or modules are part of your public API, not all classes and modules need to be documented.

You can choose to document only a couple classes or modules with the following cumulative configuration option::

  --html-subject=pydoctor.zopeinterface.ZopeInterfaceSystem

This will generate only ``pydoctor.zopeinterface.ZopeInterfaceSystem.html``.
The ``--html-subject`` argument acts like a filter.

.. warning:: The ``index.html`` and other index files won't be generated, you need to link to the specific HTML pages.


Publish your documentation
--------------------------

``pydoctor`` output are static HTML pages without no extra server-side support.

With Github actions
~~~~~~~~~~~~~~~~~~~

Here is an exemple to automatically generate and publish your documentation with Github actions and publish the documentation to the default Github pages website.

::

    name: publish-pydoctor-apidocs
    on:
    - push

    jobs:
      deploy:
        runs-on: ubuntu-latest

        steps:
        - uses: actions/checkout@master
        - name: Set up Python 3.8
          uses: actions/setup-python@v2
          with:
            python-version: 3.8

        - name: Install package
          run: |
            python -m pip install --upgrade pip setuptools wheel
            python -m pip install .
            python -m pip install pydoctor

        - name: Generate pydoctor documentation
          run: |
            # Allow pydoctor to exit with non-zero status code
            set +e

            # Run pydoctor build
            pydoctor \
                --project-name=(projectname) \
                --project-url=https://github.com/$GITHUB_REPOSITORY \
                --html-viewsource-base=https://github.com/$GITHUB_REPOSITORY/tree/$GITHUB_SHA \
                --make-html \
                --html-output=./apidocs \
                --project-base-dir="$(pwd)" \
                --docformat=restructuredtext \
                --intersphinx=https://docs.python.org/3/objects.inv \
                ./(packagedirectory)

        - name: Publish pydoctor documentation to the gh-pages branch
          uses: peaceiris/actions-gh-pages@v3
          with:
            github_token: ${{ secrets.GITHUB_TOKEN }}
            publish_dir: ./apidocs
            commit_message: "Generate pydoctor documentation"

.. note:: As mentionned in the ``actions-gh-pages`` `documentation`__, the first workflow run won't actually publish the documentation to Github pages.
    Github pages needs to be enabled afterwards in the repo settings, select ``gh-pages`` branch, then re-run your workflow.

    The website we'll be at https://(user).github.io/(repo)/

    __ https://github.com/peaceiris/actions-gh-pages

.. With Sphinx and Read The Docs
.. ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. .. note:: Documentation to come!

Sphinx Integration
------------------

Sphinx object inventories can be used to create links in both ways between
documentation generated by pydoctor and by Sphinx.


Linking from pydoctor to external API docs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It can link to external API documentation using a Sphinx objects inventory
with the following cumulative configuration option::

    --intersphinx=https://docs.python.org/3/objects.inv

Then, your interpreted text, with backtics (`````) using `restructuredtext` and with ``L{}`` tag using `epytext`, will be linked to the Python element. Exemple::

  `datetime.datetime`
  L{datetime.datetime}


Linking from Sphinx to your pydoctor API docs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pydoctor's HTML generator will also generate a Sphinx objects inventory that can be used with the following mapping:

* packages, modules -> ``:py:mod:``
* classes -> ``:py:class:``
* functions -> ``:py:func:``
* methods -> ``:py:meth:``
* attributes -> ``:py:attr:``

Use this mapping in Sphinx by configure the `intersphinx extension`__.

__ https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

For an up to date lists of API links,
run pydoctor before building the Sphinx documentation.

You can use the `--make-intersphinx` option to only generate the object inventory file.

You will then reference this file inside the Sphinx `intersphinx_mapping`.

Note that relative paths are relative to the Sphinx source directory.
You might need to exit the source and reference the build directory::

    intersphinx_mapping = {
        'twisted': ('https://twistedmatrix.com/documents/current/api/', '../../build/apidocs/objects.inv'),
    }

Link to elements :py:func:`with custom text <twisted:twisted.web.client.urlunparse>` with::

    :py:func:`with custom text <twisted:twisted.web.client.urlunparse>`

Link to elements with default label :py:class:`twisted:twisted.web.client.HTTPDownloader` with::

    :py:class:`twisted:twisted.web.client.HTTPDownloader`

Possible links are::

  :py:func:`Twisted urlunparse() function <twisted:twisted.web.client.urlunparse>`

  :py:mod:`twisted:twisted`
  :py:mod:`twisted:twisted.web.client`
  :py:func:`twisted:twisted.web.client.urlunparse`
  :py:class:`twisted:twisted.web.client.HTTPDownloader`
  :py:meth:`twisted:twisted.mail.smtp.SMTPClient.connectionMade`
  :py:attr:`twisted:twisted.protocols.amp.BinaryBoxProtocol.boxReceiver`


Building pydoctor together with Sphinx HTML build
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When running pydoctor with HTML generation it will generate a set of static
HTML files that can be used any HTTP server.

Under some circumstances (ex Read The Docs) you might want to trigger the
pydoctor API docs build together with the Sphinx build.

This can be done by using the :py:mod:`pydoctor.sphinx_ext.build_apidocs` extension.

Inside your Sphinx `conf.py` file enable and configure the extension in this
way.::

    extensions.append("pydoctor.sphinx_ext.build_apidocs)

    pydoctor_args = [
        '--project-name=YOUR-PROJECT-NAME',
        '--project-version=YOUR-PUBLIC-VERSION,
        '--project-url=YOUR-PROJECT-HOME-URL',
        '--docformat=epytext',
        '--intersphinx=https://docs.python.org/3/objects.inv',
        '--html-viewsource-base=https://github.com/ORG/REPO/tree/default',
        '--html-output={outdir}/api',
        '--project-base-dir=path/to/source/code',
        'path/to/source/code/package1'
        ]

    pydoctor_url_path = '/en/{rtd_version}/api/'

You can pass almost any argument to `pydoctor_args`
in the same way you call `pydoctor` from the command line.

You don't need to pass the `--make-html`, `--make-intersphinx` or `--quiet`
arguments.
The extension will add them automatically.

The `pydoctor_url_path` is an URL path,
relative to your public API documentation site.
`{rtd_version}` will be replaced with the Read The Docs version (`stable` , `latest`, tag name).
You only need to define this argument is you need to have intersphinx links
from your Sphinx narrative documentation to your pydoctor API documentation.

As a hack to integrate the pydoctor API docs `index.html` with the Sphinx TOC
and document reference, you can create an `index.rst` at the location where
the pydoctor `index.html` is hosted.
The Sphinx index.html will be generated during the Sphinx build process and
later overwritten by the pydoctor build process.

It is possible to call pydoctor multiple times (with different arguments) as
part of the same build process.
For this you need to define `pydoctor_args` as a dict.
The key is the human readable build name and the value for each dict member
is the list of arguments.
See pydoctor's own `conf.py <https://github.com/twisted/pydoctor/blob/master/docs/source/conf.py>`_
for usage example.


Customize builds
----------------

Custom HTML
~~~~~~~~~~~

They are 3 placeholders designed to be overwritten to include custom HTML into the pages.
All empty by default. 

- ``header.html``: At the very beginning of the body
- ``pageHeader.html``: After the main header, before the page title
- ``footer.html``: At the very end of the body

To overwrite a placeholder, write your cusom HTLM files to a folder 
and use the following option::

  --html-template-dir=./pydoctor_templates

.. note::

  If you want more customization, you can override the defaults 
  HTML and CSS templates in `pydoctor/templates <https://github.com/twisted/pydoctor/tree/master/pydoctor/templates>`_ with the same method. 

Custom System class
~~~~~~~~~~~~~~~~~~~

You can subclass the :py:class:`pydoctor:pydoctor.zopeinterface.ZopeInterfaceSystem` and pass your custom class dotted name with the following argument::

  --system-class=mylib._pydoctor.CustomSystem

System class allows you to dynamically show/hide classes or methods.
This is also used by the Twisted project to handle deprecation.

See the :py:class:`twisted:twisted.python._pydoctor.TwistedSystem` custom class documentation. Naviguate to the source code for a better overview.

.. warning:: PyDoctor does not have a stable API yet. Custom builds are prone to break.

Custom writer
~~~~~~~~~~~~~

You can subclass the :py:class:`pydoctor:pydoctor.templatewriter.writer.TemplateWriter` and pass your custom class dotted name with the following argument::


  --writer-class=mylib._pydoctor.CustomTemplateWriter

.. warning:: Pydoctor does not have a stable API yet. Custom builds are prone to break.
