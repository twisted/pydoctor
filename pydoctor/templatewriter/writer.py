"""Badly named module that contains the driving code for the rendering."""


from pathlib import Path
from typing import IO, Iterable, Type

from pydoctor import model
from pydoctor.templatewriter import (
    DOCTYPE, pages, summary, TemplateLookup, IWriter, StaticTemplate
)

from twisted.python.failure import Failure
from twisted.web.template import flattenString, Element


def flattenToFile(fobj: IO[bytes], elem: Element) -> None:
    """
    This method writes a page to a HTML file.
    @raises Exception: If the L{twisted.web.template.flatten} call fails.
    """
    fobj.write(DOCTYPE)
    err = None
    def e(r: Failure) -> None:
        nonlocal err
        err = r.value
    flattenString(None, elem).addCallback(fobj.write).addErrback(e)
    if err:
        raise err


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

    def __init__(self, build_directory: Path, template_lookup: TemplateLookup):
        """
        @arg build_directory: Build directory.
        @arg template_lookup: L{TemplateLookup} object.
        """
        self.build_directory = build_directory
        """Build directory"""

        self.template_lookup: TemplateLookup = template_lookup
        """Writer's L{TemplateLookup} object"""

        self.written_pages: int = 0
        self.total_pages: int = 0
        self.dry_run: bool = False
        

    def prepOutputDirectory(self) -> None:
        """
        Write static CSS and JS files to build directory.
        """
        self.build_directory.mkdir(exist_ok=True, parents=True)
        for template in self.template_lookup.templates:
            if isinstance(template, StaticTemplate):
                template.write(self.build_directory)

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
            with self.build_directory.joinpath(pclass.filename).open('wb') as fobj:
                flattenToFile(fobj, page)
            system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)

    def _writeDocsFor(self, ob: model.Documentable) -> None:
        if not ob.isVisible:
            return
        if ob.documentation_location is model.DocLocation.OWN_PAGE:
            if self.dry_run:
                self.total_pages += 1
            else:
                with self.build_directory.joinpath(f'{ob.fullName()}.html').open('wb') as fobj:
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
