import py
import sys

rootdir = py.magic.autopath().dirpath()

sys.path.append(str(rootdir.dirpath().dirpath()))
