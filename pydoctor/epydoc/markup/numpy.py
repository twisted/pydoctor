"""
Parser for numpy-style docstrings. 

@See: L{pydoctor.epydoc.markup.google}
@See: L{pydoctor.epydoc.markup._napoleon}
"""
from typing import Callable, List, Optional
from pydoctor.model import Documentable
from pydoctor.epydoc.markup import ParseError, ParsedDocstring
from pydoctor.epydoc.markup._napoleon import NapoelonDocstringParser


def get_parser(obj: Optional[Documentable]) -> Callable[[str, List[ParseError], bool], ParsedDocstring]:
    """
    Returns the parser function. Behaviour will depend on the documentable type and system options.
    """
    return NapoelonDocstringParser(obj).parse_numpy_docstring
