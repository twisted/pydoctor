"""Miscellaneous utilities for the HTML writer."""

import warnings
from typing import Optional
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

def templatefile(filename: str) -> None:
    """Deprecated: can be removed once Twisted stops patching this."""
    warnings.warn("pydoctor.templatewriter.util.templatefile() "
        "is deprecated and returns None. It will be remove in future versions. "
        "Please use the templating system.")
    return None
