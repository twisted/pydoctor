from sub2.mod import A
import mod1
import sub2.mod
from mod2 import B

class C(A, sub2.mod.B, mod1.C, B):
    pass
