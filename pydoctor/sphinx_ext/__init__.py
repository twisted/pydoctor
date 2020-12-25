"""
Public and private extensions for Sphinx.
"""
import os
import subprocess


def get_source_reference() -> str:
    """
    Return the reference for current build to be used when linking
    the source files.
    """
    if os.environ.get("READTHEDOCS", "") == "True":
        rtd_version = os.environ.get("READTHEDOCS_VERSION", "")
        if "." in rtd_version:
            # It looks like we have a tag build.
            return rtd_version

    return _get_git_reference()


def _get_git_reference() -> str:
    """
    Return the reference for current git checkout to be used when linking
    the source files.

    @return: Tag name, branch name, or fallback to SHA.
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
        # This can happen for CI builds.
        # Fallback to commit ID.
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            text=True,
            encoding="utf8",
            capture_output=True,
            check=True,
            ).stdout.strip()

    return result
