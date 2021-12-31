
__all__ = ["Ord", "Sibling", "Term"]

from collections import defaultdict
from itertools import product
from typing import Dict, Iterator, List, Set, Tuple, Union


_TERM_INSTANCES: Dict[str, 'Term'] = {}


class Term:
    """Logical Term"""

    __slots__ = "name",

    def __new__(cls, *args, **kwargs):
        name = args[0] if args else kwargs["name"]
        if name not in _TERM_INSTANCES:
            _TERM_INSTANCES[name] = super().__new__(cls)
        return _TERM_INSTANCES[name]

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return self.name


SibElem = Union[Term, 'Sibling']


class Sibling:
    """Constraint for tree node siblings"""

    def __init__(self, index: int, *elems: SibElem):
        self.index = index
        self.elems = list(elems)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sibling):
            return NotImplemented
        return (self.index == other.index and
                all(a == b for a, b in zip(self.elems, other.elems)))

    def __repr__(self) -> str:
        elem_reprs = ', '.join(repr(e) for e in self.elems)
        return f"Sibling(index={self.index}, {elem_reprs})"

    # Rules:
    #   1) Sib(x, A, B) => [Sib(x, A, B)]
    #   2) Sib(x, A, Sib(y, B, C)) => [Sib(x, A, B), Sib(y, B, C)]
    def flatten(self) -> List['Sibling']:
        elems = self.elems
        ret = [self]
        for i in range(len(elems)):
            if isinstance(elems[i], Term):
                continue
            flattened = elems[i].flatten()
            ret.extend(flattened)
            elems[i] = flattened[0].elems[0]
        return ret


OrdElem = Union[Term, 'Ordered', List[Union[Term, 'Ordered']]]


class Ord:
    """Constraint for tree node order"""

    def __init__(self, *elems: OrdElem):
        self.elems = elems

    def __repr__(self) -> str:
        elem_reprs = ', '.join(repr(e) for e in self.elems)
        return f"Ord({elem_reprs})"

    def _find_paths(self) -> Iterator[List[Tuple[str, ...]]]:
        for elem in self.elems:
            if isinstance(elem, Term):
                yield [(elem.name,)]
            elif isinstance(elem, Ord):
                yield list(elem._paths_product())
            else:  # elem is List[Union[Term, Ord]]
                yield [
                    item_elem for item in elem for item_elem in
                    (item._paths_product() if isinstance(item, Ord) else [(item.name,)])
                ]

    def _paths_product(self) -> Iterator[Tuple[str, ...]]:
        for prod in product(*self._find_paths()):
            yield tuple(a for b in prod for a in b)

    def to_dag(self) -> Dict[str, Set[str]]:
        ret = defaultdict(set)
        for links in self._paths_product():
            for i in range(len(links) - 1):
                ret[links[i]].add(links[i+1])
        return ret
