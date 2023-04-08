"""Badly named module that contains the driving code for the rendering."""


import itertools
from pathlib import Path
from typing import IO, Iterable, Type, TYPE_CHECKING

from pydoctor import model
from pydoctor.extensions import zopeinterface
from pydoctor.templatewriter import (
    DOCTYPE, pages, summary, search, TemplateLookup, IWriter, StaticTemplate
)

from twisted.python.failure import Failure
from twisted.web.template import flattenString

if TYPE_CHECKING:
    from twisted.web.template import Flattenable


def flattenToFile(fobj: IO[bytes], elem: "Flattenable") -> None:
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
        for pclass in itertools.chain(summary.summaryPages(system), search.searchpages):
            system.msg('html', 'starting ' + pclass.__name__ + ' ...', nonl=True)
            T = time.time()
            page = pclass(system=system, template_lookup=self.template_lookup)
            with self.build_directory.joinpath(pclass.filename).open('wb') as fobj:
                flattenToFile(fobj, page)
            system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)
        
        # Generate the searchindex.json file
        system.msg('html', 'starting lunr search index ...', nonl=True)
        T = time.time()
        search.write_lunr_index(self.build_directory, system=system)
        system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)

        if len(system.root_names) == 1:
            # If there is just a single root module it is written to index.html to produce nicer URLs.
            # To not break old links we also create a symlink from the full module name to the index.html
            # file. This is also good for consistency: every module is accessible by <full module name>.html
            root_module_path = (self.build_directory / (list(system.root_names)[0] + '.html'))
            try:
                root_module_path.unlink()
                # not using missing_ok=True because that was only added in Python 3.8 and we still support Python 3.6
            except FileNotFoundError:
                pass
            root_module_path.symlink_to('index.html')

    def _writeDocsFor(self, ob: model.Documentable) -> None:
        if not ob.isVisible:
            return
        if ob.documentation_location is model.DocLocation.OWN_PAGE:
            if self.dry_run:
                self.total_pages += 1
            else:
                with self.build_directory.joinpath(ob.url).open('wb') as fobj:
                    self._writeDocsForOne(ob, fobj)
        for o in ob.contents.values():
            self._writeDocsFor(o)

    def _writeDocsForOne(self, ob: model.Documentable, fobj: IO[bytes]) -> None:
        if not ob.isVisible:
            return
        pclass: Type[pages.CommonPage] = pages.CommonPage
        class_name = ob.__class__.__name__
        
        # Special case the zope interface custom renderer. 
        # TODO: Find a better way of handling renderer customizations and get rid of ZopeInterfaceClassPage completely.
        if class_name == 'Class' and isinstance(ob, zopeinterface.ZopeInterfaceClass):
            class_name = 'ZopeInterfaceClass'
        
        try:
            # This implementation relies on 'pages.commonpages' dict that ties
            # documentable class name (i.e. 'Class') with the
            # page class used for rendering: pages.ClassPage
            pclass = pages.commonpages[class_name]
        except KeyError:
            ob.system.msg(section="html", 
                # This is typically only reached in tests, when rendering Functions or Attributes with this method.
                msg=f"Could not find page class suitable to render object type: {class_name!r}, using CommonPage.", 
                once=True, thresh=-2)
        
        ob.system.msg('html', str(ob), thresh=1)
        page = pclass(ob=ob, template_lookup=self.template_lookup)
        self.written_pages += 1
        ob.system.progress('html', self.written_pages, self.total_pages, 'pages written')
        flattenToFile(fobj, page)
