:orphan:

Simple ReadTheDocs config to publish API docs
---------------------------------------------

Here is an example of a simple ReadTheDocs integration to automatically
generate your documentation with Pydoctor. 

.. note:: This kind of integration should
    not be confused with `Sphinx support <sphinx-integration.html>`_ that can also be used to run 
    pydoctor inside ReadTheDocs as part of the standard Sphinx build process. 
    
    This page, on the other hand, documents **how to simply run pydoctor 
    and publish on ReadTheDocs** by using build customizations features.

This example only includes a configuration file (``.readthedocs.yaml``), 
but the repository must also have been 
integrated to ReadTheDocs (by linking your Github account and importing your project for 
instance or by `manual webhook configuration <https://stackoverflow.com/a/74959815>`_).

The config file below assume you're cloning your repository with http(s) protocol 
and that repository is a GitHub instance 
(the value of ``--html-viewsource-base`` could vary depending on your git server). 

Though, a similar process can be applied to Gitea, GitLab, Bitbucket ot others git servers.

Just substitute `(projectname)` and `(packagedirectory)`
with the appropriate information.

.. code:: yaml

    version: 2
    build:
    os: "ubuntu-22.04"
    tools:
        python: "3.10"
    commands:
        - pip install pydoctor
        - | 
        pydoctor \
        --project-name=(projectname) \
        --project-version=${READTHEDOCS_GIT_IDENTIFIER} \
        --project-url=${READTHEDOCS_GIT_CLONE_URL%*.git} \
        --html-viewsource-base=${READTHEDOCS_GIT_CLONE_URL%*.git}/tree/${READTHEDOCS_GIT_COMMIT_HASH} \
        --html-base-url=${READTHEDOCS_CANONICAL_URL} \
        --html-output $READTHEDOCS_OUTPUT/html/ \
        --docformat=restructuredtext \
        --intersphinx=https://docs.python.org/3/objects.inv \
        ./(packagedirectory)

`More on ReadTheDocs build customizations <https://docs.readthedocs.io/en/stable/build-customization.html>`_.
