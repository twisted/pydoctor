import pathlib
import re

import setuptools


setuptools.setup(
    long_description=re.sub(
        pattern="(?ms)^.. description-end.*",
        repl="",
        string=pathlib.Path("README.rst").read_text(encoding="utf-8"),
        count=1,
    )
)
