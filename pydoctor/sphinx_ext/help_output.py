"""
Produce the pydoctor help output to be included in the documentation.
"""
from docutils import nodes
from docutils.parsers.rst import Directive

from contextlib import redirect_stdout
from io import StringIO
from typing import List, Mapping, TYPE_CHECKING

from pydoctor.driver import parse_args


if TYPE_CHECKING:
    from sphinx.application import Sphinx


class HelpOutputDirective(Directive):
    """
    Directive that will generate the pydoctor help as block literal.
    """
    has_content = True

    def run(self) -> List[nodes.Node]:

        stream = StringIO()
        try:
            with redirect_stdout(stream):
                parse_args(['--help'])
        except SystemExit:
            pass

        text = ['pydoctor --help'] + stream.getvalue().splitlines()[1:]
        return [nodes.literal_block(text='\n'.join(text))]


def setup(app: 'Sphinx') -> Mapping[str, object]:
    app.add_directive('help_output', HelpOutputDirective)

    return {
            'version': '0.1',
            'parallel_read_safe': True,
            'parallel_write_safe': True,
        }
