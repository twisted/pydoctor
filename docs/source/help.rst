CLI Options and Config File
===========================

Command line options
--------------------

.. argparse::
   :ref: pydoctor.options.get_parser
   :prog: pydoctor
   :nodefault:

Configuration file
------------------

Arguments that start with ``--`` (eg. ``--project-name``) can also be set in a config file. 
Currently, positional arguments cannot be configured with a file.  

By convention, the config file resides on the root of your repository. 

Pydoctor automatically integrates with common project files ``./pyproject.toml`` or ``./setup.cfg`` and loads file ``./pydoctor.ini`` if if exists.
The configuration parser supports `TOML <https://github.com/toml-lang/toml/blob/main/toml.md>`_ and INI formats. 

.. note:: No path processing is done to determine the project root directory, pydoctor only looks at the current working directory. 
    You can set a different config file path with option ``--config``, this is necessary to load project configuration files from Sphinx's ``conf.py``.

``pydoctor.ini``
^^^^^^^^^^^^^^^^

Declaring section ``[pydoctor]`` is required.

:: 

    [pydoctor]
    intersphinx = 
        https://docs.python.org/3/objects.inv
        https://twistedmatrix.com/documents/current/api/objects.inv
    docformat = restructuredtext
    verbose = 1
    warnings-as-errors = true
    privacy = 
        HIDDEN:pydoctor.test
        PUBLIC:pydoctor._configparser

``pyproject.toml``
^^^^^^^^^^^^^^^^^^

``pyproject.toml`` are considered for configuration when they contain a ``[tool.pydoctor]`` table.  It must use TOML format.

:: 

    [tool.pydoctor]
    intersphinx = ["https://docs.python.org/3/objects.inv", 
                   "https://twistedmatrix.com/documents/current/api/objects.inv"]
    docformat = "restructuredtext"
    verbose = 1
    warnings-as-errors = true
    privacy = ["HIDDEN:pydoctor.test",
               "PUBLIC:pydoctor._configparser",]

Note that the config file fragment above is also valid INI format and could be parsed from a ``setup.cfg`` file successfully.

``setup.cfg``
^^^^^^^^^^^^^

``setup.cfg`` can also be used to hold pydoctor configuration if they have a ``[tool:pydoctor]`` section. It must use INI format.

:: 

    [tool:pydoctor]
    intersphinx = 
        https://docs.python.org/3/objects.inv
        https://twistedmatrix.com/documents/current/api/objects.inv
    docformat = restructuredtext
    verbose = 1
    warnings-as-errors = true
    privacy = 
        HIDDEN:pydoctor.test
        PUBLIC:pydoctor._configparser

.. Note:: Repeatable arguments must be defined as list. 

.. Note:: If an argument is specified in more than one place, 
    then command line values override config file values which override defaults.
    If more than one config file exists, ``pydoctor.ini`` overrides values from 
    ``pyproject.toml`` which overrrides ``setup.cfg``. Repeatable options are not 
    merged together, there are overriden as well. 

.. Note:: 
    The INI parser behaves like :py:class:`configargparse:configargparse.ConfigparserConfigFileParser` in addition that it 
    converts plain multiline values to list, each non-empty line will be converted to a list item.
    If for some reason you need newlines in a string value, just tripple quote your string like you would do in python. 
    
    Allowed syntax is that for a :py:class:`std:configparser.ConfigParser` with the default options.

.. Note:: 
    Last note: pydoctor has always supported a ``--config`` option, but before 2022, the format was undocumentd and rather fragile.
    This new configuration format breaks compatibility with older config file in two main ways: 
        - Options names are now the same as argument without the leading ``--`` (e.g ``project-name`` and not ``projectname``).
        - Define repeatable options with multiline strings or list literals instead of commas separated string.