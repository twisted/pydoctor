class C:
    def m(self):
        "this is a docstring"
    def __m(self):
        "this method's name gets mangled"

m = C().m

class B:
    pass

exec('''class D(B): pass''')
