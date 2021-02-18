"""Render pydoctor data as HTML."""

DOCTYPE = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''
from typing import Iterable, List, Optional, Dict, Protocol, overload, runtime_checkable
import abc
from pathlib import Path
import warnings
import copy
from  xml.dom import minidom

from zope.interface import implementer

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import XMLString

from pydoctor.model import System, Documentable

def parse_dom(text: str) -> minidom.Document:
    """
    Create a L{minidom} representaton of the XML string. 
    """
    try:
        dom = minidom.parseString(text)
    except Exception as e:
        raise ValueError(f"Can't parse XML from text '{text}'. XML documents can have only one root. ") from e
    else:
        return dom

class UnsupportedTemplateVersion(Exception):
    """Raised when custom template is designed for a newer version of pydoctor"""
    pass

@runtime_checkable
class IWriter(Protocol):
    """
    Interface class for pydoctor output writer. 
    """

    @overload
    def __init__(self, htmloutput: str) -> None: ...
    @overload
    def __init__(self, htmloutput: str, template_lookup: 'TemplateLookup') -> None: ...

    def prepOutputDirectory(self) -> None:
        """
        Called first.
        """
        ... 

    def writeModuleIndex(self, system:'System') -> None: 
        """
        Called second.
        """
        ...

    def writeIndividualFiles(self, obs:Iterable['Documentable']) -> None:
        """
        Called last.
        """
        ...


class Template(abc.ABC):
    """
    Represents a pydoctor template file. 
    
    It holds references to template information. 

    It's an additionnal level of abstraction to hook to the 
    rendering system, it stores the loader object that 
    is going to be reused for each output file using this template. 

    Use L{Template.fromfile} to create Templates. 

    @see: L{TemplateLookup}
    """

    def __init__(self, path: Path):
        self.path: Path = path
        """
        Template file path
        """
        
        with path.open('r') as f:
            self.text = f.read()
            """
            File text
            """
        

    path: Path
    """
    File path
    """

    text: str
    """
    File text 
    """
    
    TEMPLATE_FILES_SUFFIX = ['.html', '.css', '.js']
    
    @classmethod
    def fromfile(cls, path: Path) -> Optional['Template']:
        """
        Create a concrete template object. 
        Type depends on the file extension. 

        Warns if the template cannot be created.

        @param path: A L{Path} that should point to a HTML, CSS or JS file. 
        @returns: The template object or C{None} if file is invalid. 
        """
        if not path.is_file():
            warnings.warn(f"Cannot create Template: {path.as_posix()} is not a file.")
        elif path.suffix.lower() in cls.TEMPLATE_FILES_SUFFIX:

            if path.suffix.lower() == '.html':
                return _HtmlTemplate(path=path)
            else:
                return _StaticTemplate(path=path)
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

    @abc.abstractproperty
    def version(self) -> int:
        """
        Template version, C{-1} if no version. 

        HTML Templates should have a version identifier as follow::
    
            <meta name="pydoctor-template-version" content="1" />

        This is always C{-1} for CSS and JS templates. 
        """
        raise NotImplementedError()

    @abc.abstractproperty
    def loader(self) -> Optional[ITemplateLoader]:
        """
        Object(s) used to render the final file. 

        For HTML templates, this is a L{ITemplateLoader} or a list of L{ITemplateLoader}.  

        For CSS and JS templates, this is C{None} 
        because there is no rendering to do, it's already the final file.  
        """
        raise NotImplementedError()

class _StaticTemplate(Template):
    """
    Static template: no rendering. 
    For CSS and JS templates. 
    """
    @property
    def version(self) -> int: return -1
    @property
    def loader(self) -> None: return None


@implementer(ITemplateLoader)
class _NullLoader:
    def load(self) -> List[str]:
        return []

class _HtmlTemplate(Template):
    """
    HTML template that works with the Twisted templating system 
    and use L{xml.dom.minidom} to parse the C{pydoctor-template-version} meta tag. 
    """
    def __init__(self, path: Path):
        super().__init__(path)
        self._version: int
        self._loader: ITemplateLoader
        if self.is_empty():
            self._version = -1
            self._loader = _NullLoader()
        else:
            self._version = self._extract_version(parse_dom(self.text), self.name)
            self._loader = XMLString(self.text)
    
    @property
    def version(self) -> int: return self._version
    @property
    def loader(self) -> ITemplateLoader: return self._loader

    @staticmethod
    def _extract_version(dom: minidom.Document, template_name: str) -> int:
        # If no meta pydoctor-template-version tag found, 
        # it's most probably a placeholder template. 
        version = -1
        for meta in dom.getElementsByTagName("meta"):
            if meta.getAttribute("name") != "pydoctor-template-version":
                continue
            if meta.hasAttribute("content"):
                version_str = meta.getAttribute("content")
                if version_str:
                    try:
                        version = int(version_str)
                    except ValueError:
                        warnings.warn(f"Could not read '{template_name}' template version: "
                                "the 'content' attribute must be an integer")
                else:
                    warnings.warn(f"Could not read '{template_name}' template version: "
                        f"the 'content' attribute is empty")
            else:
                warnings.warn(f"Could not read '{template_name}' template version: "
                    f"the 'content' attribute is missing")
        return version

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
        default_template_dir = Path(__file__).parent.parent.joinpath(self._default_template_dir)
        self._templates: Dict[str, Template] = { t.name:t for t in (Template.fromfile(f) for f in 
                default_template_dir.iterdir()) if t }

        self._default_templates = copy.deepcopy(self._templates)


    def add_template(self, template: Template) -> None:
        """
        Add a custom template to the lookup. 

        Compare the passed Template version with default template, 
        issue warnings if template are outdated.

        Warns if the custom template is designed for an older version of pydoctor. 

        @raises UnsupportedTemplateVersion: If the custom template is designed for a newer version of pydoctor. 
        """
        
        try:
            default_version = self._default_templates[template.name].version
        except KeyError:
            warnings.warn(f"Invalid template filename '{template.name}' (will be ignored). Valid filenames are: {list(self._templates)}")
        else:
            template_version = template.version
            if default_version and template_version != -1:
                if template_version < default_version: 
                    warnings.warn(f"Your custom template '{template.name}' is out of date, information might be missing. "
                                   "Latest templates are available to download from our github." )
                elif template_version > default_version:
                    raise UnsupportedTemplateVersion(f"It appears that your custom template '{template.name}' is designed for a newer version of pydoctor."
                                        "Rendering will most probably fail. Upgrade to latest version of pydoctor with 'pip install -U pydoctor'. ")
        finally:
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
__all__ = ["TemplateWriter"] # re-export as pydoctor.templatewriter.TemplateWriter
