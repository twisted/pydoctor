"""
A collection of helpful iterators.

Forked from ``sphinx.ext.napoleon.iterators``. 

:copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import collections
from typing import Any, Callable, Deque, Iterable, Iterator, Optional, Sequence, TypeVar, Generic, Union, overload

__docformat__ = "numpy en" 

T = TypeVar("T")

class peek_iter(Generic[T]):
    """
    An iterator object that supports peeking ahead.

    `peek_iter` can operate as a drop in replacement for the built-in `iter` function.
    
    Attributes
    ----------
    sentinel
        The value used to indicate the iterator is exhausted. 
        If `sentinel` was not given when the `peek_iter` was instantiated, then it will
        be set to a new object instance: ``object()``.
    counter
        Store and increment line number to report correct lines!
    """
    def __init__(self, o: Union[Callable[[], T], Iterable[T]], sentinel: Optional[T]=None) -> None:
        """
        Parameters
        ----------
        o : Iterable or Callable
            ``o`` is interpreted very differently depending on the presence of
            `sentinel`.
            If ``sentinel`` is not given, then ``o`` must be a collection object
            which supports either the iteration protocol or the sequence protocol.
            If ``sentinel`` is given, then ``o`` must be a callable object.
        sentinel : object, optional
            If given, the iterator will call ``o`` with no arguments for each
            call to its `next` method; if the value returned is equal to
            ``sentinel``, `StopIteration` will be raised, otherwise the
            value will be returned.
        """
        self._iterable : Iterator[T]
        if callable(o) :
            if not sentinel: raise TypeError("If o is a callable object, sentinel cannot be None.")
            self._iterable = iter(o, sentinel)
        else: 
            if sentinel: raise TypeError("If sentinel is given, then o must be a callable object.")
            self._iterable =  iter(o)

        self._cache : Deque[T] = collections.deque()

        if sentinel:
            self.sentinel = sentinel
        else:
            # mypy error: Incompatible types in assignment (expression
            # has type "object", variable has type "T")  
            self.sentinel = object() # type: ignore[assignment]
        
        # store line number to report correct lines!
        self.counter = 0

    def __iter__(self) -> "peek_iter[T]":
        return self

    # overridden: no n param: it was not used. 
    def __next__(self) -> T:  
        return self.next()

    def _fillcache(self, n: Optional[int]) -> None:
        """Cache ``n`` items. If ``n`` is 0 or None, then 1 item is cached."""
        if not n:
            n = 1
        try:
            while len(self._cache) < n:
                self._cache.append(next(self._iterable))
        except StopIteration:
            while len(self._cache) < n:
                self._cache.append(self.sentinel)

    def has_next(self) -> bool:
        """Determine if iterator is exhausted.
        Returns
        -------
        bool
            True if iterator has more items, False otherwise.
        Note
        ----
        Will never raise :exc:`StopIteration`.
        """
        return self.peek() != self.sentinel

    @overload
    def next(self, n: int) -> Sequence[T]: 
        ...
    @overload
    def next(self) -> T: 
        ...
    def next(self, n: Optional[int] = None) -> Union[Sequence[T], T]: 
        """
        Get the next item or ``n`` items of the iterator.
        
        Parameters
        ----------
        n : int or None
            The number of items to retrieve. Defaults to None.
        
        Returns
        -------
        The next item or ``n`` items of the iterator. If ``n`` is None, the
        item itself is returned. If ``n`` is an int, the items will be
        returned in a list. If ``n`` is 0, an empty list is returned.
        
        Raises
        ------
        StopIteration
            Raised if the iterator is exhausted, even if ``n`` is 0.
        """
        result: Union[T, Sequence[T]]
        self._fillcache(n)
        if not n:
            if self._cache[0] == self.sentinel:
                raise StopIteration
            if n is None:
                result = self._cache.popleft() 
            else:
                result = [] 
        else:
            if self._cache[n - 1] == self.sentinel:
                raise StopIteration
            result = [self._cache.popleft() for i in range(n)] 
        self.counter += n or 1
        return result
    
    @overload
    def peek(self, n: int) -> Sequence[T]: 
        ...
    @overload
    def peek(self) -> T: 
        ...
    def peek(self, n: Optional[int] = None) -> Union[Sequence[T], T]: 
        """Preview the next item or ``n`` items of the iterator.
        The iterator is not advanced when peek is called.
        
        Returns
        -------
        The next item or ``n`` items of the iterator. If ``n`` is None, the
        item itself is returned. If ``n`` is an int, the items will be
        returned in a list. If ``n`` is 0, an empty list is returned.
        If the iterator is exhausted, `peek_iter.sentinel` is returned,
        or placed as the last item in the returned list.
        
        Note
        ----
        Will never raise :exc:`StopIteration`.
        """
        self._fillcache(n)
        result: Union[Sequence[T], T]
        if n is None:
            result = self._cache[0]
        else:
            result = [self._cache[i] for i in range(n)]
        return result
        


class modify_iter(peek_iter[T]):
    """
    An iterator object that supports modifying items as they are returned.

    Attributes
    ----------
    modifier : Callable
        ``modifier`` is called with each item in ``o`` as it is iterated. The
        return value of ``modifier`` is returned in lieu of the item.
        Values returned by `peek` as well as `next` are affected by
        ``modifier``. However, `sentinel` is never passed through
        ``modifier``; it will always be returned from `peek` unmodified.
    
    Example
    -------
    >>> a = ["     A list    ",
    ...      "   of strings  ",
    ...      "      with     ",
    ...      "      extra    ",
    ...      "   whitespace. "]
    >>> modifier = lambda s: s.strip().replace('with', 'without')
    >>> for s in modify_iter(a, modifier=modifier):
    ...   print('"%s"' % s)
    "A list"
    "of strings"
    "without"
    "extra"
    "whitespace."
    """
    def __init__(self, o: Union[Callable[[], T], Iterable[T]], 
                 sentinel: Optional[T] = None, 
                 modifier: Optional[Callable[[str], str]] = None) -> None:
        """
        Parameters
        ----------
        o : Iterable or Callable
            ``o`` is interpreted very differently depending on the presence of
            ``sentinel``.
            If ``sentinel`` is not given, then ``o`` must be a collection object
            which supports either the iteration protocol or the sequence protocol.
            If ``sentinel`` is given, then ``o`` must be a callable object.
        sentinel : object, optional
            If given, the iterator will call ``o`` with no arguments for each
            call to its `next` method; if the value returned is equal to
            ``sentinel``, :exc:`StopIteration` will be raised, otherwise the
            value will be returned.
        modifier : callable, optional
            The function that will be used to modify each item returned by the
            iterator. ``modifier`` should take a single argument and return a
            single value. Defaults to ``lambda x: x``.
            If ``sentinel`` is not given, `modifier` must be passed as a keyword
            argument.
        """
        if modifier:
            self.modifier = modifier
        else:
            self.modifier = lambda x: x
        if not callable(self.modifier):
            raise TypeError('modify_iter(): modifier must be callable')
        super().__init__(o, sentinel)

    def _fillcache(self, n: Optional[int]) -> None:
        """Cache ``n`` modified items. If ``n`` is 0 or None, 1 item is cached.
        Each item returned by the iterator is passed through the
        `modify_iter.modifier` function before being cached.
        """
        if not n:
            n = 1
        try:
            while len(self._cache) < n:
                self._cache.append(self.modifier(next(self._iterable)))
        except StopIteration:
            while len(self._cache) < n:
                self._cache.append(self.sentinel)
