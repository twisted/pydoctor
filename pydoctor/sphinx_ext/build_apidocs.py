"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.

This was designed to generate pydoctor HTML files as part of the
Read The Docs build process.

Inside the Sphinx conf.py file you need to define the following configuration options:

* pydoctor_args: A list with all the pydoctor command line arguments used to trigger the build.

The following format placeholders are resolved for pydoctor_args at runtime:
* `{outdir}` the Sphinx output dir

You must call pydoctor with `--quiet` argument
as otherwise any extra output is converted into Sphinx warnings.
"""
import os
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Dict, TYPE_CHECKING

from sphinx.errors import ConfigError
from sphinx.util import logging

from pydoctor import __version__
from pydoctor.driver import main

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


def on_build_finished(app: 'Sphinx', exception: Exception) -> None:
    """
    Called when Sphinx build is done.
    """
    if not app.config.pydoctor_args:
        raise ConfigError("Missing 'pydoctor_args'.")

    placeholders = {
        'outdir': app.outdir,
        }

    args = []
    for argument in app.config.pydoctor_args:
        args.append(argument.format(**placeholders))

    logger.info("Bulding pydoctor API docs as:")
    logger.info('\n'.join(args))

    with StringIO() as stream:
        with redirect_stdout(stream):
            main(args=args)

        for line in stream.getvalue().splitlines():
            logger.warning(line)


def setup(app: 'Sphinx') ->  Dict[str, Any]:
    app.connect('build-finished', on_build_finished)
    app.add_config_value("pydoctor_args", [], "env")

    return {
        'version': str(__version__),
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        }
