from collections import deque
from typing import TypeVar, Generic, Iterator, Iterable, Self, overload, Optional


maxsize = 9223372036854775807

T = TypeVar("T")
U = TypeVar("U")


class Peekable(Generic[T], Iterator[T]):
    def __init__(self, iterable: Iterable[T]):
        self._it = iter(iterable)
        self._cache = deque()

    def __iter__(self) -> Self:
        return self

    def __bool__(self) -> bool:
        try:
            self.peek()
        except StopIteration:
            return False
        return True

    @overload
    def peek(self) -> T:
        ...

    @overload
    def peek(self, default: U) -> T | U:
        ...

    def peek(self, default: Optional[U] = None) -> T | U:
        if not self._cache:
            try:
                self._cache.append(next(self._it))
            except StopIteration:
                if default is None:
                    raise
                return default
        return self._cache[0]

    def prepend(self, *items: T):
        self._cache.extendleft(reversed(items))

    def __next__(self) -> T:
        if self._cache:
            return self._cache.popleft()

        return next(self._it)
