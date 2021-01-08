"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.

This was designed to generate pydoctor HTML files as part of the
Read The Docs build process.

Inside the Sphinx conf.py file you need to define the following configuration options:

  - C{pydoctor_url_path} - defined the URL path to the API documentation
                           You can use C{{rtd_version}} to have the URL automatically updated
                           based on Read The Docs build.
                         - (private usage) a mapping with values URL path definition.
                           Make sure each definition will produce a unique URL.

  - C{pydoctor_args} - Sequence with all the pydoctor command line arguments used to trigger the build.
                     - (private usage) a mapping with values as sequence of pydoctor command line arguments.

The following format placeholders are resolved for C{pydoctor_args} at runtime:
  - C{{outdir}} - the Sphinx output dir

You must call pydoctor with C{--quiet} argument
as otherwise any extra output is converted into Sphinx warnings.
"""
import os
import pathlib
import shutil
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Sequence, Mapping

from sphinx.application import Sphinx
from sphinx.errors import ConfigError
from sphinx.util import logging

from pydoctor import __version__
from pydoctor.driver import main, parse_args


logger = logging.getLogger(__name__)


def on_build_finished(app: Sphinx, exception: Exception) -> None:
    """
    Called when Sphinx build is done.
    """
    if app.builder.name != 'html':
        return

    runs = app.config.pydoctor_args
    placeholders = {
        'outdir': app.outdir,
        }

    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    for key, value in runs.items():
        arguments = _get_arguments(value, placeholders)

        options, _ = parse_args(arguments)
        output_path = pathlib.Path(options.htmloutput)
        sphinx_files = output_path.with_suffix('.sphinx_files')

        temp_path = output_path.with_suffix('.pydoctor_temp')
        shutil.rmtree(sphinx_files, ignore_errors=True)
        output_path.rename(sphinx_files)
        temp_path.rename(output_path)


def on_builder_inited(app: Sphinx) -> None:
    """
    Called to build the API documentation HTML  files
    and inject our own intersphinx inventory object.
    """
    if app.builder.name != 'html':
        return

    rtd_version = 'latest'
    if os.environ.get('READTHEDOCS', '') == 'True':
        rtd_version = os.environ.get('READTHEDOCS_VERSION', 'latest')

    config = app.config
    if not config.pydoctor_args:
        raise ConfigError("Missing 'pydoctor_args'.")

    placeholders = {
        'outdir': app.outdir,
        }

    runs = config.pydoctor_args
    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    pydoctor_url_path = config.pydoctor_url_path
    if not isinstance(pydoctor_url_path, Mapping):
        pydoctor_url_path = {'main': pydoctor_url_path}

    for key, value in runs.items():
        arguments = _get_arguments(value, placeholders)

        options, _ = parse_args(arguments)
        output_path = pathlib.Path(options.htmloutput)
        temp_path = output_path.with_suffix('.pydoctor_temp')

        # Update intersphinx_mapping.
        url_path = pydoctor_url_path.get(key)
        if url_path:
            intersphinx_mapping = config.intersphinx_mapping
            url = url_path.format(**{'rtd_version': rtd_version})
            inv = (str(temp_path / 'objects.inv'),)
            intersphinx_mapping[f'{key}-api-docs'] = (None, (url, inv))

        # Build the API docs in temporary path.
        shutil.rmtree(temp_path, ignore_errors=True)
        _run_pydoctor(key,  arguments)
        output_path.rename(temp_path)


def _run_pydoctor(name: str, arguments: Sequence[str]) -> None:
    """
    Call pydoctor with arguments.

    @param name: A human-readable description of this pydoctor build.
    @param arguments: Command line arguments used to call pydoctor.
    """
    logger.info(f"Building '{name}' pydoctor API docs as:")
    logger.info('\n'.join(arguments))

    with StringIO() as stream:
        with redirect_stdout(stream):
            main(args=arguments)

        for line in stream.getvalue().splitlines():
            logger.warning(line)


def _get_arguments(arguments: Sequence[str], placeholders: Mapping[str, str]) -> Sequence[str]:
    """
    Return the resolved arguments for pydoctor build.

    @param arguments: Sequence of proto arguments used to call pydoctor.

    @return: Sequence with actual acguments use to call pydoctor.
    """
    args = ['--make-html', '--quiet']
    for argument in arguments:
        args.append(argument.format(**placeholders))

    return args


def setup(app: Sphinx) -> Mapping[str, Any]:
    """
    Called by Sphinx when the extension is initialized.

    @return: The extension version and runtime options.
    """
    app.add_config_value("pydoctor_args", None, "env")
    app.add_config_value("pydoctor_url_path", None, "env")

    # Make sure we have a lower priority than intersphinx extension.
    app.connect('builder-inited', on_builder_inited, priority=490)
    app.connect('build-finished', on_build_finished)


    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        }
