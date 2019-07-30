# epydoc -- Regression testing
#
# Copyright (C) 2005 Edward Loper
# Author: Edward Loper <edloper@loper.org>
# URL: <http://epydoc.sf.net>
#

import pydoctor.epydoc
pydoctor.epydoc.DEBUG = True

from pydoctor.epydoc import log
del log._loggers[:]
log.register_logger(log.SimpleLogger(log.WARNING))
