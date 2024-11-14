"""
Parser for google-style docstrings. 

@See: L{pydoctor.epydoc.markup.numpy}
@See: L{pydoctor.epydoc.markup._napoleon}
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from pydoctor.epydoc.markup import ParserFunction
from pydoctor.epydoc.markup._napoleon import NapoelonDocstringParser
if TYPE_CHECKING:
    from pydoctor.model import Documentable


def get_parser(obj: Optional[Documentable]) -> ParserFunction:
    """
    Returns the parser function. Behaviour will depend on the documentable type and system options.
    """
    return NapoelonDocstringParser(obj).parse_google_docstring
