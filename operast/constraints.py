
__all__ = ["Ord", "Sib"]

from collections import defaultdict
from itertools import product
from typing import Dict, Iterator, List, Set, Tuple, Union


SibElem = Union[str, 'Sib']


class Sib:
    """Constraint for tree node siblings"""

    __slots__ = "index", "elems"

    def __init__(self, index: int, *elems: SibElem):
        self.index = index
        new_elems = []
        for elem in elems:
            if isinstance(elem, Sib) and elem.index == self.index:
                new_elems.extend(elem.elems)
            else:
                new_elems.append(elem)
        self.elems = new_elems

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sib):
            return NotImplemented
        return (self.index == other.index and
                all(a == b for a, b in zip(self.elems, other.elems)))

    def __repr__(self) -> str:
        elem_reprs = ', '.join(repr(e) for e in self.elems)
        return f"Sib(index={self.index}, {elem_reprs})"

    # Rules:
    #   1) Sib(x, A, B) => [Sib(x, A, B)]
    #   2) Sib(x, A, Sib(y, B, C)) => [Sib(x, A, B), Sib(y, B, C)]
    def flatten(self) -> List['Sib']:
        ret = [self]
        for i, elem, in enumerate(self.elems):
            if isinstance(elem, Sib):
                flattened = elem.flatten()
                ret.extend(flattened)
                self.elems[i] = flattened[0].elems[0]
        return ret


OrdElem = Union[str, 'Ord', List[Union[str, 'Ord']]]


class Ord:
    """Constraint for tree node order"""

    __slots__ = "elems",

    def __init__(self, *elems: OrdElem):
        self.elems = elems

    def __repr__(self) -> str:
        elem_reprs = ', '.join(repr(e) for e in self.elems)
        return f"Ord({elem_reprs})"

    def _find_paths(self) -> Iterator[List[Tuple[str, ...]]]:
        for elem in self.elems:
            if isinstance(elem, str):
                yield [(elem,)]
            elif isinstance(elem, Ord):
                yield list(elem._paths_product())
            else:  # elem is List[Union[Term, Ord]]
                yield [
                    item_elem for item in elem for item_elem in
                    (item._paths_product() if isinstance(item, Ord) else [(item,)])
                ]

    def _paths_product(self) -> Iterator[Tuple[str, ...]]:
        for prod in product(*self._find_paths()):
            yield tuple(a for b in prod for a in b)

    def to_dag(self) -> Dict[str, Set[str]]:
        dag = defaultdict(set)
        for links in self._paths_product():
            for i in range(len(links) - 1):
                dag[links[i]].add(links[i+1])
        return dag
