from pydoctor import model
import types, sys, os, warnings, inspect

def liveCheck(system, builder=None):
    savepath = sys.path[:]
    savefilters = warnings.filters[:]
    try:
        sys.path[0:0] = [os.path.dirname(p) for p in system.packages]
        print sys.path
        if builder is None:
            builder = system.defaultBuilder(system)
        warnings.filterwarnings('ignore')

        for m in system.objectsOfType(model.Module):
            try:
                realMod = __import__(m.fullName(), {}, {}, ['*'])
            except ImportError, e:
                print "could not import", m.fullName(), e
                continue
            except Exception, e:
                print "error importing", m.fullName(), e
                continue
            builder.push(m)
            for name in realMod.__dict__:
                if name in ('__name__', '__doc__', '__file__', '__builtins__'):
                    continue
                if name in m.contents:
                    continue
                if name in m._name2fullname:
                    continue
                OBJ = realMod.__dict__[name]
                if type(OBJ) is types.MethodType and OBJ.im_self is not None:
                    f = builder.pushFunction(OBJ.__name__, OBJ.__doc__)
                    print '*********', builder.current, '*************'
                    try:
                        argspec = inspect.getargspec(OBJ)
                        del argspec[0][0]
                        f.argspec = argspec
                    finally:
                        builder.popFunction()
            builder.pop(m)
    finally:
        sys.path[:] = savepath
        warnings.filters[:] = savefilters
    system.state = 'livechecked'
