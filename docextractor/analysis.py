import cPickle
from docextractor import model

def isInterface(syst, cls):
    if 'zope.interface.Interface' in cls.bases or 'twisted.python.components.Interface' in cls.bases:
        return True
    for b in cls.bases:
        if b in syst.allobjects and isInterface(syst, syst.allobjects[b]):
            return True
    return False

def checkForUndoccedClasses(system):
    seen = {}
    for o in system.objectsOfType(model.Class):
        if '.test.' not in o.fullName():
            for b in o.bases:
                if b.startswith('twisted') and b not in system.allobjects and b not in seen:
                    print b
                    seen[b] = 1

def main(argv):
    system = cPickle.load(open('da.out', 'rb'))
    checkForUndoccedClasses(system)
