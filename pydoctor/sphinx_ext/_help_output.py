"""
Private extension that produces the pydoctor help output to be included in the documentation.
"""
from docutils import nodes
from docutils.parsers.rst import Directive

from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Dict, List, TYPE_CHECKING

from pydoctor import __version__
from pydoctor.driver import parse_args


if TYPE_CHECKING:
    from sphinx.application import Sphinx


class HelpOutputDirective(Directive):
    """
    Directive that will generate the pydoctor help as block literal.

    It takes no options or input value.
    """
    has_content = True

    def run(self) -> List[nodes.Node]:
        """
        Called by docutils each time the directive is found.
        """

        stream = StringIO()
        try:
            with redirect_stdout(stream):
                parse_args(['--help'])
        except SystemExit:
            # The stdlib --help handling triggers system exit.
            pass

        text = ['pydoctor --help'] + stream.getvalue().splitlines()[1:]
        return [nodes.literal_block(text='\n'.join(text), language='text')]


def setup(app: 'Sphinx') -> Dict[str, Any]:
    """
    Called by Sphinx when the extensions is loaded.
    """
    app.add_directive('help_output', HelpOutputDirective)

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        }
