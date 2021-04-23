"""Miscellaneous utilities."""

import warnings
from typing import Optional
from pydoctor.model import Documentable

def srclink(o: Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename: str) -> None:
    """Deprecated: can be removed once Twisted stops patching this."""
    warnings.warn("pydoctor.templatewriter.util.templatefile() "
        "is deprecated and returns None. It will be remove in future versions. "
        "Please use the templating system.")
    return None
