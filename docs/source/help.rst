CLI Options and Config File
===========================

Command line options
--------------------

.. argparse::
   :ref: pydoctor.driver.get_parser
   :prog: pydoctor
   :nodefault:

Configuration file
------------------

To loading the configuration file, pydoctor uses the `ConfigArgParse`__ module.

Arguments that start with ``--`` (eg. ``--project-name``) can also be set in a config file. 
Positional arguments cannot be configured with a file. 
You should not set arguments like ``--help`` or ``--version`` from the configuration file, 
unexpected behaviour can happend.

By default, it looks for the file ``./pydoctor.ini``, you can set a different config file with option ``--config``. 
It will use configparser module to parse an INI file which allows multi-line values.          

Allowed syntax is that for a ConfigParser with the following options::

    delimiters=("=",":"),
    allow_no_value=False,
    comment_prefixes=("#",";"),
    inline_comment_prefixes=("#",";"),
    strict=True,
    empty_lines_in_values=False,    

See `the configparser docs`__ for details.          

.. Note:: INI file sections names are treated as comments. If an argument is specified in more than one place, 
    then commandline values override config file values which override defaults.

Example of a ``pydoctor.ini`` file, use lists syntax for repeatable options:

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

__ https://github.com/bw2/ConfigArgParse
__ https://docs.python.org/3/library/configparser.html