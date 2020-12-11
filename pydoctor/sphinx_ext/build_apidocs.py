"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.

This was designed to generate pydoctor HTML files as part of the
Read The Docs build process.

Inside the Sphinx conf.py file you need to define the following configuration options:

  - C{pydoctor_args} - an iterable with all the pydoctor command line arguments used to trigger the build.
                     - (private usage) a mapping with values as iterables of pydoctor command line arguments.

  - C{pydoctor_git_reference} - The branch name or SHA reference for current build.
  - C{pydoctor_debug} - C{True} if you want to see extra debug message for this extension.

The following format placeholders are resolved for C{pydoctor_args} at runtime:
  - C{{outdir}} - the Sphinx output dir
  - C{{git_reference}} - the Git reference that can be used for source code links.

You must call pydoctor with C{--quiet} argument
as otherwise any extra output is converted into Sphinx warnings.
"""
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Iterable, Mapping

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError
from sphinx.util import logging

from pydoctor import __version__
from pydoctor.driver import main
from pydoctor.sphinx_ext import get_git_reference

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
        'git_reference': get_git_reference(
            main_branch=config.pydoctor_main_branch,
            debug=config.pydoctor_debug,
            ),
        }

    runs = config.pydoctor_args

    if not isinstance(runs, Mapping):
        # We have a single pydoctor call
        runs = {'main': runs}

    for key, value in runs.items():
        _run_pydoctor(key, value, placeholders)


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

    logger.info(f"Building '{name}' pydoctor API docs as:")
    logger.info('\n'.join(args))

    with StringIO() as stream:
        with redirect_stdout(stream):
            main(args=args)

        for line in stream.getvalue().splitlines():
            logger.warning(line)


def setup(app: Sphinx) ->  Mapping[str, Any]:
    """
    Called by Sphinx when the extension is initialized.

    @return: The extension version and runtime options.
    """
    app.connect('build-finished', on_build_finished)
    app.add_config_value("pydoctor_args", None, "env")
    app.add_config_value("pydoctor_main_branch", "main", "env")
    app.add_config_value("pydoctor_debug", False, "env")

    return {
        'version': str(__version__),
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        }
