from pydoctor.test.test_packages import processPackage
from pydoctor.liveobjectchecker import liveCheck

def test_simple():
    system = processPackage('liveobject')
    liveCheck(system)
    mod = system.allobjects['liveobject.mod']
    assert mod.contents['m'].docstring == 'this is a docstring'
    assert 'C' in mod.contents
    cls = mod.contents['C']
    assert cls.name == 'C'
    
