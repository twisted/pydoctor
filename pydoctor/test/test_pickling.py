from __future__ import print_function

import pickle

from pydoctor import model
from pydoctor.test.test_astbuilder import fromText


def test_pickling_system():
    system = model.System()
    fromText("class A: pass", "mod", system)
    # not sure how to test this, other than that it doesn't fail...
    pickle.loads(pickle.dumps(system))
