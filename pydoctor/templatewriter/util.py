"""Miscellaneous utilities."""

from typing import Optional, List, Any

from pydoctor.model import Documentable
from twisted.web.template import Tag, tags

def srclink(o: Documentable) -> Optional[str]:
    return o.sourceHref

def taglink(o: Documentable, label: Optional[str] = None) -> Tag:
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())
    if label is None:
        label = o.fullName()
    # Create a link to the object, with a "data-type" attribute which says what
    # kind of object it is (class, etc). This helps doc2dash figure out what it
    # is.
    ret: Tag = tags.a(href=o.url, class_="code", **{"data-type": o.kind})(label)
    return ret
