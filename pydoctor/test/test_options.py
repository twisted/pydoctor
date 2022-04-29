import os
from pathlib import Path
import pytest
from io import StringIO

from pydoctor import imodel
from pydoctor.options import PydoctorConfigParser, Options

from pydoctor.test import FixtureRequest, TempPathFactory

EXAMPLE_TOML_CONF = """
[tool.poetry]
packages = [
    { include = "my_package" },
    { include = "extra_package" },
]
name = "awesome"

[tool.poetry.dependencies]
# These packages are mandatory and form the core of this package’s distribution.
mandatory = "^1.0"

# A list of all of the optional dependencies, some of which are included in the
# below `extras`. They can be opted into by apps.
psycopg2 = { version = "^2.7", optional = true }
mysqlclient = { version = "^1.3", optional = true }

[tool.poetry.extras]
mysql = ["mysqlclient"]
pgsql = ["psycopg2"]
"""

EXAMPLE_INI_CONF = """
[metadata]
name = setup.cfg
version = 0.9.0.dev
author = Erik M. Bray
author-email = embray@stsci.edu
summary = Reads a distributions's metadata from its setup.cfg file and passes it to setuptools.setup()
description-file =
    README.rst
    CHANGES.rst
home-page = http://pypi.python.org/pypi/setup.cfg
requires-dist = setuptools
classifier =
    Development Status :: 5 - Production/Stable
    Environment :: Plugins
    Framework :: Setuptools Plugin
    Intended Audience :: Developers
    License :: OSI Approved :: BSD License
    Operating System :: OS Independent
    Programming Language :: Python
    Programming Language :: Python :: 3
    Topic :: Software Development :: Build Tools
    Topic :: Software Development :: Libraries :: Python Modules
    Topic :: System :: Archiving :: Packaging

[files]
packages =
    setup
    setup.cfg
    setup.cfg.extern
extra_files =
    CHANGES.rst
    LICENSE
    ez_setup.py
"""

PYDOCTOR_SECTIONS = ["""
[pydoctor]
intersphinx = ["https://docs.python.org/3/objects.inv",
                "https://twistedmatrix.com/documents/current/api/objects.inv",
                "https://urllib3.readthedocs.io/en/latest/objects.inv",
                "https://requests.readthedocs.io/en/latest/objects.inv",
                "https://www.attrs.org/en/stable/objects.inv",
                "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
docformat = 'restructuredtext'
project-name = 'MyProject'
project-url = "https://github.com/twisted/pydoctor"
privacy = ["HIDDEN:pydoctor.test"]
quiet = 1
warnings-as-errors = true
""", # toml/ini

"""
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
privacy = ["HIDDEN:pydoctor.test"]
quiet = 1
warnings-as-errors = true
""", # toml/ini

"""
[tool:pydoctor]
intersphinx = 
    https://docs.python.org/3/objects.inv
    https://twistedmatrix.com/documents/current/api/objects.inv
    https://urllib3.readthedocs.io/en/latest/objects.inv
    https://requests.readthedocs.io/en/latest/objects.inv
    https://www.attrs.org/en/stable/objects.inv
    https://tristanlatr.github.io/apidocs/docutils/objects.inv
docformat = restructuredtext
project-name = MyProject
project-url = https://github.com/twisted/pydoctor
privacy = 
    HIDDEN:pydoctor.test
quiet = 1
warnings-as-errors = true
""", # ini only

"""
[pydoctor]
intersphinx: ["https://docs.python.org/3/objects.inv",
                "https://twistedmatrix.com/documents/current/api/objects.inv",
                "https://urllib3.readthedocs.io/en/latest/objects.inv",
                "https://requests.readthedocs.io/en/latest/objects.inv",
                "https://www.attrs.org/en/stable/objects.inv",
                "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
docformat: restructuredtext
project-name: MyProject
project-url: '''https://github.com/twisted/pydoctor'''
privacy = 
    HIDDEN:pydoctor.test
quiet = 1
warnings-as-errors = true
""", # ini only
]

@pytest.fixture(scope='module')
def tempDir(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Path:
    name = request.module.__name__.split('.')[-1]
    return tmp_path_factory.mktemp(f'{name}-cache')

@pytest.mark.parametrize('project_conf', [EXAMPLE_TOML_CONF, EXAMPLE_INI_CONF])
@pytest.mark.parametrize('pydoctor_conf', PYDOCTOR_SECTIONS)
def test_config_parsers(project_conf:str, pydoctor_conf:str, tempDir:Path) -> None:

    if '[tool:pydoctor]' in pydoctor_conf and '[tool.poetry]' in project_conf:
        # colons in section names are not supported in TOML (without quotes)
        return
    if 'intersphinx:' in pydoctor_conf and '[tool.poetry]' in project_conf:
        # colons to defined key pairs are not supported in TOML
        return

    parser = PydoctorConfigParser()
    stream = StringIO(project_conf + '\n' + pydoctor_conf)
    data = parser.parse(stream)

    assert data['docformat'] == 'restructuredtext', data
    assert data['project-url'] == 'https://github.com/twisted/pydoctor', data
    assert len(data['intersphinx']) == 6, data
    
    conf_file = (tempDir / "pydoctor_temp_conf")
    
    with conf_file.open('w') as f:
        f.write(project_conf + '\n' + pydoctor_conf)

    options = Options.from_args([f"--config={conf_file}"])
    assert options.verbosity == -1
    assert options.warnings_as_errors == True
    assert options.privacy == [(imodel.PrivacyClass.HIDDEN, 'pydoctor.test')]
    assert options.intersphinx[0] == "https://docs.python.org/3/objects.inv"
    assert options.intersphinx[-1] == "https://tristanlatr.github.io/apidocs/docutils/objects.inv"

def test_repeatable_options_multiple_configs_and_args(tempDir:Path) -> None:
    config1 = """
[pydoctor]
intersphinx = ["https://docs.python.org/3/objects.inv"]
verbose = 1
"""
    config2 = """
[tool.pydoctor]
intersphinx = ["https://twistedmatrix.com/documents/current/api/objects.inv"]
verbose = -1
project-version = 2050.4C
"""
    config3 = """
[tool:pydoctor]
intersphinx = ["https://requests.readthedocs.io/en/latest/objects.inv"]
verbose = 0
project-name = "Hello World!"
"""

    cwd = os.getcwd()
    try:
        conf_file1 = (tempDir / "pydoctor.ini")
        conf_file2 = (tempDir / "pyproject.toml")
        conf_file3 = (tempDir / "setup.cfg")

        for cfg, file in zip([config1, config2, config3],[conf_file1, conf_file2, conf_file3]):
            with open(file, 'w') as f:
                f.write(cfg)
        
        os.chdir(tempDir)
        options = Options.defaults()

        assert options.verbosity == 1
        assert options.intersphinx == ["https://docs.python.org/3/objects.inv",]
        assert options.projectname == "Hello World!"
        assert options.projectversion == "2050.4C"

        options = Options.from_args(['-vv'])

        assert options.verbosity == 3 # I would have expected 2
        assert options.intersphinx == ["https://docs.python.org/3/objects.inv",]
        assert options.projectname == "Hello World!"
        assert options.projectversion == "2050.4C"

        options = Options.from_args(['-vv', '--intersphinx=https://twistedmatrix.com/documents/current/api/objects.inv', '--intersphinx=https://urllib3.readthedocs.io/en/latest/objects.inv'])

        assert options.verbosity == 3 # I would have expected 2
        assert options.intersphinx == ["https://twistedmatrix.com/documents/current/api/objects.inv", "https://urllib3.readthedocs.io/en/latest/objects.inv"]
        assert options.projectname == "Hello World!"
        assert options.projectversion == "2050.4C"

    finally:
        os.chdir(cwd)
