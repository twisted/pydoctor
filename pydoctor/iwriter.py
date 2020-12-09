from abc import ABC, abstractmethod
import os
from typing import List
from . import model
class IWriter(ABC):
    """
    PyDoctor Output writer interface. 
    """

    def __init__(self, filebase:str):
        """
        @arg filebase: Output directory. 
        """
        self.base = filebase

    @abstractmethod
    def prepOutputDirectory(self) -> None:
        """
        Called first.
        """
        os.makedirs(self.base, exist_ok=True)

    @abstractmethod
    def writeModuleIndex(self, system:'model.System') -> None: 
        """
        Called second.
        """
        pass

    @abstractmethod
    def writeIndividualFiles(self, obs:List['model.Documentable'], functionpages:bool=False) -> None:
        """
        Called last.
        """
        pass
