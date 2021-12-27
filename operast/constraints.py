
__all__ = ["Ord", "Sibling", "Term"]

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class Term:
    """Logical Term"""

    def __init__(self, name: str, value: Optional[Any] = None):
        self.name = name
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.value == other.value


SibElem = Union[Term, 'Sibling']


class Sibling:
    """Constraint for tree node siblings"""

    def __init__(self, index: int, *elems: SibElem):
        self.index = index
        self.elems = list(elems)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sibling):
            return NotImplemented
        return self.index == other.index and all(a == b for a, b in zip(self.elems, other.elems))

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
            elems[i] = elems[0]
        return ret


class Node:
    """Helper class for building Ordered DAG"""

    def __init__(self, term: Term):
        self.term = term
        self.children: List[Node] = []

    def __repr__(self) -> str:
        if self.children:
            children_repr = ', '.join(repr(c) for c in self.children)
            return f"Node('{self.term.name}', children=[{children_repr}])"
        return f"Node('{self.term.name}')"

    def add_children(self, children: List['Node']) -> None:
        self.children.extend(children)

    def to_dag(self) -> Dict[str, Set[str]]:
        ret = defaultdict(set)
        for c in self.children:
            ret[self.term.name].add(c.term.name)
            ret.update(c.to_dag())
        return ret


OrdElem = Union[Term, 'Ordered', List[Union[Term, 'Ordered']]]


class Ord:
    """Constraint for tree node order"""

    def __init__(self, *elems: OrdElem):
        self.elems = elems

    # Cases:
    #   1) Ord(A, B) => A -> B
    #   2) Ord(A, [B, C]) => A -> B, A -> C
    #   3) Ord([A, B], C) => A -> C, B -> C
    #   4) Ord(A, [Ord(B, C), D]) => Ord(A, [B -> C, D]) => A -> B -> C, A -> D
    #   5) Ord([A, Ord(B, C)], D) => Ord([A, B -> C], D) => A -> D, B -> C -> D
    #   6) Ord(A, [Ord([B, C], D), E]) => Ord(A, [B -> D, C -> D, E]) => A -> B -> D, A -> C -> D, A -> E
    #   7) Ord(A, [Ord([B, C], D), E], F) => Ord(A, [B -> D, C -> D, E], F) =>
    #       A -> B -> D -> F, A -> C -> D -> F, A -> E -> F
    def _construct_graph(self) -> Tuple[List[Node], List[Node]]:
        first: List[Node] = []
        last: List[Node] = []
        for elem in self.elems:
            if isinstance(elem, Term):
                node = Node(elem)
                new_first, new_last = [node], [node]
            elif isinstance(elem, Ord):
                new_first, new_last = elem._construct_graph()
            else:  # elem is List[Union[Term, Ordered]]
                new_first, new_last = [], []
                for sub_e in elem:
                    if isinstance(sub_e, Term):
                        node = Node(sub_e)
                        new_first.append(node)
                        new_last.append(node)
                    else:  # elem is Ordered
                        _fst, _lst = sub_e._construct_graph()
                        new_first.extend(_fst)
                        new_last.extend(_lst)
            if not first:
                first = new_first
            for node in last:
                node.add_children(new_first)
            last = new_last
        return first, last

    def to_dag(self) -> Dict[str, Set[str]]:
        ret = defaultdict(set)
        nodes = self._construct_graph()[0]
        for node in nodes:
            for term_name, children in node.to_dag().items():
                ret[term_name].update(children)
        return ret
