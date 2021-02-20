"""Miscellaneous utilities."""

import warnings
from typing import Optional
from pydoctor.model import Documentable

def srclink(o: Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename: str) -> None:
    """Deprecated"""
    warnings.warn("pydoctor.templatewriter.util.templatefile() "
        "is deprecated and will be remove in future versions. "
        "Please use the templating system.")
    return None

def templatefilepath(filename:str) -> None:
    """Deprecated"""
    warnings.warn("pydoctor.templatewriter.util.templatefilepath() "
        "is deprecated and will be remove in future versions. "
        "Please use the templating system.")
    return None
