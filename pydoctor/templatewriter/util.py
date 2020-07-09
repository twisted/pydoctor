"""Miscellaneous utilities."""

from urllib.parse import quote
import os

from pydoctor import model
from twisted.python.filepath import FilePath
from twisted.web.template import tags

def link(o):
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())
    return quote(o.fullName()+'.html')

def srclink(o):
    return o.sourceHref

def templatefile(filename):
    abspath = os.path.abspath(__file__)
    pydoctordir = os.path.dirname(os.path.dirname(abspath))
    return os.path.join(pydoctordir, 'templates', filename)

def templatefilepath(filename):
    return FilePath(templatefile(filename))

def taglink(o, label=None):
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())
    if label is None:
        label = o.fullName()
    if o.documentation_location is model.DocLocation.PARENT_PAGE:
        p = o.parent
        if isinstance(p, model.Module) and p.name == '__init__':
            p = p.parent
        linktext = link(p) + '#' + quote(o.name)
    elif o.documentation_location is model.DocLocation.OWN_PAGE:
        linktext = link(o)
    else:
        raise AssertionError(
            "Unknown documentation_location: %s" % o.documentation_location)
    # Create a link to the object, with a "data-type" attribute which says what
    # kind of object it is (class, etc). This helps doc2dash figure out what it
    # is.
    return tags.a(href=linktext, class_="code", **{"data-type":o.kind})(label)
