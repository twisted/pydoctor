"""
Generate the API docs using pydoctor to be integrated into Sphinx build system.
"""
import os
from sphinx.util import logging

from contextlib import redirect_stdout
from io import StringIO
from pydoctor.driver import main

logger = logging.getLogger(__name__)


def on_build_finished(app, exception):
    """
    Called when Sphinx build is done.
    """
    placeholders = {
        'outdir': app.outdir,
        }

    args = []
    for argument in app.config.pydoctor_args:
        args.append(argument.format(**placeholders))


    logger.info("Building pydoctor API docs using arguments:")
    logger.info('\n'.join(args))

    stream = StringIO()
    with redirect_stdout(stream):
        main(args=args)

    for line in stream.getvalue().splitlines():
        logger.warning(line)


def setup(app):
    app.connect('build-finished', on_build_finished)
    app.add_config_value("pydoctor_args", [], "env")

    return {
            'version': '0.1',
            'parallel_read_safe': True,
            'parallel_write_safe': True,
        }
