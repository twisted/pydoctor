"""Badly named module that contains the driving code for the rendering."""


from typing import Iterable, Type, Optional, List
import os
import shutil
from typing import IO
from pathlib import Path

from pydoctor.templatewriter import IWriter
from pydoctor import model
from pydoctor.templatewriter import DOCTYPE, pages, summary, TemplateLookup
from twisted.web.template import flattenString, Element
from twisted.python.failure import Failure

def flattenToFile(fobj:IO[bytes], page:Element) -> None:
    """
    This method writes a page to a HTML file.
    @raises Exception: If any failure during L{flattenString} call. 
    """
    fobj.write(DOCTYPE)
    err: List[Failure] = []
    flattenString(None, page).addCallback(fobj.write).addErrback(err.append)
    if err:
        raise err.pop().value


class TemplateWriter(IWriter):
    """
    HTML templates writer. 
    """

    @classmethod
    def __subclasshook__(cls, subclass: Type[object]) -> bool:
        for name in dir(cls):
            if not name.startswith('_'):
                if not hasattr(subclass, name):
                    return False
        return True

    def __init__(self, filebase:str, template_lookup:Optional[TemplateLookup] = None):
        """
        @arg filebase: Output directory. 
        @arg template_lookup: Custom L{TemplateLookup} object. 
        """
        self.base: Path = Path(filebase)
        self.written_pages: int = 0
        self.total_pages: int = 0
        self.dry_run: bool = False
        self.template_lookup:TemplateLookup = ( 
            template_lookup if template_lookup else TemplateLookup() )
        """Writer's L{TemplateLookup} object"""

    def prepOutputDirectory(self) -> None:
        """
        Copy static CSS and JS files to build directory and warn when custom templates are outdated. 
        """
        os.makedirs(self.base, exist_ok=True)
        shutil.copy(
            self.template_lookup.get_template('apidocs.css').path,
            self.base.joinpath('apidocs.css'))
        shutil.copy(
            self.template_lookup.get_template('bootstrap.min.css').path,
            self.base.joinpath('bootstrap.min.css'))
        shutil.copy(
            self.template_lookup.get_template('pydoctor.js').path,
            self.base.joinpath('pydoctor.js'))

    def writeIndividualFiles(self, obs:Iterable[model.Documentable]) -> None:
        """
        Iterate trought C{obs} and call L{_writeDocsFor} method for each L{Documentable}. 
        """
        self.dry_run = True
        for ob in obs:
            self._writeDocsFor(ob)
        self.dry_run = False
        for ob in obs:
            self._writeDocsFor(ob)

    def writeModuleIndex(self, system:model.System) -> None:
        import time
        for i, pclass in enumerate(summary.summarypages):
            system.msg('html', 'starting ' + pclass.__name__ + ' ...', nonl=True)
            T = time.time()
            page = pclass(system=system, template_lookup=self.template_lookup)
            # mypy get error: Argument 1 to "joinpath" of "PurePath" has incompatible type "Callable[[BaseElement], str]"; expected "Union[str, _PathLike[str]]"  [arg-type]
            f = self.base.joinpath(pclass.filename).open('wb') # type: ignore
            flattenToFile(f, page)
            f.close()
            system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)

    def _writeDocsFor(self, ob:model.Documentable) -> None:
        if not ob.isVisible:
            return
        if ob.documentation_location is model.DocLocation.OWN_PAGE:
            if self.dry_run:
                self.total_pages += 1
            else:
                path = (self.base / f'{ob.fullName()}.html')
                with path.open('wb') as out:
                    self._writeDocsForOne(ob, out)
        for o in ob.contents.values():
            self._writeDocsFor(o)

    def _writeDocsForOne(self, ob:model.Documentable, fobj:IO[bytes]) -> None:
        if not ob.isVisible:
            return
        # Dynalmically list all known page subclasses
        page_clses = { k:v for k,v in pages.__dict__.items() if 'Page' in k }
        for parent in ob.__class__.__mro__:
            potential_page_cls = parent.__name__ + 'Page'
            if potential_page_cls in page_clses:
                pclass = page_clses[potential_page_cls]
                break
        else:
            pclass = pages.CommonPage
        ob.system.msg('html', str(ob), thresh=1)
        page = pclass(ob=ob, template_lookup=self.template_lookup)
        self.written_pages += 1
        ob.system.progress('html', self.written_pages, self.total_pages, 'pages written')
        flattenToFile(fobj, page)