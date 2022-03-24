"""
Utilities related to Stan tree building and HTML flattening.
"""
import re
from typing import Any, Union, List, TYPE_CHECKING, cast

from twisted.web.template import Tag, XMLString, flattenString
from twisted.python.failure import Failure

if TYPE_CHECKING:
    from twisted.web.template import Flattenable
    from pydoctor.epydoc.markup import ParsedDocstring

_RE_CONTROL = re.compile((
    '[' + ''.join(
    ch for ch in map(chr, range(0, 32)) if ch not in '\r\n\t\f'
    ) + ']'
    ).encode())

def html2stan(html: Union[bytes, str]) -> Tag:
    """
    Convert an HTML string to a Stan tree.

    @param html: An HTML fragment; multiple roots are allowed.
    @return: The fragment as a tree with a transparent root node.
    """
    if isinstance(html, str):
        html = html.encode('utf8')

    html = _RE_CONTROL.sub(lambda m:b'\\x%02x' % ord(m.group()), html)
    stan = XMLString(b'<div>%s</div>' % html).load()[0]
    assert isinstance(stan, Tag)
    assert stan.tagName == 'div'
    stan.tagName = ''
    return stan

def flatten(stan: "Flattenable") -> str:
    """
    Convert a document fragment from a Stan tree to HTML.

    @param stan: Document fragment to flatten.
    @return: An HTML string representation of the C{stan} tree.
    """
    ret: List[bytes] = []
    err: List[Failure] = []
    flattenString(None, stan).addCallback(ret.append).addErrback(err.append)
    if err:
        raise err[0].value
    else:
        return ret[0].decode()

def flatten_text(stan: Union[Tag, str]) -> str:
    """Return the text inside a stan tree.
    
    @note: Only compatible with L{Tag} objects.
    """
    text = ''
    if isinstance(stan, (str)):
        text += stan
    else:
        for child in stan.children:
            if isinstance(child, (Tag, str)):
                text += flatten_text(child)
    return text

class _ParsedDocFromStan:
    def __init__(self, stan: Tag):
        self.fields: List[Any] = []
        self._stan = stan
        self.has_body = True
    def to_stan(self, docstring_linker: Any) -> Tag:
        return self._stan
    def to_node(self) -> Any:
        raise NotImplementedError()

def parsed_doc_from_stan(stan: Tag) -> 'ParsedDocstring':
    return cast('ParsedDocstring', _ParsedDocFromStan(stan))