"""
Tests for util code.
"""
import pytest

from pydoctor.util import get_source_reference
from . import MonkeyPatch


def test_get_source_reference_rtd_tag(monkeypatch: MonkeyPatch) -> None:
    """
    When running in a RTD environment, it will use the READTHEDOCS_VERSION
    value when it looks like a VCS tag.
    """
    monkeypatch.setenv("READTHEDOCS", "True")
    monkeypatch.setenv("READTHEDOCS_VERSION", "V_1_2")

    result = get_source_reference()

    assert result == 'V_1_2'


def test_get_source_reference_RTD_latest(monkeypatch: MonkeyPatch) -> None:
    """
    When the RTD environment version is `latest` it returns the git
    branch name or SHA.
    """
    monkeypatch.setenv("READTHEDOCS", "True")
    monkeypatch.setenv("READTHEDOCS_VERSION", "latest")

    result = get_source_reference()

    # This is a system integration test and is hard to assert the actual
    # value here.
    # On local build you get the branch name, on CI you might get the SHA.
    assert result != "latest"


def test_get_source_reference_git_fail(monkeypatch: MonkeyPatch) -> None:
    """
    When getting the git reference fails, it raised RunntimeError.
    """
    monkeypatch.setenv("READTHEDOCS", "False")
    monkeypatch.chdir('/')

    with pytest.raises(RuntimeError) as exc_info:
        get_source_reference()

    exc_info.match('Failed to get git reference. ')
