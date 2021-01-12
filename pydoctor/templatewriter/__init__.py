"""Render pydoctor data as HTML."""

DOCTYPE = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''
from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional, Dict
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
    def __init__(self, filebase:str, template_lookup:Optional['TemplateLookup'] = None):
        pass

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
    def writeIndividualFiles(self, obs:Iterable['Documentable']) -> None:
        """
        Called last.
        """
        pass

class Template(abc.ABC):
    """
    Represents a pydoctor template file. 
    
    It holds references to template information. 

    It's an additionnal level of abstraction to hook to the 
    rendering system, it stores the renderable object that 
    is going to be reused for each output file using this template. 

    Use L{Template.fromfile} to create Templates. 
    """

    def __init__(self, path:Path):
        """
        Template is constructed using a Path that should point to a file. 
        """
        self._text: Optional[str] = None
        self.path: Path = path

    @classmethod
    def fromfile(cls, path:Path) -> Optional['Template']:
        """
        Create a concrete template object. Type depends on the file extension. 
        @returns: the template object or None if file is invalid. 
        """
        if not path.is_file():
            warnings.warn(f"Cannot create Template: {path.as_posix()} is not a file.")
        elif path.suffix.lower() == '.html':
            return _HtmlTemplate(path)
        elif path.suffix.lower() in ['.css', '.js']:
            return _SimpleTemplate(path)
        else:
            warnings.warn(f"Cannot create Template: {path.as_posix()} is not a template file.")
        return None

    @property
    def name(self) -> str:
        """
        Template filename
        """
        return self.path.name

    @property
    def text(self) -> str:
        """
        File text 
        """
        if not self._text:
            self._text = self.path.open('r').read()
        return self._text

    @abc.abstractproperty
    def version(self) -> int:
        """
        Template version, C{-1} if no version. 

        HTML Templates should have a version identifier as follow::
    
            <meta name="pydoctor-template-version" content="1" />

        This is always C{-1} for CSS and JS templates. 
        """
        pass

    @abc.abstractproperty
    def renderable(self) -> Any:
        """
        Object that is used to render the final file. 

        For HTML templates, this is a L{ITemplateLoader}. 

        For CSS and JS templates, this is C{None} 
        because there is no rendering to do, it's already the final file.  
        """
        pass

class _SimpleTemplate(Template):
    """
    Simple template with no rendering for CSS and JS templates. 
    """
    @property
    def version(self) -> int:
        return -1
    @property
    def renderable(self) -> None:
        return None

class _HtmlTemplate(Template):
    """
    HTML template that works with the Twisted templating system. 
    """

    def __init__(self, path:Path):
        super().__init__(path)
        self._xmlfile:Optional[XMLFile] = None
        self._version:Optional[int] = None

    @property
    def version(self) -> int:
        if self._version == None:
            if not self.text:
                self._version = -1
            else:
                soup = BeautifulSoup(self.text, 'html.parser')
                res = soup.find_all("meta", attrs=dict(name="pydoctor-template-version"))
                try:
                    meta = res.pop()
                    version_str = meta['content']
                    self._version = int(version_str)
                except IndexError:
                    # No meta pydoctor-template-version tag found, 
                    # most probably a placeholder template. 
                    self._version = -1
                except KeyError as e:
                    warnings.warn(f"Cannot get meta pydoctor-template-version tag content: {e}")
                    self._version = -1
                except ValueError as e:
                    warnings.warn(f"Cannot cast template version to int: {e}")
                    self._version = -1

        # mypy gets error: Incompatible return value type (got "Optional[int]", expected "int")  [return-value]
        # It's ok to ignore mypy error because the version is set to an int if it's None
        return self._version # type: ignore 

    @property
    def renderable(self) -> ITemplateLoader:
        if not self._xmlfile:
            self._xmlfile = XMLFile(FilePath(self.path.as_posix()))
        return self._xmlfile

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
        # Dict comprehension to init templates to whats in pydoctor/templates
        self._templates: Dict[str, Template] = { t.name:t for t in (Template.fromfile(f) for f in 
                Path(__file__).parent.parent.joinpath(
                    self._default_template_dir).iterdir()) if t }


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
        for path in dir.iterdir():
            template = Template.fromfile(path)
            if template:
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