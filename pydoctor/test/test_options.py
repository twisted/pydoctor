from pathlib import Path
import pytest
import requests
from io import StringIO


from pydoctor import model
from pydoctor.options import PydoctorConfigParser, Options
from pydoctor._configparser import parse_toml_section_name, _is_quoted, unquote_str
from pydoctor.test.epydoc.test_pyval_repr import color2
from pydoctor.test import FixtureRequest, TempPathFactory

def test_unquote_str() -> None:

    assert unquote_str('string') == 'string'
    assert unquote_str('"string') == '"string'
    assert unquote_str('string"') == 'string"'
    assert unquote_str('"string"') == 'string'
    assert unquote_str('\'string\'') == 'string'
    assert unquote_str('"""string"""') == 'string'
    assert unquote_str('\'\'\'string\'\'\'') == 'string'
    assert unquote_str('"""\nstring"""') == '\nstring'
    assert unquote_str('\'\'\'string\n\'\'\'') == 'string\n'
    assert unquote_str('"""\nstring  \n"""') == '\nstring  \n'
    assert unquote_str('\'\'\'\n  string\n\'\'\'') == '\n  string\n'
    
    assert unquote_str('\'\'\'string') == '\'\'\'string'
    assert unquote_str('string\'\'\'') == 'string\'\'\''
    assert unquote_str('"""string') == '"""string'
    assert unquote_str('string"""') == 'string"""'
    assert unquote_str('"""str"""ing"""') == '"""str"""ing"""'
    assert unquote_str('str\'ing') == 'str\'ing'

def test_unquote_naughty_quoted_strings() -> None:
    # See https://github.com/minimaxir/big-list-of-naughty-strings/blob/master/blns.txt
    res = requests.get('https://raw.githubusercontent.com/minimaxir/big-list-of-naughty-strings/master/blns.txt')

    for i, string in enumerate(res.text.split('\n')):
        if string.strip().startswith('#'):
            continue

        # gerenerate two quoted version of the naughty string
        # simply once
        naughty_string_quoted = repr(string) 
        # quoted twice, once with repr, once with our colorizer 
        # (we insert \n such that we force the colorier to produce tripple quoted strings)
        naughty_string_quoted2 = color2(f"\n{string!r}", linelen=0) 
        assert naughty_string_quoted2.startswith("'''")
        
        # test unquote that repr
        try:
            assert unquote_str(naughty_string_quoted) == string

            assert unquote_str(unquote_str(naughty_string_quoted2).strip()) == string

            if _is_quoted(string):
                assert unquote_str(string) == string[1:-1]
            else:
                assert unquote_str(string) == string

        except Exception as e:
            raise AssertionError(f'error with naughty string at line {i}: {e}') from e

def test_parse_toml_section_keys() -> None:
    assert parse_toml_section_name('tool.pydoctor') == ('tool', 'pydoctor')
    assert parse_toml_section_name(' tool.pydoctor ') == ('tool', 'pydoctor')
    assert parse_toml_section_name(' "tool".pydoctor ') == ('tool', 'pydoctor')
    assert parse_toml_section_name(' tool."pydoctor" ') == ('tool', 'pydoctor')

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
intersphinx = ["https://docs.python.org/3/objects.inv",
                "https://twistedmatrix.com/documents/current/api/objects.inv",
                "https://urllib3.readthedocs.io/en/latest/objects.inv",
                "https://requests.readthedocs.io/en/latest/objects.inv",
                "https://www.attrs.org/en/stable/objects.inv",
                "https://tristanlatr.github.io/apidocs/docutils/objects.inv"]
docformat = restructuredtext
project-name = MyProject
project-url = https://github.com/twisted/pydoctor
privacy = ["HIDDEN:pydoctor.test"]
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
privacy = ["HIDDEN:pydoctor.test"]
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
    assert options.privacy == [(model.PrivacyClass.HIDDEN, 'pydoctor.test')]