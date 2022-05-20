"""
Utilities related to Stan tree building and HTML flattening.
"""
import re
from types import GeneratorType
from typing import Union, List, TYPE_CHECKING

from twisted.web.template import Tag, XMLString, flattenString
from twisted.python.failure import Failure

if TYPE_CHECKING:
    from twisted.web.template import Flattenable

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
    if not html.startswith(b'<?xml'):
        stan = XMLString(b'<div>%s</div>' % html).load()[0]
        assert isinstance(stan, Tag)
        assert stan.tagName == 'div'
    else:
        stan = XMLString(b'%s' % html).load()[0]
        assert isinstance(stan, Tag)
        assert stan.tagName == 'html'
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

def flatten_text(stan: Union[Tag, str, List[Tag]]) -> str:
    """Return the text inside a stan tree.
    
    @note: Only compatible with L{Tag} objects.
    """
    text = ''
    if isinstance(stan, (str)):
        text += stan
    elif isinstance(stan, (GeneratorType)):
        text += flatten_text(list(stan))
    elif isinstance(stan, (list)):
        for child in stan:
            text += flatten_text(child)
    else:
        if isinstance(stan, Tag):
            for child in stan.children:
                text += flatten_text(child)
        else:
            pass
            # flatten_text() does not support the object received.
            # Since this function is currently only used in the tests
            # it's ok to silently ignore the unknown flattenable, which can be
            # a Comment for instance. 
            # Actually, some tests fails if we try to raise
            # an error here instead of ignoring.
    return text
