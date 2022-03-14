
Customize Output
================

Tweak HTML templates
--------------------

They are 3 placeholders designed to be overwritten to include custom HTML and CSS into the pages.

- ``header.html``: at the very beginning of the body
- ``subheader.html``: after the main header, before the page title
- ``extra.css``: extra CSS sheet for layout customization

To override a placeholder, write your custom HTML or CSS files to a directory
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

    This example is using new ``pydoctor`` option, ``--theme=base``. 
    This means that bootstrap CSS will not be copied to build directory.

.. _customize-privacy:

Override objects privacy (show/hide)
------------------------------------

Pydoctor supports 3 types of privacy.
Below is the description of each type and the default association:

- ``PRIVATE``: By default for objects whose name starts with an underscore and are not a dunder method. 
  Rendered in HTML, but hidden via CSS by default.

- ``PUBLIC``: By default everything else that is not private.
  Always rendered and visible in HTML.

- ``HIDDEN``: Nothing is hidden by default.
  Not rendered at all and no links can be created to hidden objects. 
  Not present in the search index nor the intersphinx inventory.
  Basically excluded from API documentation. If a module/package/class is hidden, then all it's members are hidden as well.

When the default rules regarding privacy doesn't fit your use case,
use the `--privacy` command line option.
It can be used multiple times to define multiple privacy rules::

  --privacy=<PRIVACY>:<PATTERN>

where ``<PRIVACY>`` can be one of ``PUBLIC``, ``PRIVATE`` or ``HIDDEN`` (case insensitive), and ``<PATTERN>`` is fnmatch-like 
pattern matching objects fullName.

Privacy tweak examples
^^^^^^^^^^^^^^^^^^^^^^
- ``--privacy="PUBLIC:**"``
  Makes everything public.

- ``--privacy="HIDDEN:twisted.test.*" --privacy="PUBLIC:twisted.test.proto_helpers"``
  Makes everything under ``twisted.test`` hidden except ``twisted.test.proto_helpers``, which will be public.
  
- ``--privacy="PRIVATE:**.__*__" --privacy="PUBLIC:**.__init__"``
  Makes all dunder methods private except ``__init__``.

.. important:: The order of arguments matters. Pattern added last have priority over a pattern added before,
  but an exact match wins over a fnmatch.

.. note:: See :py:mod:`pydoctor.qnmatch` for more informations regarding the pattern syntax.

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
