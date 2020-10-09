from pydoctor.epydoc.markup import flatten
from pydoctor.epydoc.markup.restructuredtext import parse_docstring


def rst2html(s):
    errors = []
    parsed = parse_docstring(s, errors)
    assert not errors
    return flatten(parsed.to_stan(None))

def test_rst_anon_link_target_missing():
    src = """
    This link's target is `not defined anywhere`__.
    """
    errors = []
    parse_docstring(src, errors)
    assert len(errors) == 1
    assert errors[0].descr().startswith("Anonymous hyperlink mismatch:")
    assert errors[0].is_fatal()

def test_rst_anon_link_email():
    src = "`<postmaster@example.net>`__"
    html = rst2html(src)
    assert html.startswith('<a ')
    assert ' href="mailto:postmaster@example.net"' in html
    assert html.endswith('>mailto:postmaster@example.net</a>')
