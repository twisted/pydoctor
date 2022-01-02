Theming and other customizations
================================

Theming
-------

There are 3 builtin themes: ``classic`` and ``readthedocs`` are the main themes. 

The ``base`` theme is included in both main themes and can be used as a base for other themes.
Bootstrap CSS will not be copied to build directory when using the read the docs theme or the base theme.


Choose your theme with option:: 

  --theme

Tweak HTML templates
--------------------

They are 3 special files designed to be included in specific places of each pages. 

- ``header.html``: at the very beginning of the body
- ``subheader.html``: after the main header, before the page title
- ``extra.css``: extra CSS sheet for layout customization

To include a file, write your custom HTML or CSS files to a directory
and use the following option::

  --template-dir=./pydoctor_templates

If you want more customization, you can override the default templates in
`pydoctor/themes/base <https://github.com/twisted/pydoctor/tree/master/pydoctor/themes/base>`_
with the same method.

HTML templates have their own versioning system and warnings will be triggered when an outdated custom template is used.

.. admonition:: Demo theme example
    
  There is a demo template inspired by Twisted web page for which the source code is `here <https://github.com/twisted/pydoctor/tree/master/docs/sample_template>`_.
  You can try the result by checking `this page <custom_template_demo/pydoctor.html>`_.

  .. note:: 

    This example is using the ``base`` theme. 

Use a custom system class
-------------------------

You can subclass the :py:class:`pydoctor.zopeinterface.ZopeInterfaceSystem`
and pass your custom class dotted name with the following argument::

  --system-class=mylib._pydoctor.CustomSystem

System class allows you to dynamically show/hide classes or methods.
This is also used by the Twisted project to handle deprecation.

See the :py:class:`twisted:twisted.python._pydoctor.TwistedSystem` custom class documentation.
Navigate to the source code for a better overview.

Use a custom writer class
-------------------------

You can subclass the :py:class:`pydoctor.templatewriter.TemplateWriter`
and pass your custom class dotted name with the following argument::


  --html-class=mylib._pydoctor.CustomTemplateWriter

.. warning:: Pydoctor does not have a stable API yet. Code customization is prone
    to break in future versions.
