from docextractor import model
import pickle

def test_pickling_system():
    system = model.System()
    model.fromText("class A: pass", "mod", system)
    # not sure how to test this, other than that it doesn't fail...
    pickle.loads(pickle.dumps(system))
