"""Render pydoctor data as HTML."""

DOCTYPE = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict
import abc
from pathlib import Path
import warnings
from twisted.web.iweb import ITemplateLoader

from twisted.web.template import XMLFile
from twisted.python.filepath import FilePath
from bs4 import BeautifulSoup

from pydoctor.model import System, Documentable

class IWriter(ABC):
    """
    Interface class for pydoctor output writer. 
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

class Template(abc.ABC):
    """
    Represents a pydoctor template file. 
    
    It holds references to template data. 
    """

    def __init__(self, path:Path):
        """
        Template is constructed using a Path that should point to a file. 
        """
        self._text: Optional[str] = None
        self.path: Path = path
        if not self.path.is_file():
            raise FileNotFoundError(f"Cannot find the template file: '{self.path}'")

    @property
    def name(self) -> str:
        """
        Template filename
        """
        return self.path.name

    @property
    def text(self) -> str:
        """
        Raw file text 
        """
        if not self._text:
            self._text = self.path.open('r').read()
        return self._text

    @abc.abstractproperty
    def version(self) -> int:
        """
        Template version, C{-1} if no version. 
        """
        pass

    @abc.abstractproperty
    def renderable(self) -> Any:
        """
        Object that is used to render the final file. 

        For HTML templates, this will return a L{ITemplateLoader}. 

        For CSS and JS templates, this will return C{None} 
        as there is no rendering to do with those, it's already the final file.  
        """
        pass

class SimpleTemplate(Template):
    """
    Simple template file with no rendering for CSS and JS templates. 
    """
    @property
    def version(self) -> int:
        return -1
    @property
    def renderable(self) -> None:
        return None

class HtmlTemplate(Template):
    """
    HTML template that works with the Twisted templating system. 
    """

    def __init__(self, path:Path):
        super().__init__(path)
        self._xmlfile:Optional[XMLFile] = None
        self._version:Optional[int] = None

    @property
    def version(self) -> int:
        """
        @returns The template version as L{int}, C{-1} if no version was detected.
        """
        if self._version == None:
            soup = BeautifulSoup(self.text, 'html.parser')
            res = soup.find_all("meta", attrs=dict(name="pydoctor-template-version"))
            if res:
                try:
                    self._version = int(res[0]['content'])
                except (ValueError, KeyError):
                    self._version = -1
            else:
                self._version = -1

        # mypy gets error: Incompatible return value type (got "Optional[int]", expected "int")  [return-value]
        # It's ok to ignore mypy error because the version is parsed if it's None
        return self._version # type: ignore 

    @property
    def renderable(self) -> ITemplateLoader:
        """Get the L{ITemplateLoader} """
        if not self._xmlfile:
            self._xmlfile = XMLFile(FilePath(self.path.as_posix()))
        return self._xmlfile

class TemplateCollection(List[Template]):
    """
    List container to reflect the content of templates directory.
    """

    @classmethod
    def fromdir(cls, dir:Path) -> 'TemplateCollection':
        """
        Scan a directory and create concrete Template objects 
        depending on the file extensions. 
        """
        collection = cls()
        for path in dir.iterdir():
            if path.is_file():
                if path.suffix.lower() == '.html':
                    collection.append(HtmlTemplate(
                        path=path
                    ))
                elif path.suffix.lower() in ['.css', '.js']:
                    collection.append(SimpleTemplate(
                        path=path
                    ))
                else:
                    warnings.warn(f"Ignored file in template directory: {path.as_posix()}")
            else:
                warnings.warn(f"Ignored not-file in template directory: {path.as_posix()}")
        return collection
            

class TemplateLookup:
    """
    The L{TemplateLookup} handles the HTML template files locations. 
    A little bit like C{mako.lookup.TemplateLookup} but more simple. 

    The location of the files depends wether the users set a template directory 
    with the option C{--template-dir}, custom files with matching names will be 
    loaded if present. 

    This object allow the customization of any templates, this can lead to warnings 
    when upgrading pydoctor, then, please update your template.

    @Note: The HTML templates versions are independent of the pydoctor version
           and are idependent from each other. They are all initialized to '1.0'.

    """

    _default_template_dir = 'templates'

    def __init__(self) -> None:
        templates = TemplateCollection.fromdir(
          Path(__file__).parent.parent.joinpath(
            self._default_template_dir))
        self._templates: Dict[str, Template] = {t.name:t for t in templates}


    def add_template(self, template:Template) -> None:
        """
        Add a custom template to the lookup. 

        Check the template version against current template, 
        issue warnings when custom templates are outdated.
        """
        
        try:
            default_version = self.get_template_version(template.name)

            template_version = template.version
            if default_version:
                if template_version < default_version: 
                    warnings.warn(f"Your custom template '{template.name}' is out of date, information might be missing."
                                            " Latest templates are available to download from our github.")
                elif template_version > default_version:
                    raise RuntimeError(f"It appears that your custom template '{template.name}' is designed for a newer version of pydoctor."
                                            "Rendering will most probably fail, so we're crashing now. Upgrade to latest version of pydoctor with 'pip install -U pydoctor'. ")
        except FileNotFoundError as e:
            raise RuntimeError(f"Invalid template filename '{template.name}'. Valid names are: {list(self._templates)}") from e
        
        self._templates[template.name] = template


    def add_templatedir(self, dir:Path) -> None:
        """
        Add all templates in the given directory to the lookup. 
        """
        for template in TemplateCollection.fromdir(dir):
            self.add_template(template)


    def get_template(self, filename:str) -> Template:
        """
        Lookup a template based on it's filename. 

        Return the custom template if provided, else the default template.

        @param filename: File name, (ie 'index.html')
        @return: The Template object
        @raises FileNotFoundError: If the template file do not exist
        """
        t = self._templates.get(filename, None)
        if not t:
            raise FileNotFoundError(f"Cannot find template: '{filename}' in template lookup: {self._templates}")
        return t

    def get_template_version(self, filename: str) -> int: 
        """
        Get a template version. 

        @arg filename: Template file name
        @return: The template version as int
        @raises FileNotFoundError: If the template file do not exist
        """
        return self.get_template(filename).version

from pydoctor.templatewriter.writer import TemplateWriter
TemplateWriter = TemplateWriter