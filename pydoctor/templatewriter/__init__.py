"""Render pydoctor data as HTML."""
from typing import Iterable, Iterator, Optional, Dict, Union, overload, TYPE_CHECKING
if TYPE_CHECKING:
    from typing_extensions import Protocol, runtime_checkable
else:
    Protocol = object
    def runtime_checkable(f):
        return f
import abc
from pathlib import Path, PurePath
from os.path import splitext
import warnings
import sys
from xml.dom import minidom

# Newer APIs from importlib_resources should arrive to stdlib importlib.resources in Python 3.9.
if sys.version_info < (3, 9):
    from importlib_resources.abc import Traversable
else:
    from importlib.abc import Traversable

from twisted.web.iweb import ITemplateLoader
from twisted.web.template import TagLoader, XMLString, Element, tags

from pydoctor.model import System, Documentable

DOCTYPE = b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
          "DTD/xhtml1-strict.dtd">
'''

def parse_xml(text: str) -> minidom.Document:
    """
    Create a L{minidom} representaton of the XML string.
    """
    try:
        return minidom.parseString(text)
    except Exception as e:
        raise ValueError(f"Failed to parse template as XML: {e}") from e
    

class TemplateError(Exception):
    pass

class UnsupportedTemplateVersion(TemplateError):
    """Raised when custom template is designed for a newer version of pydoctor"""

class OverrideTemplateNotAllowed(TemplateError):
    """Raised when a template path overrides a path of a different type (HTML/static/directory)."""

class FailedToCreateTemplate(TemplateError):
    """Raised when a template could not be created because of an error"""

@runtime_checkable
class IWriter(Protocol):
    """
    Interface class for pydoctor output writer.
    """

    @overload
    def __init__(self, build_directory: Path) -> None: ...
    @overload
    def __init__(self, build_directory: Path, template_lookup: 'TemplateLookup') -> None: ...

    def prepOutputDirectory(self) -> None:
        """
        Called first.
        """

    def writeSummaryPages(self, system: System) -> None:
        """
        Called second.
        """

    def writeIndividualFiles(self, obs: Iterable[Documentable]) -> None:
        """
        Called last.
        """

class Template(abc.ABC):
    """
    Represents a pydoctor template file.

    It holds references to template information.

    It's an additionnal level of abstraction to hook to the writer class. 

    Use L{Template.fromfile} or L{Template.fromdir} to create Templates.

    @see: L{TemplateLookup}, L{StaticTemplate} and L{HtmlTemplate}

    @note: Directories are not L{Template}. The L{Template.name} attribute is the 
        relative path to the template file, it may include subdirectories in it! 
        
        Currently, subdirectories should only contains static templates. This is because 
        the subdirectory creation is handled in L{StaticTemplate.write()}.
    """

    def __init__(self, name: str):
        self.name = name
        """Template filename, may include subdirectories."""

    @classmethod
    def fromdir(cls, path: Union[Traversable, Path], subdir: Optional[PurePath] = None) -> Iterator['Template']:
        """
        Scan a directory for templates. 

        @param path: A L{Path} or L{Traversable} object that should point to a template folder.
        @param subdir: The subdirectory inside the template folder structure that holds this template directory. 
        @raises FailedToCreateTemplate: If the path is not a directory or do not exist. 
        """
        if not path.is_dir():
            raise FailedToCreateTemplate(f"Template folder do not exist or is not a directory: {path}")
        subdir = subdir.joinpath(path.name) if subdir else PurePath()
        for entry in path.iterdir():
            if entry.is_dir():
                yield from Template.fromdir(entry, subdir=subdir)
            else:
                template = Template.fromfile(entry, subdir=subdir)
                if template:
                    yield template

    @classmethod
    def fromfile(cls, path: Union[Traversable, Path], subdir: Optional[PurePath] = None) -> Optional['Template']:
        """
        Create a concrete template object.
        Type depends on the file extension.

        @param path: A L{Path} or L{Traversable} object that should point to a template file.
        @param subdir: The subdirectory inside the template folder structure that holds this template file. 
        @returns: The template object or C{None} if a the path entry is not a file.
        @raises FailedToCreateTemplate: If there is an error while creating the template.
        """

        def suffix(name: str) -> str:
            # Workaround to get a filename extension because
            # importlib.abc.Traversable objects do not include .suffix property.
            _, ext = splitext(name)
            return ext
        
        def template_name(filename: str) -> str:
            # The template name is the relative path to the template.
            # Template files in subdirectories will have a name like: 'static/bar.svg'.
            return subdir.joinpath(filename).as_posix() if subdir else filename

        if not path.is_file():
            return None

        file_extension = suffix(path.name).lower()
        
        template: Template

        try:
            # Only try to decode the file text if the file is an HTML template
            if file_extension == '.html':
                try:
                    text = path.read_text(encoding='utf-8')
                except UnicodeDecodeError as e:
                    raise FailedToCreateTemplate("Cannot decode HTML Template"
                                f" as UTF-8: '{path}'. {e}") from e
                else:
                    template = HtmlTemplate(name=template_name(path.name), text=text)
            
            # else, treat the file as binary data.
            else:
                data = path.read_bytes()
                template = StaticTemplate(name=template_name(path.name), data=data)
        
        # Catch io errors only once for the whole block, it's ok to do that since 
        # we're reading only one file per call to fromfile()
        except IOError as e:
            raise FailedToCreateTemplate(f"Cannot read Template: '{path}'."
                        " I/O error: {e}") from e
        
        return template

class StaticTemplate(Template):
    """
    Static template: no rendering, will be copied as is to build directory.

    For CSS and JS templates.
    """
    def __init__(self, name: str, data: bytes) -> None:
        super().__init__(name)
        self.data: bytes = data
        """
        Contents of the template file as L{bytes}.
        """
    
    def write(self, build_directory: Path) -> None:
        """
        Directly write the contents of this static template as is to the build dir.
        """
        outfile = build_directory.joinpath(self.name)
        outfile.parent.mkdir(exist_ok=True, parents=True)
        with outfile.open('wb') as fobjb:
            fobjb.write(self.data)
        
class HtmlTemplate(Template):
    """
    HTML template that works with the Twisted templating system
    and use L{xml.dom.minidom} to parse the C{pydoctor-template-version} meta tag.

    @ivar text:  Contents of the template file as 
        UFT-8 decoded L{str}.

    @ivar version: Template version, C{-1} if no version could be read in the XML file.

        HTML Templates should have a version identifier as follow::

            <meta name="pydoctor-template-version" content="1" />

        The version indentifier should be a integer.
    
    @ivar loader: Object used to render the final HTML file 
        with the Twisted templating system.

        This is a L{ITemplateLoader}.
    """
    def __init__(self, name: str, text: str):
        super().__init__(name=name)
        self.text = text
        if len(self.text.strip()) == 0:
            self._dom: Optional[minidom.Document] = None
            self.version = -1
            self.loader: ITemplateLoader = TagLoader(tags.transparent)
        else:
            self._dom = parse_xml(self.text)
            self.version = self._extract_version(self._dom, self.name)
            self.loader = XMLString(self._dom.toxml())

    @staticmethod
    def _extract_version(dom: minidom.Document, template_name: str) -> int:
        # If no meta pydoctor-template-version tag found,
        # it's most probably a placeholder template.
        version = -1
        for meta in dom.getElementsByTagName("meta"):
            if meta.getAttribute("name") != "pydoctor-template-version":
                continue

            # Remove the meta tag as soon as found
            meta.parentNode.removeChild(meta)

            if not meta.hasAttribute("content"):
                warnings.warn(f"Could not read '{template_name}' template version: "
                    f"the 'content' attribute is missing")
                continue

            version_str = meta.getAttribute("content")

            try:
                version = int(version_str)
            except ValueError:
                warnings.warn(f"Could not read '{template_name}' template version: "
                        "the 'content' attribute must be an integer")
            else:
                break

        return version

class TemplateLookup:
    """
    The L{TemplateLookup} handles the HTML template files locations.
    A little bit like C{mako.lookup.TemplateLookup} but more simple.

    The location of the files depends wether the users set a template directory
    with the option C{--template-dir} and/or with the option C{--theme}, 
    any files in a template directory will be loaded.

    This object allow the customization of any templates. 
    
    For HTML templates, this can lead to warnings
    when upgrading pydoctor, then, please update your template from our repo.

    @note: The HTML templates versions are independent of the pydoctor version
           and are idependent from each other.

    @see: L{Template}, L{StaticTemplate}, L{HtmlTemplate}
    """

    def __init__(self, path: Union[Traversable, Path]) -> None:
        """
        Loads all templates from the given C{path} into the lookup.

        @param path: A L{Path} or L{Traversable} object pointing to a
            directory to load the templates from.
        """
        self._templates: Dict[str, Template] = {}

        self.add_templatedir(path)
        
        self._default_templates = self._templates.copy()
    
    def _add_overriding_html_template(self, template: HtmlTemplate, current_template: HtmlTemplate) -> None:
        default_version = current_template.version
        template_version = template.version
        if default_version != -1 and template_version != -1:
            if template_version < default_version:
                warnings.warn(f"Your custom template '{template.name}' is out of date, "
                                "information might be missing. "
                                "Latest templates are available to download from our github." )
            elif template_version > default_version:
                raise UnsupportedTemplateVersion(f"It appears that your custom template '{template.name}' "
                                    "is designed for a newer version of pydoctor."
                                    "Rendering will most probably fail. Upgrade to latest "
                                    "version of pydoctor with 'pip install -U pydoctor'. ")
        self._templates[template.name] = template

    def _is_template_overriding_subdir(self, template: Template) -> bool:
        # Since we cannot have a file named the same as a directory, 
        # we must reject files that overrides direcotries.
        for t in self.templates:
            if f"{template.name}/" in t.name:
                return True
        return False

    def add_template(self, template: Template) -> None:
        """
        Add a template to the lookup. The custom template override the default. 
        
        If the file doesn't exist in the default template, we assume it is additional data used by the custom template.

        For HTML, compare the passed Template version with default template,
        issue warnings if template are outdated.

        @raises UnsupportedTemplateVersion: If the custom template is designed for a newer version of pydoctor.
        @raises OverrideTemplateNotAllowed: If this template path overrides a path of a different type (HTML/static/directory).
        """

        if self._is_template_overriding_subdir(template):
            raise OverrideTemplateNotAllowed(f"Cannot override a directory with "
                        f"a template. Rename '{template.name}' to something else.")

        current_template = self._templates.get(template.name, None)
        if current_template:
            
            if isinstance(current_template, StaticTemplate):
                if isinstance(template, StaticTemplate):
                    self._templates[template.name] = template
                else:
                    raise OverrideTemplateNotAllowed(f"Cannot override a static template with "
                        f"a HTML template. Rename '{template.name}' to something else.")
                        # we can assume the template is HTML since there is only 
                        # two types of concrete templates
            
            elif isinstance(current_template, HtmlTemplate):
                if isinstance(template, HtmlTemplate):
                    self._add_overriding_html_template(template, current_template)
                else:
                    raise OverrideTemplateNotAllowed(f"Cannot override an HTML template with "
                        f"a static template. Rename '{template.name}' to something else.")
        else:
            self._templates[template.name] = template

    def add_templatedir(self, path: Union[Path, Traversable]) -> None:
        """
        Scan a directory and add all templates in the given directory to the lookup.
        """
        for template in Template.fromdir(path):
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

    def get_loader(self, filename: str) -> ITemplateLoader:
        """
        Lookup a HTML template loader based on its filename.

        @raises ValueError: If the template is not an HTML file.
        """ 
        template = self.get_template(filename)
        if not isinstance(template, HtmlTemplate):
            raise ValueError(f"Failed to get loader of template '{filename}': Not an HTML file.")
        return template.loader

    @property
    def templates(self) -> Iterable[Template]:
        """
        All templates that can be looked up.
        For each name, the custom template will be included if it exists,
        otherwise the default template.
        """
        return self._templates.values()

class TemplateElement(Element, abc.ABC):
    """
    Renderable element based on a template file.
    """

    filename: str = NotImplemented
    """
    Associated template filename.
    """

    @classmethod
    def lookup_loader(cls, template_lookup: TemplateLookup) -> ITemplateLoader:
        """
        Lookup the element L{ITemplateLoader} with the C{TemplateLookup}.
        """
        return template_lookup.get_loader(cls.filename)

from pydoctor.templatewriter.writer import TemplateWriter
__all__ = ["TemplateWriter"] # re-export as pydoctor.templatewriter.TemplateWriter
