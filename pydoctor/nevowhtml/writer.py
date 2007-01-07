from pydoctor.nevowhtml.util import link, templatefile
from pydoctor.nevowhtml import pages, summary

from nevow import flat

import os, sys, shutil

class NevowWriter:
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
        if self.system.options.htmlusesorttable:
            shutil.copyfile(templatefile('sorttable.js'),
                            os.path.join(self.base, 'sorttable.js'))
        if self.system.options.htmlusesplitlinks or self.system.options.htmlshortenlists:
            shutil.copyfile(templatefile('pydoctor.js'),
                            os.path.join(self.base, 'pydoctor.js'))

    def writeIndividualFiles(self, obs, functionpages=False):
        self.dry_run = True
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)
        self.dry_run = False
        for ob in obs:
            self.writeDocsFor(ob, functionpages=functionpages)
        print

    def writeModuleIndex(self, system):
        import time
        for i, pclass in enumerate(summary.summarypages):
            print 'starting', pclass.__name__, '...',
            sys.stdout.flush()
            T = time.time()
            page = pclass(system)
            f = open(os.path.join(self.base, pclass.filename), 'w')
            f.write(flat.flatten(page))
            f.close()
            print "took", time.time() - T, 's'

    def writeDocsFor(self, ob, functionpages):
        isfunc = ob.document_in_parent_page
        if (isfunc and functionpages) or not isfunc:
            f = open(os.path.join(self.base, link(ob)), 'w')
            self.writeDocsForOne(ob, f)
            f.close()
        for o in ob.orderedcontents:
            self.writeDocsFor(o, functionpages)

    def writeDocsForOne(self, ob, fobj):
        if self.dry_run:
            self.total_pages += 1
            return
        # brrrrrrrr!
        d = pages.__dict__
        for c in ob.__class__.__mro__:
            n = c.__name__ + 'Page'
            if n in d:
                pclass = d[n]
                break
        else:
            pclass = pages.CommonPage
        if self.system.options.verbosity > 0:
            print ob
        page = pclass(ob)
        self.written_pages += 1
        if self.system.options.verbosity == 0:
            print '\rwritten', self.written_pages, '/', self.total_pages, 'pages',
        sys.stdout.flush()
        fobj.write(flat.flatten(page))
