"""Miscellaneous utilities for the HTML writer."""

from typing import Optional
import os

from twisted.python.filepath import FilePath
from twisted.web.template import Element, Tag, renderer, tags

from pydoctor import model
from pydoctor.epydoc2stan import format_kind

def css_class(o: model.Documentable) -> str:
    """
    A short, lower case description for use as a CSS class in HTML. 
    Includes the kind and privacy. 
    """
    kind = o.kind
    assert kind is not None # if kind is None, object is invisible
    class_ = format_kind(kind).lower().replace(' ', '')
    if o.privacyClass is model.PrivacyClass.PRIVATE:
        class_ += ' private'
    return class_

def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename):
    abspath = os.path.abspath(__file__)
    pydoctordir = os.path.dirname(os.path.dirname(abspath))
    return os.path.join(pydoctordir, 'templates', filename)

def templatefilepath(filename):
    return FilePath(templatefile(filename))


class Page(Element):

    def __init__(self, system: model.System):
        super().__init__()
        self.system = system

    @property
    def project_tag(self) -> Tag:
        system = self.system
        projecturl: Optional[str] = system.options.projecturl
        tag: Tag = tags.a(href=projecturl) if projecturl else tags.transparent
        tag(system.projectname)
        return tag

    @renderer
    def project(self, request, tag):
        return self.project_tag
