"""Badly named module that contains the driving code for the rendering."""


from typing import Iterable, Type, Optional, List
import os
from typing import IO
from pathlib import Path, PurePath

from pydoctor.templatewriter import IWriter, _StaticTemplate, _TemplateSubFolder, Template
from pydoctor import model
from pydoctor.templatewriter import DOCTYPE, pages, summary, search, TemplateLookup

from twisted.web.template import Element, flatten
from twisted.python.failure import Failure


def flattenToFile(fobj: IO[bytes], page: Element) -> None:
    """
    This method writes a page to a HTML file.
    @raises Exception: If the L{flatten} call fails.
    """
    fobj.write(DOCTYPE)
    err: List[Failure] = []
    d = flatten(None, page, fobj.write).addErrback(err.append)
    assert d.called
    if err:
        raise err[0]


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

    def __init__(self, output_dir: str, template_lookup: Optional[TemplateLookup] = None):
        """
        @arg output_dir: Output directory.
        @arg template_lookup: Custom L{TemplateLookup} object.
        """
        self.output_dir: Path = Path(output_dir)
        self.written_pages: int = 0
        self.total_pages: int = 0
        self.dry_run: bool = False
        self.template_lookup:TemplateLookup = (
            template_lookup if template_lookup else TemplateLookup() )
        """Writer's L{TemplateLookup} object"""

    def prepOutputDirectory(self) -> None:
        """
        Write static CSS and JS files to build directory.
        """
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self._writeStaticTemplates(self.template_lookup.templates)
    
    def _writeStaticTemplates(self, templates: Iterable[Template], subfolder: Optional[PurePath] = None) -> None:
        """
        Write all L{_StaticTemplate} to output directory, inspect L{_TemplateSubFolder} 
        and reccursively write the static templates in subfolders.
        """
        _template_rel_path_t = subfolder if subfolder else PurePath()
        
        for template in templates:
            _template_rel_path = _template_rel_path_t.joinpath(template.name)
            outfile = self.output_dir.joinpath(_template_rel_path)
            if isinstance(template, _TemplateSubFolder):
                outfile.mkdir(exist_ok=True, parents=True)
                self._writeStaticTemplates(template.lookup.templates, subfolder=_template_rel_path)
                
            elif isinstance(template, _StaticTemplate):
                with outfile.open('w', encoding='utf-8') as fobj:
                    fobj.write(template.text)

    def writeIndividualFiles(self, obs: Iterable[model.Documentable]) -> None:
        """
        Iterate through C{obs} and call L{_writeDocsFor} method for each L{Documentable}.
        """
        self.dry_run = True
        for ob in obs:
            self._writeDocsFor(ob)
        self.dry_run = False
        for ob in obs:
            self._writeDocsFor(ob)

    def writeSummaryPages(self, system: model.System) -> None:
        import time
        for pclass in summary.summarypages + search.searchpages:
            system.msg('html', 'starting ' + pclass.__name__ + ' ...', nonl=True)
            T = time.time()
            page = pclass(system=system, template_lookup=self.template_lookup)
            with self.output_dir.joinpath(pclass.filename).open('wb') as fobj:
                flattenToFile(fobj, page)
            system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)

        # Search stuff.
        system.msg('html', 'starting search index ...', nonl=True)
        T = time.time()
        search.write_lunr_index(self.output_dir, system)
        system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)

    def _writeDocsFor(self, ob: model.Documentable) -> None:
        if not ob.isVisible:
            return
        if ob.documentation_location is model.DocLocation.OWN_PAGE:
            if self.dry_run:
                self.total_pages += 1
            else:
                with self.output_dir.joinpath(f'{ob.fullName()}.html').open('wb') as fobj:
                    self._writeDocsForOne(ob, fobj)
        for o in ob.contents.values():
            self._writeDocsFor(o)

    def _writeDocsForOne(self, ob: model.Documentable, fobj: IO[bytes]) -> None:
        if not ob.isVisible:
            return
        pclass: Type[pages.CommonPage] = pages.CommonPage
        for parent in ob.__class__.__mro__:
            # This implementation relies on 'pages.commonpages' dict that ties
            # documentable class name (i.e. 'Class') with the
            # page class used for rendering: pages.ClassPage
            try:
                pclass = pages.commonpages[parent.__name__]
            except KeyError:
                continue
            else:
                break
        ob.system.msg('html', str(ob), thresh=1)
        page = pclass(ob=ob, template_lookup=self.template_lookup)
        self.written_pages += 1
        ob.system.progress('html', self.written_pages, self.total_pages, 'pages written')
        flattenToFile(fobj, page)
