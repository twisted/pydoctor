from pydoctor import model

from nevow import rend, loaders, tags

import os, shutil

def link(o):
    return o.fullName()+'.html'

def sibpath(path, sibling):
    return os.path.join(os.path.dirname(os.path.abspath(path)), sibling)

class NevowWriter:
    def __init__(self, filebase):
        self.base = filebase

    def prepOutputDirectory(self):
        if not os.path.exists(self.base):
            os.mkdir(self.base)
        shutil.copyfile(sibpath(__file__, 'apidocs.css'),
                        os.path.join(self.base, 'apidocs.css'))

    def writeIndividualFiles(self, obs):
        for ob in obs:
            self.writeDocsFor(ob)

    def writeModuleIndex(self, system):
        pass

    def writeDocsFor(self, ob):
        pclass = None
        if isinstance(ob, model.Package):
            pclass = PackagePage
        if not pclass:
            print "skipping", ob, "for now!"
        page = pclass(ob)
        f = open(os.path.join(self.base, link(ob)), 'w')
        def _cb(text):
            f.write(text)
            f.close()
        page.renderString().addCallback(_cb)
        assert f.closed

class PackagePage(rend.Page):
    docFactory = loaders.stan(tags.html[
        tags.head[
        tags.title["hello"]],
        tags.body[
        tags.h1["there"]]])
    def __init__(self, pkg):
        self.pkg = pkg
    
        
        
