"""Miscellaneous utilities."""

from typing import Optional, List
import os

from pydoctor import model
from twisted.python.filepath import FilePath
from twisted.web.template import Tag, tags
import warnings

def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

class TemplateFileLookup:
    """
    The `TemplateFileManager` handles the HTML template files locations. 
    A little bit like `mako.lookup.TemplateLookup` but more simple. 

    The location of the files depends wether the users set a template directory 
    with the option `--template-dir`, custom files with matching names will be 
    loaded if present. 

    Warning: While this object allow the customization of any templates, this can lead to errors 
    when upgrading pydoctor. 

    Only customization of "footer.html", "header.html" and "pageHeader.html" is currently supported.

    """
    def __init__(self):
        self.templatedirs:List[FilePath] = []
        # Add default template dir
        self._init_default_template_dir()

    def _init_default_template_dir(self) -> None:
        abspath = os.path.abspath(__file__)
        pydoctordir = os.path.dirname(os.path.dirname(abspath))
        self.templatedirs.append(FilePath(os.path.join(pydoctordir, 'templates')))

    def add_templatedir(self, folderpath:str) -> None:
        """
        Add a custom template directory. 
        """
        path = FilePath(folderpath)
        if not path.isdir():
            raise FileNotFoundError(f"Cannot find the template directory: '{path}'")
        self.templatedirs.append(path)

    def clear_templates(self) -> None:
        self.templatedirs = []
        self._init_default_template_dir()

    def get_templatefilepath(self, filename:str) -> FilePath:
        """
        Lookup a template file path base on the file name. 
        Load the custom template if provided, else load the default template.

        @param filename: File name, (ie 'index.html')
        """
        for template in reversed(self.templatedirs):
            p_templatefile = FilePath(os.path.join(template.path, filename))
            if p_templatefile.isfile():
                return p_templatefile
        raise FileNotFoundError(f"Cannot find template file: '{filename}' in template directories: {self.templatedirs}")

# Deprecated
def templatefile(filename:str) -> str:
    warnings.warn(  "pydoctor.templatewriter.templatefile() and pydoctor.templatewriter.templatefilepath() " 
                    "are deprecated since pydoctor 21.0. Please use templating system. ")
    return TemplateFileLookup().get_templatefile(filename)
# Deprecated
def templatefilepath(filename:str) -> FilePath:
    return FilePath(templatefile(filename))

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
