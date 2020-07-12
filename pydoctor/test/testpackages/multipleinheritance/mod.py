class NewBaseClassA:
    def methodA(self):
        """
        This is method A.
        """


class NewBaseClassB:
    def methodB(self):
        """
        This is method B.
        """


class NewClassThatMultiplyInherits(NewBaseClassA, NewBaseClassB):
    def methodC(self):
        """
        This is method C.
        """


class OldBaseClassA:
    def methodA(self):
        """
        This is method A.
        """


class OldBaseClassB:
    def methodB(self):
        """
        This is method B.
        """


class OldClassThatMultiplyInherits(OldBaseClassA, OldBaseClassB):
    def methodC(self):
        """
        This is method C.
        """
