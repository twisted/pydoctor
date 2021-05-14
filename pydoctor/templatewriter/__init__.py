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
    import importlib_resources
    from importlib_resources.abc import Traversable
else:
    import importlib.resources as importlib_resources
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

def scandir(path: Union[Traversable, Path]) -> Iterator['Template']:
    """
    Scan a directory for templates. 
    """
    for entry in path.iterdir():
        template = Template.fromfile(entry)
        if template:
            yield template

class TemplateError(Exception):
    pass

class UnsupportedTemplateVersion(TemplateError):
    """Raised when custom template is designed for a newer version of pydoctor"""

class OverrideTemplateNotAllowed(TemplateError):
    """Raised when a template is trying to be overriden because of a bogus path entry"""

class FailedToCreateTemplate(TemplateError):
    """Raised when a template could not be created because of an error"""

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

    It's an additionnal level of abstraction to hook to the
    rendering system, it stores the loader object that
    is going to be reused for each output file using this template.

    Use L{Template.fromfile} to create Templates.

    @see: L{TemplateLookup}
    """

    def __init__(self, name: str, data: Union[str, bytes]):
        self.name = name
        """Template filename"""

        self.data = data
        """
        Template data: contents of the template file as 
        UFT-8 decoded L{str} or directly L{bytes} for static templates.
        """

    TEMPLATE_FILES_SUFFIX = ('.html', '.css', '.js', # Web
    '.svg', '.bmp', '.gif', '.ico', '.jpeg', '.jpg', '.png', '.tif', '.tiff', # Images
    '.fnt', '.fon', '.otf','.ttf', '.woff', '.woff2', # Font Formats
    '.xml', '.json', # Data
    )

    @classmethod
    def fromfile(cls, path: Union[Traversable, Path]) -> Optional['Template']:
        """
        Create a concrete template object.
        Type depends on the file extension.

        Warns if the template cannot be created.

        @param path: A L{Path} or L{Traversable} object that should point to a template file or folder. 
        @returns: The template object or C{None} if file extension is invalid.
        @raises FailedToCreateTemplate: If there is an error while creating the template.
        """

        def suffix(name: str) -> str:
            # Workaround to get a filename extension because
            # importlib.abc.Traversable objects do not include .suffix property.
            _, ext = splitext(name)
            return ext

        if path.is_dir():
            return _TemplateSubFolder(name=path.name, lookup=TemplateLookup(path))
        if path.is_file():
            file_extension = suffix(path.name).lower()

            # Remove this 'if/else' to copy ANY kind of files to build directory.
            if file_extension in cls.TEMPLATE_FILES_SUFFIX:
                try:
                    if file_extension == '.html':
                        try:
                            with path.open('r', encoding='utf-8') as fobj:
                                text = fobj.read()
                        except UnicodeDecodeError as e:
                            raise FailedToCreateTemplate(f"Cannot decode HTML Template as UTF-8: '{path}'. {e}") from e
                        else:
                            return _HtmlTemplate(name=path.name, text=text)
                    else:
                        # treat the file as binary data.
                        with path.open('rb') as fobjb:
                            _bytes = fobjb.read()
                        return _StaticTemplate(name=path.name, data=_bytes)
                except IOError as e:
                    raise FailedToCreateTemplate(f"Cannot read Template: '{path}'. I/O error: {e}") from e

            else:
                warnings.warn(f"Cannot create Template: {path} is not recognized as template file. "
                    f"Template files must have one of the following extensions: {', '.join(cls.TEMPLATE_FILES_SUFFIX)}")
        
        return None

    def is_empty(self) -> bool:
        """
        Does this template contain nothing except whitespace?
        Empty templates will not be rendered.
        """
        if isinstance(self.data, str):
            return len(self.data.strip()) == 0
        else:
            return len(self.data) == 0

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
        Object used to render the final file.

        For HTML templates, this is a L{ITemplateLoader}.

        For CSS and JS templates, this is C{None}
        because there is no rendering to do, it's already the final file.
        """
        raise NotImplementedError()

class _StaticTemplate(Template):
    """
    Static template: no rendering, will be copied as is to build directory.

    For CSS and JS templates.
    """
    data: bytes

    @property
    def version(self) -> int:
        return -1
    @property
    def loader(self) -> None:
        return None
    
    def write(self, output_dir: Path, subfolder: Optional[PurePath] = None) -> PurePath:
        """
        Directly write the contents of this static template as is to the output dir.

        @returns: The relative path of the file that has been wrote.
        """
        _subfolder_path = subfolder if subfolder else PurePath()
        _template_path = _subfolder_path.joinpath(self.name)
        outfile = output_dir.joinpath(_template_path)
        self._write(outfile)
        return _template_path
    
    def _write(self, path: Path) -> None:
        with path.open('wb') as fobjb:
            fobjb.write(self.data)

class _TemplateSubFolder(_StaticTemplate):
    """
    Special template to hold a subfolder contents. 

    Currently used for C{fonts}.
    """
    def __init__(self, name: str, lookup: 'TemplateLookup'):
        super().__init__(name, '')

        self.lookup: 'TemplateLookup' = lookup
        """
        The lookup instance that contains the subfolder templates. 
        """

    def write(self, output_dir: Path, subfolder: Optional[PurePath] = None) -> PurePath:
        """
        Create the subfolder and reccursively write it's content to the output directory.
        """
        subfolder = super().write(output_dir, subfolder)
        for template in self.lookup.templates:
            if isinstance(template, _StaticTemplate):
                template.write(output_dir, subfolder)
        return subfolder

    def _write(self, path: Path) -> None:
        path.mkdir(exist_ok=True, parents=True)
        
class _HtmlTemplate(Template):
    """
    HTML template that works with the Twisted templating system
    and use L{xml.dom.minidom} to parse the C{pydoctor-template-version} meta tag.
    """
    data: str

    def __init__(self, name: str, text: str):
        super().__init__(name=name, data=text)
        if self.is_empty():
            self._dom: Optional[minidom.Document] = None
            self._version = -1
            self._loader: ITemplateLoader = TagLoader(tags.transparent)
        else:
            self._dom = parse_xml(self.data)
            self._version = self._extract_version(self._dom, self.name)
            self._loader = XMLString(self._dom.toxml())

    @property
    def version(self) -> int:
        return self._version
    @property
    def loader(self) -> ITemplateLoader:
        return self._loader

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
    with the option C{--template-dir}, custom files with matching names will be
    loaded if present.

    This object allow the customization of any templates, this can lead to warnings
    when upgrading pydoctor, then, please update your template.

    @note: The HTML templates versions are independent of the pydoctor version
           and are idependent from each other.

    @see: L{Template}
    """

    def __init__(self, template_dir: Optional[Union[Traversable, Path]] = None, theme: str = 'classic') -> None:
        """
        Init L{TemplateLookup} with templates in C{pydoctor/templates}.
        This loads all templates into the lookup C{_templates} dict.

        @param template_dir: A custom L{Path} or L{Traversable} object to load the templates from.
        @param theme: Load the theme if C{template_dir} is not defined.
        """
        self._templates: Dict[str, Template] = {}

        if not template_dir:
            theme_path = importlib_resources.files('pydoctor.themes') / theme
            self._load_dir(theme_path)
        else:
            self._load_dir(template_dir)
        
        self._default_templates = self._templates.copy()

    def _load_dir(self, templatedir: Union[Traversable, Path], add: bool = False) -> None:
        for template in scandir(templatedir):
            if add:
                self.add_template(template)
            else:
                self._load_template(template)
    
    def _load_lookup(self, lookup: 'TemplateLookup') -> None:
        # Currently, _load_lookup is only called when adding a subfolder to the TemplateLookup entries,
        # so we call add_template() no matter what to check for version compat.
        for template in lookup.templates:
            self.add_template(template)
    
    def _load_template(self, template: Template) -> None:
        """
        Load the template inside the lookup, handle the subfolders etc.     

        @raises OverrideTemplateNotAllowed: If a path in this template overrides a path of a different type (HTML/static/subdir).      
        """
        current_template = self._templates.get(template.name, None)
        if current_template:
            if isinstance(current_template, _TemplateSubFolder):
                if isinstance(template, _TemplateSubFolder):
                    current_template.lookup._load_lookup(template.lookup)
                else:
                    raise OverrideTemplateNotAllowed(f"Cannot override _TemplateSubFolder with a {template.__class__.__name__}."
                        f"Rename '{template.name}' to something else. ")
            
            elif isinstance(current_template, _StaticTemplate):
                if isinstance(template, _StaticTemplate):
                    self._templates[template.name] = template
                else:
                    raise OverrideTemplateNotAllowed(f"Cannot override _StaticTemplate with a {template.__class__.__name__}."
                        f"Rename '{template.name}' to something else. ")
            
            elif isinstance(current_template, _HtmlTemplate):
                if isinstance(template, _HtmlTemplate):
                    self._templates[template.name] = template
                else:
                    raise OverrideTemplateNotAllowed(f"Cannot override _HtmlTemplate with a  {template.__class__.__name__}."
                        f"Rename '{template.name}' to something else. ")
        else:
            self._templates[template.name] = template

    def add_template(self, template: Template) -> None:
        """
        Add a custom template to the lookup. The custom template override the default.

        Compare the passed Template version with default template,
        issue warnings if template are outdated.

        @raises UnsupportedTemplateVersion: If the custom template is designed for a newer version of pydoctor.
        @raises OverrideTemplateNotAllowed: If a path in this template overrides a path of a different type (HTML/static/subdir).
        """

        try:
            default_version = self._default_templates[template.name].version
        except KeyError:
            # Passing the file as is
            self._load_template(template)
        else:
            template_version = template.version
            if default_version != -1 and template_version != -1 :
                if template_version < default_version:
                    warnings.warn(f"Your custom template '{template.name}' is out of date, "
                                    "information might be missing. "
                                   "Latest templates are available to download from our github." )
                elif template_version > default_version:
                    raise UnsupportedTemplateVersion(f"It appears that your custom template '{template.name}' "
                                        "is designed for a newer version of pydoctor."
                                        "Rendering will most probably fail. Upgrade to latest "
                                        "version of pydoctor with 'pip install -U pydoctor'. ")
            self._load_template(template)

    def add_templatedir(self, dir: Path) -> None:
        """
        Scan a directory and add all templates in the given directory to the lookup.
        """
        self._load_dir(dir, add=True)

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

        @raises ValueError: If the template loader is C{None}.
        """
        template = self.get_template(filename)
        if template.loader is None:
            raise ValueError(f"Failed to get loader of template '{filename}' (template.loader is None)")
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
