"""
Here the module C{mod} is made available under an alias name
that is explicitly advertised under the alias name. 
"""
from . import mod as module
__all__=('module',)
