from typing import List

from pydoctor.epydoc.markup import ParseError
from pydoctor.epydoc.markup.restructuredtext import parse_docstring


def test_rst_anon_link_target_missing() -> None:
    src = """
    This link's target is `not defined anywhere`__.
    """
    errors: List[ParseError] = []
    parse_docstring(src, errors)
    assert len(errors) == 1
    assert errors[0].descr().startswith("Anonymous hyperlink mismatch:")
    assert errors[0].is_fatal()
