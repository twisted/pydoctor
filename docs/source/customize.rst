
Customize output
================

Include custom HTML
-------------------

They are 4 placeholders designed to be overwritten to include custom HTML and CSS into the pages.

- ``header.html``: At the very beginning of the body
- ``pageHeader.html``: After the main header, before the page title
- ``footer.html``: At the very end of the body
- ``extra.css``: Extra CSS sheet for layout customization

To override a placeholder, write your custom HTLM files to a folder 
and use the following option::

  --template-dir=./pydoctor_templates

.. note::

  If you want more customization, you can override the defaults 
  HTML and CSS templates in 
  `pydoctor/templates <https://github.com/twisted/pydoctor/tree/master/pydoctor/templates>`_ 
  with the same method. 

Use a custom system class
-------------------------

You can subclass the :py:class:`pydoctor:pydoctor.zopeinterface.ZopeInterfaceSystem` 
and pass your custom class dotted name with the following argument::

  --system-class=mylib._pydoctor.CustomSystem

System class allows you to dynamically show/hide classes or methods.
This is also used by the Twisted project to handle deprecation.

See the :py:class:`twisted:twisted.python._pydoctor.TwistedSystem` custom class documentation. 
Navigate to the source code for a better overview.

Use a custom writer class
-------------------------

You can subclass the :py:class:`pydoctor:pydoctor.templatewriter.writer.TemplateWriter` 
and pass your custom class dotted name with the following argument::


  --writer-class=mylib._pydoctor.CustomTemplateWriter

.. warning:: Pydoctor does not have a stable API yet. Code customization is prone 
    to break in future versions. 

