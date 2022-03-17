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

.. note:: 
    The INI parser includes support for quoting strings literal as well as python list syntax evaluation for repeatable options. 
    It will use ``configparser`` module to parse an INI file which allows multi-line values.
    Allowed syntax is that for a ``ConfigParser`` with the default options. See `the configparser docs <https://docs.python.org/3/library/configparser.html>`_ for details.          

``pydoctor.ini``
^^^^^^^^^^^^^^^^

If more than one config file exists, ``./pydoctor.ini`` overrides values from other config files. 
Declaring section ``[pydoctor]`` is required.

:: 

    [pydoctor]
    privacy = ["HIDDEN:pydoctor.test"]
    quiet = 1

``pyproject.toml``
^^^^^^^^^^^^^^^^^^

``pyproject.toml`` are considered for configuration when they contain a ``[tool.pydoctor]`` table.  It must use TOML format.

:: 

    [tool.pydoctor]
    pyvalreprmaxlines = 0
    docformat = "restructuredtext"
    project-name = "MyProject"
    project-url = "https://github.com/twisted/pydoctor"

``setup.cfg``
^^^^^^^^^^^^^

``setup.cfg`` can also be used to hold pydoctor configuration if they have a ``[tool:pydoctor]`` section. It must use INI format.

:: 

    [tool:pydoctor]
    intersphinx = ["https://docs.python.org/3/objects.inv",
                    "https://twistedmatrix.com/documents/current/api/objects.inv",
                    "https://urllib3.readthedocs.io/en/latest/objects.inv",
                    "https://requests.readthedocs.io/en/latest/objects.inv",
                    "https://www.attrs.org/en/stable/objects.inv",
                    "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
    verbose = 1
    warnings_as_errors = true

.. Note:: If an argument is specified in more than one place, 
    then commandline values override config file values which override defaults.