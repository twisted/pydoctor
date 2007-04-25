import py
import sys

rootdir = py.magic.autopath().dirpath()

sys.path.append(str(rootdir.dirpath().dirpath()))

import py
Option = py.test.config.Option

option = py.test.config.addoptions("pydoctor options",
        Option('--view-html',
               action="store_true", dest="viewhtml", 
               help=("")))
