"""
Parser for google-style docstrings. 

@See: L{pydoctor.epydoc.markup.numpy}
@See: L{pydoctor.epydoc.markup._napoleon}
"""
from __future__ import annotations

from pydoctor.epydoc.markup import ObjClass, ParserFunction
from pydoctor.epydoc.markup._napoleon import NapoelonDocstringParser


def get_parser(objclass: ObjClass | None) -> ParserFunction:
    """
    Returns the parser function. Behaviour will depend on the documentable type and system options.
    """
    return NapoelonDocstringParser(objclass).parse_google_docstring
