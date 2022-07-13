Theming and other customizations
================================

Configure sidebar expanding/collapsing
--------------------------------------

By default, the sidebar only lists one level of objects (always expanded), 
to allow objects to expand/collapse and show first nested content, use the following option::

  --sidebar-expand-depth=2

This value describe how many nested modules and classes should be expandable.

.. note:: 
  Careful, a value higher than ``1`` (which is the default) can make your HTML files 
  significantly larger if you have many modules or classes.

  To disable completely the sidebar, use option ``--no-sidebar``

Theming
-------

Currently, there are 2 main themes packaged with pydoctor: ``classic`` and ``readthedocs``.

Choose your theme with option:: 

  --theme

.. note::
  Additionnaly, the ``base`` theme can be used as a base for customizations.

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
use the ``--privacy`` command line option.
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

.. note:: Quotation marks should be added around each rule to avoid shell expansions.
    Unless the arguments are passed directly to pydoctor, like in Sphinx's ``conf.py``, in this case you must not quote the privacy rules.

.. _use-custom-system-class:

Use a custom system class
-------------------------

You can subclass the :py:class:`pydoctor.model.System`
and pass your custom class dotted name with the following argument::

  --system-class=mylib._pydoctor.CustomSystem

System class allows you to customize certain aspect of the system and configure the enabled extensions. 
If what you want to achieve has something to do with the state of some objects in the Documentable tree, 
it's very likely that you can do it without the need to override any system method, 
by using the extension mechanism described below. Configuring extenions and other forms of system customizations
does, nonetheless requires you to subclass the :py:class:`pydoctor.model.System` and override the required class variables.

Brief on pydoctor extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The AST builder can now be customized with extension modules.
This is how we handle Zope Interfaces declarations and :py:mod:`twisted.python.deprecate` warnings.

Each pydocotor extension is a Python module with at least a ``setup_pydoctor_extension()`` function. 
This function is called at initialization of the system with one argument, 
the :py:class:`pydoctor.extensions.ExtRegistrar` object representing the system.

An extension can register multiple kind of components:
 - AST builder visitors
 - Mixin classes for :py:class:`pydoctor.model.Documentable`
 - Post processors

Take a look at built-in extensions :py:mod:`pydoctor.extensions.zopeinterface` and  :py:mod:`pydoctor.extensions.deprecate`. 
Navigate to the source code for a better overview.

A concrete example
^^^^^^^^^^^^^^^^^^

Let's say you want to write a extension for simple pydantic classes like this one:

.. code:: python

    from typing import ClassVar
    from pydantic import BaseModel
    class Model(BaseModel):
        a: int
        b: int = Field(...)
        name:str = 'Jane Doe'
        kind:ClassVar = 'person'
        

First, we need to create a new module that will hold our extension code: ``mylib._pydoctor``. 
This module will contain visitor code that visits ``ast.AnnAssign`` nodes after the main visitor. 
It will check if the current context object is a class derived from ``pydantic.BaseModel`` and 
transform each class variable into instance variables accordingly.

.. code:: python

    # Module mylib._pydoctor

    import ast
    from pydoctor import astutils, extensions, model

    class PydanticModVisitor(extensions.ModuleVisitorExt):

        def depart_AnnAssign(self, node: ast.AnnAssign) -> None:
            """
            Called after an annotated assignment definition is visited.
            """
            ctx = self.visitor.builder.current
            if not isinstance(ctx, model.Class):
                # check if the current context object is a class
                return

            if not any(ctx.expandName(b) == 'pydantic.BaseModel' for b in ctx.bases):
                # check if the current context object if a class derived from ``pydantic.BaseModel``
                return

            dottedname = astutils.node2dottedname(node.target)
            if not dottedname or len(dottedname)!=1:
                # check if the assignment is a simple name, otherwise ignore it
                return
            
            # Get the attribute from current context
            attr = ctx.contents[dottedname[0]]

            assert isinstance(attr, model.Attribute)

            # All class variables that are not annotated with ClassVar will be transformed to instance variables.
            if astutils.is_using_typing_classvar(attr.annotation, attr):
                return

            if attr.kind == model.DocumentableKind.CLASS_VARIABLE:
                attr.kind = model.DocumentableKind.INSTANCE_VARIABLE

    def setup_pydoctor_extension(r:extensions.ExtRegistrar) -> None:
        r.register_astbuilder_visitor(PydanticModVisitor)

    class PydanticSystem(model.System):
        # Declare that this system should load this additional extension
        custom_extensions = ['mylib._pydoctor']

Then, we would pass our custom class dotted name with the argument ``--system-class``::

  --system-class=mylib._pydoctor.PydanticSystem

Et voilà.

If this extension mechanism doesn't support the tweak you want, you can consider overriding some
:py:class:`pydoctor.model.System` methods. For instance, overriding :py:meth:`pydoctor.model.System.__init__` method could be useful, 
if some want to write a custom :py:class:`pydoctor.sphinx.SphinxInventory`.


.. important:: 
    If you feel like other users of the community might benefit from your extension as well, please 
    don't hesitate to open a pull request adding your extension module to the package :py:mod:`pydoctor.extensions`.

.. _tweak-ifs-branch-priority:

Tweak 'ifs' branch priority
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes pydoctor default :ref:`Branch priorities <branch-priorities>` can be inconvenient. 
Specifically, when dealing with ``TYPE_CHECKING``. 
A common purpose of ``if TYPE_CHECKING:`` blocks is to contain imports that are only 
necessary for the purpose of type annotations. These might be circular imports at runtime. 
When these types are used to annotate arguments or return values, 
they are relevant to pydoctor as well: either to extract type information 
from annotations or to look up the fully qualified version of some ``L{name}``.

In other cases, ``if TYPE_CHECKING:`` blocks are used to perform trickery 
to make ``mypy`` accept code that is difficult to analyze. 
In these cases, pydoctor can have better results by analysing the runtime version of the code instead. 
For details, read `the comments in this Klein PR <https://github.com/twisted/klein/pull/315>`_.

Pydoctor has the ability to evaluate some simple name based :py:class:`ast.If` 
condition in order to visit either the statements in main ``If.body`` or the ``If.orelse`` only.

You can instrut pydoctor do to such things with a custom system class, 
by overriding the class variable :py:attr:`pydoctor.model.System.eval_if`.
This variable should be a dict of strings to dict of strings to any value. 
This mechanism currently supports simple name based 'Ifs' only.
    
Meaning like::

    if TYPE_CHECKING:
        ...
    if typing.TYPE_CHECKING:
        ...

Does not recognize 'If' expressions like::

    if TYPE_CHECKING==True:
        ...
    if TYPE_CHECKING is not False:
        ...

The code below demonstrate an example usage. 

The assignment to :py:attr:`pydoctor.model.System.eval_if` declares two custom 'If' evaluation rules. 
The first rule applies only to the 'Ifs' in ``my_mod`` and second one applies to all objects directly in the package ``my_mod._complex``
Both rules makes the statements in ``if TYPE_CHECKING:`` blocks skipped to give the priority to what's defined in the ``else:`` blocks.

.. code:: python

    class MySystem(model.System):
        eval_if = {
            'my_mod':{'TYPE_CHECKING':False},
            'my_mod._complex.*':{'TYPE_CHECKING':False},
        }

.. note:: See :py:mod:`pydoctor.qnmatch` for more informations regarding the pattern syntax. 

Then use the ``--system-class`` option as described in :ref:`Use a custom system class <use-custom-system-class>` section.


Use a custom writer class
-------------------------

You can subclass the :py:class:`pydoctor.templatewriter.TemplateWriter` (or the abstract super class :py:class:`pydoctor.templatewriter.IWriter`)
and pass your custom class dotted name with the following argument::

  --html-writer=mylib._pydoctor.CustomTemplateWriter

The option is actually badly named because, theorically one could write a subclass 
of :py:class:`pydoctor.templatewriter.IWriter` (to be used alongside option ``--template-dir``) 
that would output Markdown, reStructuredText or JSON.

.. warning:: Pydoctor does not have a stable API yet. Code customization is prone
    to break in future versions.
