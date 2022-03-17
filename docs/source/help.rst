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
You can set a different config file path with option ``--config``. 

The configuration parser supports TOML and INI formats.

.. note:: INI parser note
    The INI parser includes support for quoting strings literal as well as python list syntax evaluation for repeatable options. 
    It will use ``configparser`` module to parse an INI file which allows multi-line values.
    Allowed syntax is that for a ``ConfigParser`` with the default options.See `the configparser docs`__ for details.          

``setup.cfg``
^^^^^^^^^^^^^

:: 

    [tool:pydoctor]
    intersphinx = ["https://docs.python.org/3/objects.inv",
                    "https://twistedmatrix.com/documents/current/api/objects.inv",
                    "https://urllib3.readthedocs.io/en/latest/objects.inv",
                    "https://requests.readthedocs.io/en/latest/objects.inv",
                    "https://www.attrs.org/en/stable/objects.inv",
                    "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
    docformat = restructuredtext
    project-name = MyProject
    project-url = https://github.com/twisted/pydoctor

``pyproject.toml``
^^^^^^^^^^^^^^^^^^

:: 

    [tool.pydoctor]
    intersphinx = ["https://docs.python.org/3/objects.inv",
                    "https://twistedmatrix.com/documents/current/api/objects.inv",
                    "https://urllib3.readthedocs.io/en/latest/objects.inv",
                    "https://requests.readthedocs.io/en/latest/objects.inv",
                    "https://www.attrs.org/en/stable/objects.inv",
                    "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
    docformat = "restructuredtext"
    project-name = "MyProject"
    project-url = "https://github.com/twisted/pydoctor"

``pydoctor.ini``
^^^^^^^^^^^^^^^^

:: 

    [pydoctor]
    intersphinx = ["https://docs.python.org/3/objects.inv",
                    "https://twistedmatrix.com/documents/current/api/objects.inv",
                    "https://urllib3.readthedocs.io/en/latest/objects.inv",
                    "https://requests.readthedocs.io/en/latest/objects.inv",
                    "https://www.attrs.org/en/stable/objects.inv",
                    "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
    docformat = restructuredtext
    project-name = MyProject
    project-url = https://github.com/twisted/pydoctor

.. Note:: If an argument is specified in more than one place, 
    then commandline values override config file values which override defaults.

.. Note:: If more than one config file exists, ``./pydoctor.ini`` overrides values from other config files.

__ https://github.com/bw2/ConfigArgParse
__ https://docs.python.org/3/library/configparser.html