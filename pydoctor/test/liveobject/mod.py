class C:
    def m(self):
        "this is a docstring"

m = C().m

exec '''class C: pass'''
