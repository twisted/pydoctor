"""Miscellaneous utilities."""

from typing import Optional, List, Union, Tuple
import os
import attr
from bs4 import BeautifulSoup

from pydoctor import model
from twisted.python.filepath import FilePath
from twisted.web.template import Tag, tags
import warnings

def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

@attr.s
class Template:
    """
    """

@attr.s
class HtmlTemplate:
    """
    """
    pass

@attr.s
class RstTemplate:
    """
    """
    pass

class TemplateLookup:
    """
    The L{TemplateLookup} handles the HTML template files locations. 
    A little bit like `mako.lookup.TemplateLookup` but more simple. 

    The location of the files depends wether the users set a template directory 
    with the option C{--template-dir}, custom files with matching names will be 
    loaded if present. 

    This object allow the customization of any templates, this can lead to warnings when upgrading pydoctor, then, please update your template.

    @Note: The HTML templates versions are independent of the pydoctor version and are idependent from each other. 
           They are all initialized to '1.0'.
           Please upgrade the template version between releases if the template was changed. 

    """
    _default_dir = 'templates'

    def __init__(self):
        self.templatedirs:List[FilePath] = []
        # Add default template dir
        self.templatedirs.append(
            self._get_default_template_dir(self._default_dir))

    def _get_default_template_dir(self, dirname) -> FilePath:
        abspath = os.path.abspath(__file__)
        pydoctordir = os.path.dirname(os.path.dirname(abspath))
        return FilePath(os.path.join(pydoctordir, dirname))

    def add_templatedir(self, folderpath:str) -> None:
        """
        Add a custom template directory. 
        """
        path = FilePath(folderpath)
        if not path.isdir():
            raise FileNotFoundError(f"Cannot find the template directory: '{path}'")
        self.templatedirs.append(path)

    def get_templatefilepath(self, filename:str) -> FilePath:
        """
        Lookup a template file path base on the file name. 
        Load the custom template if provided, else load the default template.

        @param filename: File name, (ie 'index.html')
        """
        for template in reversed(self.templatedirs):
            p_templatefile = template.child(filename)
            if p_templatefile.isfile():
                return p_templatefile # type: ignore
        raise FileNotFoundError(f"Cannot find template file: '{filename}' in template directories: {self.templatedirs}")
    
    def getall_templates_filenames(self) -> List[str]:
        """
        Get all templates FilePath. 
        """
        templates : List[FilePath] = []
        for template in reversed(self.templatedirs):
            for potential_template in template.children():
                if potential_template.basename() not in [t.basename() for t in templates]:
                    templates.append(potential_template)
        return ([t.basename() for t in templates])

    def get_template_version(self, filename: str) -> Union[None, Tuple[int, int]]: 
        """
        All template files should have a meta tag indicating the version::

            <meta name="template" content="pydoctor-default" major_version="1" minor_version="0" />

        @arg filename: Template file name
        @return The template version as tuple[major, minor, micro] or None
        """
        soup = BeautifulSoup(self.get_templatefilepath(filename).open('r').read(), 'html.parser')
        res = soup.find_all("meta", attrs=dict(name="template"))
        if res :
            try:
                return (int(res[0]['major_version']), int(res[0]['minor_version']))
            except (ValueError, KeyError):
                return None
        else:
            return None


# Deprecated
def templatefile(filename:str) -> Union[bytes, str]:
    return templatefilepath(filename).path
# Deprecated
def templatefilepath(filename:str) -> FilePath:
    warnings.warn(  "pydoctor.templatewriter.templatefile() and pydoctor.templatewriter.templatefilepath() " 
                    "are deprecated since pydoctor 21. Please use the templating system. ")
    return TemplateLookup().get_templatefilepath(filename)

def taglink(o: model.Documentable, label: Optional[str] = None) -> Tag:
    if not o.isVisible:
        o.system.msg("html", "don't link to %s"%o.fullName())
    if label is None:
        label = o.fullName()
    # Create a link to the object, with a "data-type" attribute which says what
    # kind of object it is (class, etc). This helps doc2dash figure out what it
    # is.
    ret: Tag = tags.a(href=o.url, class_="code", **{"data-type": o.kind})(label)
    return ret
