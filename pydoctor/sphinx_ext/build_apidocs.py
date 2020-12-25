"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.

This was designed to generate pydoctor HTML files as part of the
Read The Docs build process.

Inside the Sphinx conf.py file you need to define the following configuration options:

  - C{pydoctor_url_path} - defined the URL path to the API documentation
                           You can use C{{rtd_version}} to have the URL automatically updated
                           based on Read The Docs build.

  - C{pydoctor_args} - Sequence with all the pydoctor command line arguments used to trigger the build.
                     - (private usage) a mapping with values as sequence of pydoctor command line arguments.

  - C{pydoctor_debug} - C{True} if you want to see extra debug message for this extension.

The following format placeholders are resolved for C{pydoctor_args} at runtime:
  - C{{outdir}} - the Sphinx output dir
  - C{{source_reference}} - the source reference that can be used for source code links.
                            Only git is supported for now.

You must call pydoctor with C{--quiet} argument
as otherwise any extra output is converted into Sphinx warnings.
"""
import os
import pathlib
import shutil
from contextlib import redirect_stdout
from io import StringIO
from pprint import pprint
from typing import Any, Dict, Sequence, Mapping

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError
from sphinx.util import logging

from pydoctor import __version__
from pydoctor.driver import main, parse_args
from pydoctor.sphinx_ext import get_source_reference

logger = logging.getLogger(__name__)

# Shared state between init and finish.
_placeholders: Dict[str, str] = {}


def on_build_finished(app: Sphinx, exception: Exception) -> None:
    """
    Called when Sphinx build is done.
    """
    runs = app.config.pydoctor_args

    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    for key, value in runs.items():
        arguments = _get_arguments(value, _placeholders)

        options, _ = parse_args(arguments)
        output_path = pathlib.Path(options.htmloutput)
        sphinx_files = output_path.with_suffix('.sphinx_files')

        temp_path = output_path.with_suffix('.pydoctor_temp')
        shutil.rmtree(sphinx_files, ignore_errors=True)
        output_path.rename(sphinx_files)
        temp_path.rename(output_path)


def on_config_inited(app: Sphinx, config: Config) -> None:
    """
    Called to build the API documentation HTML  files
    and inject our own intersphinx inventory object.
    """
    rtd_version = 'latest'
    if os.environ.get('READTHEDOCS', '') == 'True':
        rtd_version = os.environ.get('READTHEDOCS_VERSION', 'latest')

    if not config.pydoctor_args:
        raise ConfigError("Missing 'pydoctor_args'.")

    placeholders = {
        'outdir': app.outdir,
        }

    runs = config.pydoctor_args

    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    # Defer resolving the git reference for only when asked by
    # end users.
    is_source_reference_needed = any(
        '{source_reference}' in arg
        for value in runs.values() for arg in value
        )

    if is_source_reference_needed:
        placeholders['source_reference'] = get_source_reference()

    for key, value in runs.items():
        arguments = _get_arguments(value, placeholders)

        options, _ = parse_args(arguments)
        output_path = pathlib.Path(options.htmloutput)
        temp_path = output_path.with_suffix('.pydoctor_temp')

        # Update intersphinx_mapping.
        pydoctor_url_path = config.pydoctor_url_path
        if pydoctor_url_path:
            intersphinx_mapping = config.intersphinx_mapping
            url = pydoctor_url_path.format(**{'rtd_version': rtd_version})
            intersphinx_mapping[key + '-api-docs'] = (url, str(temp_path / 'objects.inv'))

        # Build the API docs in temporary path.
        shutil.rmtree(temp_path, ignore_errors=True)
        _run_pydoctor(key,  arguments)
        output_path.rename(temp_path)

    # Share placeholders between init and finish.
    _placeholders.update(placeholders)

    if config.pydoctor_debug:
        print("== Environment dump ===")
        pprint(dict(os.environ))
        print("== Placeholders dump ===")
        pprint(placeholders)
        print("== intersphinx_mapping dump ===")
        pprint(intersphinx_mapping)
        print("======")


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


def setup(app: Sphinx) ->  Mapping[str, Any]:
    """
    Called by Sphinx when the extension is initialized.

    @return: The extension version and runtime options.
    """
    app.add_config_value("pydoctor_args", None, "env")
    app.add_config_value("pydoctor_url_path", "", "env")
    app.add_config_value("pydoctor_debug", False, "env")

    # Make sure we have a lower priority than intersphinx extension.
    app.connect('config-inited', on_config_inited, priority=790)
    app.connect('build-finished', on_build_finished)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        }
