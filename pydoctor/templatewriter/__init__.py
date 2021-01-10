"""Render pydoctor data as HTML."""

DOCTYPE:bytes = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''
from abc import ABC, abstractmethod
from typing import List
from pydoctor.model import System, Documentable

class IWriter(ABC):
    """
    Declarative class for any pydoctor output writer. 
    """

    @abstractmethod
    def prepOutputDirectory(self) -> None:
        """
        Called first.
        """
        pass

    @abstractmethod
    def writeModuleIndex(self, system:'System') -> None: 
        """
        Called second.
        """
        pass

    @abstractmethod
    def writeIndividualFiles(self, obs:List['Documentable']) -> None:
        """
        Called last.
        """
        pass

from pydoctor.templatewriter.writer import TemplateWriter
TemplateWriter = TemplateWriter