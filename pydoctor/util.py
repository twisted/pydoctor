"""
Misc utils.
"""
import os
import subprocess


def get_source_reference() -> str:
    """
    Return a reference to the particular source version used in this build.
    This can be used in the URL passed with C{--html-viewsource-base}, to link to the
    version of the source code that corresponds with the generated documentation.

    It tries the extract the tag name from Read The Docs environment and
    falls back to source code revision.

    Only git VSC is supported for now.

    @raises RuntimeError: If source reference couldn't be retrieved.
    """
    if os.environ.get("READTHEDOCS", "") == "True":
        rtd_version = os.environ.get("READTHEDOCS_VERSION", "")
        if rtd_version not in ['latest', 'stable']:
            # It looks like we have a tag build.
            return rtd_version

    try:
        return _get_git_reference()
    except Exception as error:
        raise RuntimeError(f'Failed to get git reference. {error}')


def _get_git_reference() -> str:
    """
    Return the reference for current git checkout to be used when linking
    the source files.

    @return: Tag name, branch name, or fallback to SHA.
    """
    reference_name = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        universal_newlines=True,
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
            universal_newlines=True,
            encoding="utf8",
            capture_output=True,
            check=True,
            ).stdout.strip()

    return result
