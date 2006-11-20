from pydoctor.nevowhtml.util import link, templatefile
from pydoctor.nevowhtml import pages, summary

from nevow import flat

import os, sys, shutil

class NevowWriter:
    def __init__(self, filebase):
        self.base = filebase
        self.written_pages = 0

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(templatefile('apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))
        if self.system.options.htmlusesorttable:
            shutil.copyfile(templatefile('sorttable.js'),
                            os.path.join(self.base, 'sorttable.js'))

    def writeIndividualFiles(self, obs, functionpages=False):
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)

    def writeModuleIndex(self, system):
        for pclass in summary.summarypages:
            page = pclass(system)
            f = open(os.path.join(self.base, pclass.filename), 'w')
            f.write(flat.flatten(page))
            f.close()

    def writeDocsFor(self, ob, functionpages):
        isfunc = ob.document_in_parent_page
        if (isfunc and functionpages) or not isfunc:
            f = open(os.path.join(self.base, link(ob)), 'w')
            self.writeDocsForOne(ob, f)
            f.close()
        for o in ob.orderedcontents:
            self.writeDocsFor(o, functionpages)
        print

    def writeDocsForOne(self, ob, fobj):
        # brrrrrrrr!
        d = pages.__dict__
        for c in ob.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in d:
                pclass = d[n]
                break
        else:
            pclass = pages.CommonPage
        page = pclass(ob)
        self.written_pages += 1
        print '\rwritten', self.written_pages, 'pages',
        sys.stdout.flush()
        fobj.write(flat.flatten(page))
