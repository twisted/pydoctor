"""Miscellaneous utilities."""

from typing import Optional
import os

from pydoctor import model
from twisted.python.filepath import FilePath
from twisted.web.template import Tag, tags


def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename):
    abspath = os.path.abspath(__file__)
    pydoctordir = os.path.dirname(os.path.dirname(abspath))
    return os.path.join(pydoctordir, 'templates', filename)

def templatefilepath(filename):
    return FilePath(templatefile(filename))

def taglink(o: model.Documentable, page_url: str, label: Optional[str] = None) -> Tag:
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())

    if label is None:
        label = o.fullName()

    url = o.url
    if url.startswith(page_url + '#'):
        # When linking to an item on the same page, omit the path.
        # Besides shortening the HTML, this also avoids the page being reloaded
        # if the query string is non-empty.
        url = url[len(page_url):]

    # Create a link to the object, with a "data-type" attribute which says what
    # kind of object it is (class, etc). This helps doc2dash figure out what it
    # is.
    ret: Tag = tags.a(href=url, class_="code", **{"data-type": o.kind})(label)
    return ret
