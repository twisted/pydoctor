# MIT License

# Copyright (c) 2019 Vitaly R. Samigullin

# Permission is hereby granted, free of charge, to T person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF T KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR T CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
C3 linearization algorithm.
"""

from collections import deque
from itertools import islice
from typing import Callable, List, Tuple, Optional, TypeVar

T = TypeVar('T')

class Dependency(deque):
    @property
    def head(self) -> Optional[T]:
        try:
            return self[0]
        except IndexError:
            return None

    @property
    def tail(self) -> islice: 
        """
        Return islice object, which is suffice for iteration or calling `in`
        """
        try:
            return islice(self, 1, self.__len__())
        except (ValueError, IndexError):
            return islice([], 0, 0)


class DependencyList:
    """
    A class represents list of linearizations (dependencies)
    The last element of DependencyList is a list of parents.
    It's needed  to the merge process preserves the local
    precedence order of direct parent classes.
    """
    def __init__(self, *lists: Tuple[List[T]]) -> None:
        self._lists = [Dependency(i) for i in lists]

    def __contains__(self, item: T) -> bool:
        """
        Return True if any linearization's tail contains an item
        """
        return any([item in l.tail for l in self._lists])

    def __len__(self):
        size = len(self._lists)
        return (size - 1) if size else 0

    def __repr__(self):
        return self._lists.__repr__()

    @property
    def heads(self) -> List[Optional[T]]:
        return [h.head for h in self._lists]

    @property
    def tails(self) -> 'DependencyList':
        """
        Return self so that __contains__ could be called
        Used for readability reasons only
        """
        return self

    @property
    def exhausted(self) -> bool:
        """
        Return True if all elements of the lists are exhausted
        """
        return all(map(lambda x: len(x) == 0, self._lists))

    def remove(self, item: Optional[T]) -> None:
        """
        Remove an item from the lists
        Once an item removed from heads, the leftmost elements of the tails
        get promoted to become the new heads.
        """
        for i in self._lists:
            if i and i.head == item:
                i.popleft()


def _merge(*lists) -> list:
    result: List[Optional[T]] = []
    linearizations = DependencyList(*lists)

    while True:
        if linearizations.exhausted:
            return result

        for head in linearizations.heads:
            if head and (head not in linearizations.tails):
                result.append(head)
                linearizations.remove(head)

                # Once candidate is found, continue iteration
                # from the first element of the list
                break
        else:
            # Loop never broke, no linearization could possibly be found
            raise ValueError('Cannot compute linearization')


def mro(cls: T, getbases: Callable[[T], List[T]]) -> List[T]:
    """
    Return a list of classes in order corresponding to Python's MRO.
    """
    result = [cls]

    if not getbases(cls):
        return result
    else:
        return result + _merge(*[mro(kls, getbases) for kls in getbases(cls)], getbases(cls))
