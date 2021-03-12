"""
Parser for google-style docstrings. 

@See: L{pydoctor.epydoc.markup.numpy}
@See: L{pydoctor.epydoc.markup._napoleon}
"""
from typing import Callable, List
from pydoctor.model import Documentable
from pydoctor.epydoc.markup import ParseError, ParsedDocstring
from pydoctor.epydoc.markup._napoleon import NapoelonDocstringParser


def get_parser(obj: Documentable) -> Callable[[str, List[ParseError]], ParsedDocstring]:
    """
    Returns the parser function. Behaviour will depend on the documentable type and system options.
    """
    return NapoelonDocstringParser(obj).parse_google_docstring
