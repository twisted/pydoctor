class CommonBase(object):
    def fullName(self):
        ...

class NewBaseClassA(CommonBase):
    def methodA(self):
        """
        This is method A.
        """


class NewBaseClassB(CommonBase):
    def methodB(self):
        """
        This is method B.
        """


class NewClassThatMultiplyInherits(NewBaseClassA, NewBaseClassB):
    def methodC(self):
        """
        This is method C.
        """


class OldBaseClassA(CommonBase):
    def methodA(self):
        """
        This is method A.
        """


class OldBaseClassB(CommonBase):
    def methodB(self):
        """
        This is method B.
        """


class OldClassThatMultiplyInherits(OldBaseClassA, OldBaseClassB):
    def methodC(self):
        """
        This is method C.
        """

class Diamond(OldClassThatMultiplyInherits, NewClassThatMultiplyInherits):
    def newMethod(self):...
