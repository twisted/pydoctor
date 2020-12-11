"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.

This was designed to generate pydoctor HTML files as part of the
Read The Docs build process.

Inside the Sphinx conf.py file you need to define the following configuration options:

  - C{pydoctor_intersphinx_mapping} is mapping similar to C{intersphinx_mapping} version 1.0.
    Version 1.3 format is not yet supported.
    As opposed to C{intersphinx_mapping}, the relative path is based on the output directory
    and not the source directory.
    In the target url you can use C{{rtd_version}} to have the URL automatically updated
    based on Read The Docs build.

  - C{pydoctor_args} - an iterable with all the pydoctor command line arguments used to trigger the build.
                     - (private usage) a mapping with values as iterables of pydoctor command line arguments.

The following format placeholders are resolved for C{pydoctor_args} at runtime:
  - C{{outdir}} - the Sphinx output dir

You must call pydoctor with C{--quiet} argument
as otherwise any extra output is converted into Sphinx warnings.
"""
import os
import pathlib
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Iterable, Mapping

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError
from sphinx.util import logging

from pydoctor import __version__
from pydoctor.driver import main


logger = logging.getLogger(__name__)


def on_build_finished(app: Sphinx, exception: Exception) -> None:
    """
    Called when Sphinx build is done.
    """
    config: Config = app.config  # type: ignore[has-type]
    if not config.pydoctor_args:
        raise ConfigError("Missing 'pydoctor_args'.")

    placeholders = {
        'outdir': app.outdir,
        }

    runs = config.pydoctor_args

    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    for key, value in runs.items():
        _run_pydoctor(key, ['--make-html'] + value, placeholders)


def _run_pydoctor(name: str, arguments: Iterable[str], placeholders: Mapping[str, str]) -> None:
    """
    Call pydoctor with arguments.

    @param name: A human-readable description of this pydoctor build.
    @param arguments: Iterable of arguments used to call pydoctor.
    @param placeholders: Values that will be interpolated with the arguments using L{str.format()}.
    """
    args = []
    for argument in arguments:
        args.append(argument.format(**placeholders))

    build_type = next(iter(arguments))
    logger.info(f"Building {build_type} '{name}' pydoctor API docs as:")
    logger.info('\n'.join(args))

    with StringIO() as stream:
        with redirect_stdout(stream):
            main(args=args)

        for line in stream.getvalue().splitlines():
            logger.warning(line)


def update_intersphinx_mapping(app: Sphinx, config: Config) -> None:
    """
    Called to build and inject our own intersphinx inventory object.
    """
    rtd_version = 'latest'
    if os.environ.get('READTHEDOCS', '') == 'True':
        rtd_version = os.environ.get('READTHEDOCS_VERSION', 'latest')

    output_dir = pathlib.Path(app.outdir)

    intersphinx_mapping = config.intersphinx_mapping
    for key, value in config.pydoctor_intersphinx_mapping.items():
        url, target_path = value

        url = url.format(**{'rtd_version': rtd_version})
        inventory_path = output_dir / target_path

        intersphinx_mapping[key] = (url, str(inventory_path))

    if not config.pydoctor_args:
        raise ConfigError("Missing 'pydoctor_args'.")

    placeholders = {
        'outdir': app.outdir,
        }

    runs = config.pydoctor_args

    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    for key, value in runs.items():
        _run_pydoctor(key, ['--make-intersphinx'] + value, placeholders)


def setup(app: Sphinx) ->  Mapping[str, Any]:
    """
    Called by Sphinx when the extension is initialized.

    @return: The extension version and runtime options.
    """
    app.add_config_value("pydoctor_args", None, "env")
    app.add_config_value("pydoctor_intersphinx_mapping", {}, "env")

    # Make sure we have a lower priority than intersphinx extension.
    app.connect('config-inited', update_intersphinx_mapping, priority=799)
    app.connect('build-finished', on_build_finished)


    return {
        'version': str(__version__),
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        }
