"""Miscellaneous utilities."""

from typing import Optional
import os

from pydoctor import model
from twisted.python.filepath import FilePath
from twisted.web.template import Tag, tags


def srclink(o: model.Documentable) -> Optional[str]:
    return o.sourceHref

class TemplateFileManager:
    """
    The `TemplateFileManager` handles the HTML template files locations. 

    The location of the files depends wether the users set a template directory 
    with the option `--template-dir`, custom files with matching names will be 
    loaded if present. 

    Warning: While this object allow the customization of any templates, this can lead to errors. 
    Only customization of "footer.html", "header.html" and "pageHeader.html" is currently supported

    """
    _instance = None
    def __new__(cls):
        if cls._instance == None:
            cls._instance = super(TemplateFileManager, cls).__new__(cls)
            # Put any initialization here.
            cls.templatedir: Optional[str] = None
        return cls._instance

    def set_templatedir(self, folderpath:str) -> None:
        """
        Set the custom template directory. 
        """
        if not FilePath(folderpath).exists():
            raise FileNotFoundError(f"Cannot find the template directory '{folderpath}'")
        self.templatedir = os.path.abspath(folderpath)

    def reset_templatedir(self) -> None:
        self.templatedir = None

    def get_templatefile(self, filename:str) -> str:
        """
        Get a template file path base on it's name.
        Use the custom template if provided, else load the default template.

        @param filename: File name, (ie 'index.html')
        """
        # Return custom template
        if self.templatedir:
            p_templatefile = os.path.join(self.templatedir, filename)
            if FilePath(p_templatefile).isfile():
                return p_templatefile
        # Return original template
        abspath = os.path.abspath(__file__)
        pydoctordir = os.path.dirname(os.path.dirname(abspath))
        return os.path.join(pydoctordir, 'templates', filename)

def templatefile(filename:str) -> str:
    return TemplateFileManager().get_templatefile(filename)

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
