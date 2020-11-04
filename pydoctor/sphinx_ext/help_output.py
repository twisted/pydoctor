"""
Produce the pydoctor help output to be included in the documentation.
"""
from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from contextlib import redirect_stdout
from io import StringIO
from pydoctor.driver import parse_args


class HelpOutputDirective(SphinxDirective):

    # this enables content in the directive
    has_content = True

    def run(self):

        stream = StringIO()
        try:
            with redirect_stdout(stream):
                parse_args(['--help'])
        except SystemExit:
            pass

        text = ['pydoctor --help'] + stream.getvalue().splitlines()[1:]
        return [nodes.literal_block(text='\n'.join(text))]


def setup(app):
    app.add_directive('help_output', HelpOutputDirective)

    return {
            'version': '0.1',
            'parallel_read_safe': True,
            'parallel_write_safe': True,
        }


