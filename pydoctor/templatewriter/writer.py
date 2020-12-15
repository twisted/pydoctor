"""Badly named module that contains the driving code for the rendering."""

from abc import ABC
from typing import Type
import os
import shutil

from pydoctor import model
from pydoctor.templatewriter import DOCTYPE, pages, summary
from pydoctor.templatewriter.util import templatefile
from twisted.python.filepath import FilePath
from twisted.web.template import flattenString


def flattenToFile(fobj, page):
    fobj.write(DOCTYPE)
    err = []
    def e(r):
        err.append(r.value)
    flattenString(None, page).addCallback(fobj.write).addErrback(e)
    if err:
        raise err[0]


class TemplateWriter(ABC):
    @classmethod
    def __subclasshook__(cls, subclass: Type[object]) -> bool:
        for name in dir(cls):
            if not name.startswith('_'):
                if not hasattr(subclass, name):
                    return False
        return True

    def __init__(self, filebase):
        self.base = filebase
        self.written_pages = 0
        self.total_pages = 0
        self.dry_run = False

    def prepOutputDirectory(self):
        os.makedirs(self.base, exist_ok=True)
        shutil.copyfile(templatefile('apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))
        shutil.copyfile(templatefile('bootstrap.min.css'),
                        os.path.join(self.base, 'bootstrap.min.css'))
        shutil.copyfile(templatefile('pydoctor.js'),
                        os.path.join(self.base, 'pydoctor.js'))

    def writeIndividualFiles(self, obs):
        self.dry_run = True
        for ob in obs:
            self._writeDocsFor(ob)
        self.dry_run = False
        for ob in obs:
            self._writeDocsFor(ob)

    def writeModuleIndex(self, system):
        import time
        for i, pclass in enumerate(summary.summarypages):
            system.msg('html', 'starting ' + pclass.__name__ + ' ...', nonl=True)
            T = time.time()
            page = pclass(system)
            f = open(os.path.join(self.base, pclass.filename), 'wb')
            flattenToFile(f, page)
            f.close()
            system.msg('html', "took %fs"%(time.time() - T), wantsnl=False)

    def _writeDocsFor(self, ob):
        if not ob.isVisible:
            return
        if ob.documentation_location is model.DocLocation.OWN_PAGE:
            if self.dry_run:
                self.total_pages += 1
            else:
                path = FilePath(self.base).child(f'{ob.fullName()}.html')
                with path.open('wb') as out:
                    self._writeDocsForOne(ob, out)
        for o in ob.contents.values():
            self._writeDocsFor(o)

    def _writeDocsForOne(self, ob, fobj):
        if not ob.isVisible:
            return
        # brrrrrrr!
        d = pages.__dict__
        for c in ob.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in d:
                pclass = d[n]
                break
        else:
            pclass = pages.CommonPage
        ob.system.msg('html', str(ob), thresh=1)
        page = pclass(ob)
        self.written_pages += 1
        ob.system.progress('html', self.written_pages, self.total_pages, 'pages written')
        flattenToFile(fobj, page)
