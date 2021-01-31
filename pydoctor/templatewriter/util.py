"""Miscellaneous utilities."""

from typing import Optional

from pydoctor.model import Documentable
from pydoctor.templatewriter import TemplateLookup
from twisted.python.filepath import FilePath

def srclink(o: Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename: str) -> str:
    """Deprecated"""
    return TemplateLookup().get_template(filename).path.as_posix()

def templatefilepath(filename:str) -> FilePath:
    """Deprecated"""
    return FilePath(templatefile(filename))
