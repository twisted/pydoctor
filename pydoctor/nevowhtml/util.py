from pydoctor import model

from nevow import tags

import os, urllib

def link(o):
    return o.system.urlprefix+urllib.quote(o.fullName()+'.html')

def srclink(o):
    system = o.system
    if not system.sourcebase:
        return None
    m = o
    while not isinstance(m, (model.Module, model.Package)):
        m = m.parent
        if m is None:
            return None
    sourceHref = '%s/%s'%(system.sourcebase, m.fullName().replace('.', '/'),)
    if isinstance(m, model.Module):
        sourceHref += '.py'
    if isinstance(o, model.Module):
        sourceHref += '#L1'
    elif hasattr(o, 'linenumber'):
        sourceHref += '#L'+str(o.linenumber)
    return sourceHref

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

def fillSlots(tag, **kw):
    for k, v in kw.iteritems():
        tag = tag.fillSlots(k, v)
    return tag

def taglink(o, label=None):
    if label is None:
        label = o.fullName()
    if o.document_in_parent_page:
        p = o.parent
        if isinstance(p, model.Module) and p.name == '__init__':
            p = p.parent
        linktext = link(p) + '#' + urllib.quote(o.name)
    else:
        linktext = link(o)
    return tags.a(href=linktext)[label]
