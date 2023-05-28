from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import re
import sys

from pydoctor.options import Options
from pydoctor import driver

from . import CapSys
