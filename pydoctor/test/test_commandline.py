from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys

from pytest import raises

from pydoctor import driver

from . import CapSys


def geterrtext(*options: str) -> str:
    """
    Run CLI with options and return the output triggered by system exit.
    """
    se = sys.stderr
    f = StringIO()
    print(options)
    sys.stderr = f
    try:
        try:
            driver.main(list(options))
        except SystemExit:
            pass
        else:
            assert False, "did not fail"
    finally:
        sys.stderr = se
    return f.getvalue()

def test_invalid_option() -> None:
    err = geterrtext('--no-such-option')
    assert 'no such option' in err

def test_cannot_advance_blank_system() -> None:
    err = geterrtext('--make-html')
    assert 'No source paths given' in err

def test_no_systemclasses_py3() -> None:
    err = geterrtext('--system-class')
    assert 'requires 1 argument' in err

def test_invalid_systemclasses() -> None:
    err = geterrtext('--system-class=notdotted')
    assert 'dotted name' in err
    err = geterrtext('--system-class=no-such-module.System')
    assert 'could not import module' in err
    err = geterrtext('--system-class=pydoctor.model.Class')
    assert 'is not a subclass' in err


def test_projectbasedir_absolute(tmp_path: Path) -> None:
    """
    The --project-base-dir option, when given an absolute path, should set that
    path as the projectbasedirectory attribute on the options object.

    Previous versions of this test tried using non-existing paths and compared
    the string representations, but that was unreliable, since the input path
    might contain a symlink that will be resolved, such as "/home" on macOS.
    Using L{Path.samefile()} is reliable, but requires an existing path.
    """
    assert tmp_path.is_absolute()
    options, args = driver.parse_args(["--project-base-dir", str(tmp_path)])
    assert options.projectbasedirectory.samefile(tmp_path)
    assert options.projectbasedirectory.is_absolute()


def test_projectbasedir_symlink(tmp_path: Path) -> None:
    """
    The --project-base-dir option, when given a path containing a symbolic link,
    should resolve the path to the target directory.
    """
    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    link.symlink_to('target', target_is_directory=True)
    assert link.samefile(target)

    options, args = driver.parse_args(["--project-base-dir", str(link)])
    assert options.projectbasedirectory.samefile(target)
    assert options.projectbasedirectory.is_absolute()


def test_projectbasedir_relative() -> None:
    """
    The --project-base-dir option, when given a relative path, should convert
    that path to absolute and set it as the projectbasedirectory attribute on
    the options object.
    """
    relative = "projbasedirvalue"
    options, args = driver.parse_args(["--project-base-dir", relative])
    assert options.projectbasedirectory.is_absolute()
    assert options.projectbasedirectory.name == relative
    assert options.projectbasedirectory.parent == Path.cwd()


def test_cache_enabled_by_default() -> None:
    """
    Intersphinx object caching is enabled by default.
    """
    parser = driver.getparser()
    (options, _) = parser.parse_args([])
    assert options.enable_intersphinx_cache


def test_cli_warnings_on_error() -> None:
    """
    The --warnings-as-errors option is disabled by default.
    This is the test for the long form of the CLI option.
    """
    options, args = driver.parse_args([])
    assert options.warnings_as_errors == False

    options, args = driver.parse_args(['--warnings-as-errors'])
    assert options.warnings_as_errors == True


def test_project_version_default() -> None:
    """
    When no --project-version is provided, it will default empty string.
    """
    options, args = driver.parse_args([])
    assert options.projectversion == ''


def test_project_version_string() -> None:
    """
    --project-version can be passed as a simple string.
    """
    options, args = driver.parse_args(['--project-version', '1.2.3.rc1'])
    assert options.projectversion == '1.2.3.rc1'


def test_main_project_name_guess(capsys: CapSys) -> None:
    """
    When no project name is provided in the CLI arguments, a default name
    is used and logged.
    """
    exit_code = driver.main(args=[
        '-v', '--testing',
        'pydoctor/test/testpackages/basic/'
        ])

    assert exit_code == 0
    assert "Guessing 'basic' for project name." in capsys.readouterr().out


def test_main_project_name_option(capsys: CapSys) -> None:
    """
    When a project name is provided in the CLI arguments nothing is logged.
    """
    exit_code = driver.main(args=[
        '-v', '--testing',
        '--project-name=some-name',
        'pydoctor/test/testpackages/basic/'
        ])

    assert exit_code == 0
    assert 'Guessing ' not in capsys.readouterr().out


def test_main_return_zero_on_warnings() -> None:
    """
    By default it will return 0 as exit code even when there are warnings.
    """
    stream = StringIO()
    with redirect_stdout(stream):
        exit_code = driver.main(args=[
            '--html-writer=pydoctor.test.InMemoryWriter',
            'pydoctor/test/testpackages/report_trigger/'
            ])

    assert exit_code == 0
    assert "__init__.py:8: Unknown field 'bad_field'" in stream.getvalue()
    assert 'report_module.py:9: Cannot find link target for "BadLink"' in stream.getvalue()


def test_main_return_non_zero_on_warnings() -> None:
    """
    When `-W` is used it returns 3 as exit code when there are warnings.
    """
    stream = StringIO()
    with redirect_stdout(stream):
        exit_code = driver.main(args=[
            '-W',
            '--html-writer=pydoctor.test.InMemoryWriter',
            'pydoctor/test/testpackages/report_trigger/'
            ])

    assert exit_code == 3
    assert "__init__.py:8: Unknown field 'bad_field'" in stream.getvalue()
    assert 'report_module.py:9: Cannot find link target for "BadLink"' in stream.getvalue()


def test_main_symlinked_paths(tmp_path: Path) -> None:
    """
    The project base directory and package/module directories are normalized
    in the same way, such that System.setSourceHref() can call Path.relative_to()
    on them.
    """
    link = tmp_path / 'src'
    link.symlink_to(Path.cwd(), target_is_directory=True)

    exit_code = driver.main(args=[
        '--project-base-dir=.',
        '--html-viewsource-base=http://example.com',
        f'{link}/pydoctor/test/testpackages/basic/'
        ])
    assert exit_code == 0


def test_main_source_outside_basedir(capsys: CapSys) -> None:
    """
    If a --project-base-dir is given, all package and module paths must
    be located inside that base directory.
    """
    with raises(SystemExit):
        driver.main(args=[
            '--project-base-dir=docs',
            'pydoctor/test/testpackages/basic/'
            ])
    assert "Source path lies outside base directory:" in capsys.readouterr().err


def test_make_intersphix(tmp_path: Path) -> None:
    """
    --make-intersphinx without --make-html will only produce the Sphinx inventory object.

    This is also an integration test for the Sphinx inventory writer.
    """
    inventory = tmp_path / 'objects.inv'
    exit_code = driver.main(args=[
        '--project-base-dir=.',
        '--make-intersphinx',
        '--project-name=acme-lib',
        '--project-version=20.12.0-dev123',
        '--html-output', str(tmp_path),
        'pydoctor/test/testpackages/basic/'
        ])

    assert exit_code == 0
    # No other files are created, other than the inventory.
    assert [p.name for p in tmp_path.iterdir()] == ['objects.inv']
    assert inventory.is_file()
    assert b'Project: acme-lib\n# Version: 20.12.0-dev123\n' in inventory.read_bytes()
