import cPickle, pprint
from docextractor import model

def listInterfaces(system):
    interfaces = {}
    for cls in system.objectsOfType(model.Class):
        if cls.isinterface:
            interfaces[cls.fullName()] = []

    for cls in system.objectsOfType(model.Class):
        for i in cls.implements:
            if i in interfaces:
                interfaces[i].append(cls)

    pprint.pprint(interfaces)


def main(argv):
    system = cPickle.load(open('da.out', 'rb'))
    listInterfaces(system)
