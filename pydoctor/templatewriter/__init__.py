"""Render pydoctor data as HTML."""

DOCTYPE = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''
from typing import Any, Iterable, Optional, Dict
import abc
from pathlib import Path
import warnings
import copy
from  xml.dom import minidom

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import XMLString

from pydoctor.model import System, Documentable

class TemplateVersionError(RuntimeError):
    pass

class IWriter(abc.ABC):
    """
    Interface class for pydoctor output writer. 
    """

    @abc.abstractmethod
    def __init__(self, filebase:str, template_lookup:Optional['TemplateLookup'] = None) -> None:
        pass

    @abc.abstractmethod
    def prepOutputDirectory(self) -> None:
        """
        Called first.
        """
        pass

    @abc.abstractmethod
    def writeModuleIndex(self, system:'System') -> None: 
        """
        Called second.
        """
        pass

    @abc.abstractmethod
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

    @see: L{TemplateLookup}
    """

    def __init__(self, path:Path):
        self._text: Optional[str] = None
        self.path: Path = path
        """Template file path"""

    @classmethod
    def fromfile(cls, path:Path) -> Optional['Template']:
        """
        Create a concrete template object. 
        Type depends on the file extension. 

        @param path: A L{Path} that should point to a HTML, CSS or JS file. 
        @returns: The template object or C{None} if file is invalid. 
        @warns: If the template cannot be created
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

    def is_empty(self) -> bool:
        """
        Does this template is empty? 
        Empty placeholders templates will not be rendered. 
        """
        return len(self.text.strip()) == 0

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
            with self.path.open('r') as f:
                self._text = f.read()
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
    def renderable(self) -> Optional[Any]:
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
    HTML template that works with the Twisted templating system 
    and use BeautifulSoup to parse the pydoctor-template-version meta tag. 
    """

    def __init__(self, path:Path):
        super().__init__(path)
        self._xmlstring:Optional[XMLString] = None
        self._version:Optional[int] = None
        self._dom: Optional[minidom.Document] = None

    @property
    def dom(self) -> minidom.Document:
        if self._dom is None:
            try:
                dom = minidom.parseString(self.text)
            except Exception:
                try:
                    dom = minidom.parseString(f"<div>{self.text}</div>")
                except Exception as e:
                    raise RuntimeError(f"Can't parse XML file {self.name} from string '{self.text}'") from e
                else:
                    self._dom = dom
            else:
                self._dom = dom
        return self._dom

    @property
    def version(self) -> int:
        if self._version is None:
            if self.is_empty():
                self._version = -1
            else:
                version = -1
                # If No meta pydoctor-template-version tag found, 
                # it's most probably a placeholder template. 
                for meta in self.dom.getElementsByTagName("meta"):
                    if meta.getAttribute("name") == "pydoctor-template-version":
                        if meta.hasAttribute("content"):
                            version_str = meta.getAttribute("content")
                            if version_str:
                                try:
                                    version = int(version_str)
                                except ValueError:
                                    warnings.warn(f"Could not read '{self.name}' template version: "
                                            "the 'content' attribute must be an integer")
                            else:
                                warnings.warn(f"Could not read '{self.name}' template version: "
                                    f"the 'content' attribute is empty")
                        else:
                            warnings.warn(f"Could not read '{self.name}' template version: "
                                f"the 'content' attribute is missing")
                self._version = version
        return self._version 

    @property
    def renderable(self) -> ITemplateLoader:
        if not self._xmlstring:
            self._xmlstring = XMLString(self.text)
        return self._xmlstring

class TemplateLookup:
    """
    The L{TemplateLookup} handles the HTML template files locations. 
    A little bit like C{mako.lookup.TemplateLookup} but more simple. 

    The location of the files depends wether the users set a template directory 
    with the option C{--template-dir}, custom files with matching names will be 
    loaded if present. 

    This object allow the customization of any templates, this can lead to warnings 
    when upgrading pydoctor, then, please update your template.

    @note: The HTML templates versions are independent of the pydoctor version
           and are idependent from each other.

    @see: L{Template}
    """

    _default_template_dir = 'templates'

    def __init__(self) -> None:
        """Init L{TemplateLookup} with templates in C{pydoctor/templates}"""
        # Dict comprehension to init templates to whats in pydoctor/templates
        self._templates: Dict[str, Template] = { t.name:t for t in (Template.fromfile(f) for f in 
                Path(__file__).parent.parent.joinpath(
                    self._default_template_dir).iterdir()) if t }
        
        self._default_templates = copy.deepcopy(self._templates)


    def add_template(self, template: Template) -> None:
        """
        Add a custom template to the lookup. 

        Compare the passed Template version with default template, 
        issue warnings if template are outdated.

        @raises TemplateVersionError: If the custom template is designed for a newer version of pydoctor. 
        @warns: If the custom template is designed for an older version of pydoctor. 
        """
        
        try:
            default_version = self._default_templates[template.name].version
            template_version = template.version
            if default_version and template_version != -1:
                if template_version < default_version: 
                    warnings.warn(f"Your custom template '{template.name}' is out of date, information might be missing. "
                                   "Latest templates are available to download from our github." )
                elif template_version > default_version:
                    raise TemplateVersionError(f"It appears that your custom template '{template.name}' is designed for a newer version of pydoctor."
                                        "Rendering will most probably fail. Please upgrade to latest version of pydoctor with 'pip install -U pydoctor'. ")
        except KeyError:
            warnings.warn(f"Invalid template filename '{template.name}' (will be ignored). Valid filenames are: {list(self._templates)}")
        
        self._templates[template.name] = template


    def add_templatedir(self, dir: Path) -> None:
        """
        Scan a directory and add all templates in the given directory to the lookup. 
        """
        for path in dir.iterdir():
            template = Template.fromfile(path)
            if template:
                self.add_template(template)


    def get_template(self, filename: str) -> Template:
        """
        Lookup a template based on its filename. 

        Return the custom template if provided, else the default template.

        @param filename: File name, (ie 'index.html')
        @return: The Template object
        @raises KeyError: If no template file is found with the given name
        """
        try:
            t = self._templates[filename]
        except KeyError as e:
            raise KeyError(f"Cannot find template '{filename}' in template lookup: {self}. "
                f"Valid filenames are: {list(self._templates)}") from e
        return t

from pydoctor.templatewriter.writer import TemplateWriter
TemplateWriter = TemplateWriter
__all__ = ["TemplateWriter"] # re-export as pydoctor.templatewriter.TemplateWriter
