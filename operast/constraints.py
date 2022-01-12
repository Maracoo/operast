
__all__ = ["Ord", "OrdElem", "Partial", "Sib", "SibElem", "Total"]

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable as Iter
from itertools import product
from typing import Dict, Iterable, Iterator, List, Set, Tuple, TypeVar, Union, cast


T = TypeVar('T')


SibElem = Union[str, 'Sib']


def flatten_irregular(it: Iterable[Union[T, Iterable[T]]]) -> Iterator[T]:
    for i in it:
        if isinstance(i, Iter) and not isinstance(i, str):
            yield from i
        else:
            yield cast(T, i)


class Sib:
    """Constraint for tree node siblings"""

    __slots__ = "index", "elems"

    def __init__(self, index: int, *elems: SibElem):
        self.index = index
        self.elems: List[SibElem] = list(self._flatten(elems))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sib):
            return NotImplemented
        return (self.index == other.index and
                all(a == b for a, b in zip(self.elems, other.elems)))

    def __repr__(self) -> str:  # pragma: no cover
        elem_reprs = ', '.join(repr(e) for e in self.elems)
        return f"{type(self).__name__}(index={self.index}, {elem_reprs})"

    def _flatten(self, elems: Tuple[SibElem, ...]) -> Iterator[SibElem]:
        for elem in elems:
            if isinstance(elem, Sib) and elem.index == self.index:
                yield from elem.elems
            else:
                yield elem

    # Rules:
    #   1) Sib(x, A, B) => [Sib(x, A, B)]
    #   2) Sib(x, A, Sib(y, B, C)) => [Sib(x, A, B), Sib(y, B, C)]
    def constraint(self) -> List['Sib']:
        ret = [self]
        for i, elem, in enumerate(self.elems):
            if isinstance(elem, Sib):
                flattened = elem.constraint()
                ret.extend(flattened)
                self.elems[i] = flattened[0].elems[0]
        return ret


OrdElem = Union[str, 'Ord']
StrTuples = Union[str, Tuple[str, ...]]


class Ord(ABC):
    """Constraint for tree node order"""

    __slots__ = "elems",

    def __init__(self, *elems: OrdElem):
        self.elems = elems

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.elems == other.elems

    def __repr__(self) -> str:  # pragma: no cover
        elem_reprs = ', '.join(repr(e) for e in self.elems)
        return f"{type(self).__name__}({elem_reprs})"

    @abstractmethod
    def _find_paths(self) -> Iterator[List[StrTuples]]:
        raise NotImplementedError  # pragma: no cover

    def _paths_product(self) -> Iterator[Tuple[str, ...]]:
        for tup in product(*self._find_paths()):
            yield tuple(flatten_irregular(tup))

    def to_dag(self) -> Dict[str, Set[str]]:
        dag = defaultdict(set)
        for links in self._paths_product():
            for i in range(len(links) - 1):
                dag[links[i]].add(links[i+1])
        return dag


class Total(Ord):
    def _find_paths(self) -> Iterator[List[StrTuples]]:
        for e in self.elems:
            yield [e] if isinstance(e, str) else list(e._paths_product())


class Partial(Ord):
    def _find_paths(self) -> Iterator[List[StrTuples]]:
        paths = (e._paths_product() if isinstance(e, Ord) else e for e in self.elems)
        yield list(flatten_irregular(paths))
