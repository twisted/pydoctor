from typing import Dict, Optional
import pytest

from pydoctor.templatewriter.util import CaseInsensitiveDict

class TestCaseInsensitiveDict:
    
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """CaseInsensitiveDict instance with "Accept" header."""
        self.case_insensitive_dict: CaseInsensitiveDict[str] = CaseInsensitiveDict()
        self.case_insensitive_dict['Accept'] = 'application/json'

    def test_list(self) -> None:
        assert list(self.case_insensitive_dict) == ['Accept']

    possible_keys = pytest.mark.parametrize('key', ('accept', 'ACCEPT', 'aCcEpT', 'Accept'))

    @possible_keys
    def test_getitem(self, key: str) -> None:
        assert self.case_insensitive_dict[key] == 'application/json'

    @possible_keys
    def test_delitem(self, key: str) -> None:
        del self.case_insensitive_dict[key]
        assert key not in self.case_insensitive_dict

    def test_lower_items(self) -> None:
        assert list(self.case_insensitive_dict.lower_items()) == [('accept', 'application/json')]

    def test_repr(self) -> None:
        assert repr(self.case_insensitive_dict) == "{'Accept': 'application/json'}"

    def test_copy(self) -> None:
        copy = self.case_insensitive_dict.copy()
        assert copy is not self.case_insensitive_dict
        assert copy == self.case_insensitive_dict

    @pytest.mark.parametrize(
        'other, result', (
            ({'AccePT': 'application/json'}, True),
            ({}, False),
            (None, False)
        )
    )
    def test_instance_equality(self, other: Optional[Dict[str, str]], result: bool) -> None:
        assert (self.case_insensitive_dict == other) is result
