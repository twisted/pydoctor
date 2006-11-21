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

def templatefile(filename):
    abspath = os.path.abspath(__file__)
    pydoctordir = os.path.dirname(os.path.dirname(abspath))
    return os.path.join(pydoctordir, 'templates', filename)

def fillSlots(tag, **kw):
    for k, v in kw.iteritems():
        tag = tag.fillSlots(k, v)
    return tag

from nevow import flat

_taglink = tags.invisible[
    flat.precompile(tags.a(href=tags.slot('href'))[tags.slot('label')])
    ].freeze()

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
    return fillSlots(_taglink, href=linktext, label=label)
