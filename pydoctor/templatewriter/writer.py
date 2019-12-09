"""Badly named module that contains the driving code for the rendering."""

from __future__ import print_function

import os
import shutil

from pydoctor import model
from pydoctor.templatewriter import DOCTYPE, pages, summary
from pydoctor.templatewriter.util import link, templatefile
from twisted.web.template import flattenString


def flattenToFile(fobj, page):
    fobj.write(DOCTYPE)
    err = []
    def e(r):
        err.append(r.value)
    flattenString(None, page).addCallback(fobj.write).addErrback(e)
    if err:
        raise err[0]


class TemplateWriter:
    def __init__(self, filebase):
        self.base = filebase
        self.written_pages = 0
        self.total_pages = 0
        self.dry_run = False

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(templatefile('apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))
        shutil.copyfile(templatefile('bootstrap.min.css'),
                        os.path.join(self.base, 'bootstrap.min.css'))
        shutil.copyfile(templatefile('pydoctor.js'),
                        os.path.join(self.base, 'pydoctor.js'))

    def writeIndividualFiles(self, obs, functionpages=False):
        self.dry_run = True
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)
        self.dry_run = False
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)

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

    def writeDocsFor(self, ob, functionpages):
        if not ob.isVisible:
            return
        isfunc = ob.documentation_location is model.DocLocation.PARENT_PAGE
        if (isfunc and functionpages) or not isfunc:
            if self.dry_run:
                self.total_pages += 1
            else:
                f = open(os.path.join(self.base, link(ob)), 'wb')
                self.writeDocsForOne(ob, f)
                f.close()
        for o in ob.orderedcontents:
            self.writeDocsFor(o, functionpages)

    def writeDocsForOne(self, ob, fobj):
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
        self.system.msg('html', str(ob), thresh=1)
        page = pclass(ob)
        self.written_pages += 1
        self.system.progress('html', self.written_pages, self.total_pages, 'pages written')
        flattenToFile(fobj, page)
