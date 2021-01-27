"""Miscellaneous utilities."""

from typing import Optional
import os

from pydoctor import model
from twisted.python.filepath import FilePath


def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

def templatefile(filename):
    abspath = os.path.abspath(__file__)
    pydoctordir = os.path.dirname(os.path.dirname(abspath))
    return os.path.join(pydoctordir, 'templates', filename)

def templatefilepath(filename):
    return FilePath(templatefile(filename))
