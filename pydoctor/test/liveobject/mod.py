class C:
    def m(self):
        "this is a docstring"

m = C().m

class B:
    pass

exec '''class D(B): pass'''
