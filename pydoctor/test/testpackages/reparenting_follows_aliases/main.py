"""
This module imports MyClass from _myotherthing 
and re-export it in it's __all__ varaible

But _myotherthing.MyClass is a alias to _mything.MyClass,
so _mything.MyClass should be reparented to main.MyClass. 
"""
from ._myotherthing import MyClass
__all__=('myfunc', 'MyClass')
def myfunc(): ...
