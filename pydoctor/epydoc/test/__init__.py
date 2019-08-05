# epydoc -- Regression testing
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

import pydoctor.epydoc
pydoctor.epydoc.DEBUG = True


import logging, sys
from pydoctor.epydoc import log

class ImmediateStreamHandler(logging.StreamHandler):
    def emit(self, record):
        self.stream = sys.stdout
        logging.StreamHandler.emit(self, record)
        self.flush()

log.addHandler(ImmediateStreamHandler())
log.setLevel(logging.WARNING)
