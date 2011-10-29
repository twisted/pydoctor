"""Miscellaneous utilities."""

from pydoctor import model

from nevow import tags

import os, urllib

def link(o):
    if not o.isVisible:
        o.system.warning("html", "don't link to %s"%o.fullName())
    return o.system.urlprefix+urllib.quote(o.fullName()+'.html')

def srclink(o):
    return o.sourceHref

def templatefile(filename):
    abspath = os.path.abspath(__file__)
    pydoctordir = os.path.dirname(os.path.dirname(abspath))
    return os.path.join(pydoctordir, 'templates', filename)

def fillSlots(tag, **kw):
    for k, v in kw.iteritems():
        tag = tag.fillSlots(k, v)
    return tag

def taglink(o, label=None, tags=tags):
    if not o.isVisible:
        o.system.warning("html", "don't link to %s"%o.fullName())
    if label is None:
        label = o.fullName()
    if o.document_in_parent_page:
        p = o.parent
        if isinstance(p, model.Module) and p.name == '__init__':
            p = p.parent
        linktext = link(p) + '#' + urllib.quote(o.name)
    else:
        linktext = link(o)
    import nevow.tags
    if isinstance(tags.a, nevow.tags.Tag):
        return tags.a(href=linktext)[label]
    else:
        return tags.a(href=linktext)(label)
