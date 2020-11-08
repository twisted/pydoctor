"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.

Inside the Sphinx conf.py file you need to define the following configuration options:

* pydoctor_cwd: Absolute path in which the pydoctor build is trigerred.
* pydoctor_args: A list with all the pydoctor command line arguments used to trigger the build.

You must call pydoctor with `--quiet` argument
as otherwise any extra output is converted into Sphinx warnings.
"""
import os
from sphinx.util import logging
from sphinx.errors import ConfigError

from contextlib import redirect_stdout
from io import StringIO
from pydoctor import __version__
from pydoctor.driver import main

logger = logging.getLogger(__name__)


def on_build_finished(app, exception):
    """
    Called when Sphinx build is done.
    """
    if not app.config.pydoctor_args:
        raise ConfigError("Missing 'pydoctor_args'.")

    if not app.config.pydoctor_cwd:
        raise ConfigError("Missing 'pydoctor_cwd'.")

    placeholders = {
        'outdir': app.outdir,
        }

    args = []
    for argument in app.config.pydoctor_args:
        args.append(argument.format(**placeholders))

    stream = StringIO()

    old_cwd = os.getcwd()
    try:
        os.chdir(app.config.pydoctor_cwd)

        logger.info("Bulding pydoctor API docs with CWD %s and arguments:" % (os.getcwd(),))
        logger.info('\n'.join(args))

        with redirect_stdout(stream):
            main(args=args)
    finally:
        os.chdir(old_cwd)

    for line in stream.getvalue().splitlines():
        logger.warning(line)


def setup(app):
    app.connect('build-finished', on_build_finished)
    app.add_config_value("pydoctor_cwd", "", "env")
    app.add_config_value("pydoctor_args", [], "env")

    return {
            'version': str(__version__),
            'parallel_read_safe': True,
            'parallel_write_safe': True,
        }
