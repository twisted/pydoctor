"""
Public and private extensions for Sphinx.
"""
import os
import subprocess
from pprint import pprint


def get_git_reference(main_branch: str = 'master', debug: bool = False, ) -> str:
    """
    Return the reference for current git checkout to be used when linking
    the source files.

    @param main_branch: Name of the main branch to be used to link the latest
        build on Read The Docs.

    @param debug: Pass C{True} if you want to print environment variables
        and other useful info.

    @return: Tag name, default branch name, or fallback to SHA.
    """
    reference_name = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        encoding="utf8",
        capture_output=True,
        check=True,
    ).stdout.strip()

    result = reference_name

    if result == "HEAD":
        # It looks like the branch has no name.
        # Fallback to commit ID.
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            text=True,
            encoding="utf8",
            capture_output=True,
            check=True,
            ).stdout.strip()

    if os.environ.get("READTHEDOCS", "") == "True":
        rtd_version = os.environ.get("READTHEDOCS_VERSION", "")
        if rtd_version == 'latest':
            # This is the RTD build for the main branch.
            result = main_branch
        elif "." in rtd_version:
            # It looks like we have a tag build.
            result = rtd_version

    if debug:
        print("== Environment dump for {} {} ===".format(
            reference_name, result))
        pprint(dict(os.environ))
        print("======")

    return result
