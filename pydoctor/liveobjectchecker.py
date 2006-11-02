from pydoctor import model
import types, sys, os, warnings, inspect

def loadModulesForSystem(system):
    """
    Return a dictionary mapping model.Modules to real modules.
    """
    result = {}
    savepath = sys.path[:]
    savefilters = warnings.filters[:]
    mods = sys.modules.copy()
    try:
        sys.path[0:0] = [os.path.dirname(p) for p in system.packages]
        #print sys.path
        warnings.filterwarnings('ignore')
        # this list found by the lovely hack of python -E -c "import sys; print sys.modules.keys()"
        keeps = ['copy_reg', '__main__', 'site', '__builtin__',
                 'encodings', 'posixpath', 'encodings.codecs', 'os.path',
                 '_codecs', 'encodings.exceptions', 'stat', 'zipimport',
                 'warnings', 'encodings.types', 'UserDict', 'encodings.ascii',
                 'sys', 'codecs', 'readline', 'types', 'signal', 'linecache',
                 'posix', 'encodings.aliases', 'exceptions', 'os']
        keeps = dict([(k, sys.modules[k]) for k in keeps if k in sys.modules])
        sys.modules.clear()
        sys.modules.update(keeps)

        verbosity = system.options.verbosity

        modlist = list(system.objectsOfType(model.Module))
        errcount = 0

        for i, m in enumerate(modlist):
            try:
                realMod = __import__(m.fullName(), {}, {}, ['*'])
            except ImportError, e:
                errcount += 1
                if verbosity > 0:
                    print "could not import", m.fullName(), e
            except Exception, e:
                errcount += 1
                if verbosity > 0:
                    print "error importing", m.fullName(), e
            else:
                result[m] = realMod

            print '\r', i+1-errcount, '/', len(modlist), 'modules imported',
            print errcount, 'failed',
            sys.stdout.flush()
        print
    finally:
        sys.path[:] = savepath
        warnings.filters[:] = savefilters
        sys.modules.clear()
        sys.modules.update(mods)
    return result


_types = {}

def checker(*typs):
    def _(func):
        for typ in typs:
            _types[typ] = func
        return func
    return _

@checker(types.MethodType)
def methChecker(builder, name, OBJ):
    if OBJ.im_self is None:
        return
    f = builder.pushFunction(OBJ.__name__, OBJ.__doc__)
    if builder.system.options.verbosity > 0:
        print '**meth**', builder.current, '*************'
    try:
        argspec = inspect.getargspec(OBJ)
        if argspec[0]:
            del argspec[0][0]
        f.argspec = argspec
    finally:
        builder.popFunction()

@checker(types.TypeType, types.ClassType)
def typeChecker(builder, name, OBJ):
    c = builder.current
    mod = c
    while not isinstance(mod, model.Module):
        mod = mod.parent
    if getattr(OBJ, '__module__', None) != mod.fullName() or getattr(OBJ, '__name__', None) != name:
        return
    cls = builder.pushClass(OBJ.__name__, OBJ.__doc__)
    if builder.system.options.verbosity > 0:
        print '**type**', builder.current, '*************'
    try:
        for BASE in OBJ.__bases__:
            baseName = getattr(BASE, '__name__', '?')
            fullName = getattr(BASE, '__module__', '?') + '.' + baseName
            if baseName in mod._name2fullname:
                cls.rawbases.append(baseName)
            else:
                cls.rawbases.append(fullName)
            cls.bases.append(fullName)
            baseObject = builder.system.allobjects.get(fullName)
            cls.baseobjects.append(baseObject)
            if baseObject is not None:
                baseObject.subclasses.append(cls)
        for cls2 in builder.system.objectsOfType(model.Class):
            if cls.fullName() in cls2.bases:
                index = cls2.bases.index(cls.fullName())
                assert cls2.baseobjects[index] is None
                cls2.baseobjects[index] = cls
                cls.subclasses.append(cls2)
        checkDict(builder, OBJ.__dict__)
    finally:
        builder.popClass()

@checker(types.FunctionType)
def funcChecker(builder, name, OBJ):
    c = builder.current
    mod = c
    while not isinstance(mod, model.Module):
        mod = mod.parent
    if getattr(OBJ, '__module__', None) != mod.fullName() or getattr(OBJ, '__name__', None) != name:
        return
    f = builder.pushFunction(OBJ.__name__, OBJ.__doc__)
    if builder.system.options.verbosity > 0:
        print '**func**', builder.current, '*************'
    try:
        argspec = inspect.getargspec(OBJ)
        f.argspec = argspec
    finally:
        builder.popFunction()


def checkDict(builder, aDict):
    c = builder.current
    for name in aDict:
        if name in ('__name__', '__doc__', '__file__', '__builtins__', '__module__'):
            continue
        if name in c.contents:
            continue
        if name in c._name2fullname:
            continue
        OBJ = aDict[name]
        checker = _types.get(type(OBJ))
        if checker is not None:
            checker(builder, name, OBJ)

def liveCheck(system, builder=None):
    if builder is None:
        builder = system.defaultBuilder(system)
    realMods = loadModulesForSystem(system)
    for m in realMods:
        builder.push(m)
        checkDict(builder, realMods[m].__dict__)
        builder.pop(m)
    system.state = 'livechecked'
