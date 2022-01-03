
__all__ = [
    "EXTENSIONS",
    "And",
    "Branch",
    "Or",
    "StateEff",
    "Then",
    "TreeElem",
    "TreePattern",
    "tree_elem_expand"
]

from abc import ABC, abstractmethod
from itertools import product, zip_longest
from operast.constraints import Ord, OrdElem, Sib, SibElem, Total, Partial
from typing import Callable, Dict, Generic, Iterable, Iterator, \
    List, Tuple, Type, TypeVar, Union

T = TypeVar('T')


class StateEff(Generic[T]):
    def __init__(self, elem: T):
        self.elem = elem

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StateEff):
            return NotImplemented
        return tree_elem_equals(self, other)

    def __repr__(self) -> str:
        return f'{type(self).__name__}({tree_elem_repr(self.elem)})'


TreeElem = Union['TreePattern', StateEff, T]
Aliases = Dict[str, 'Branch']

EXTENSIONS: Dict[type, Dict[str, Callable]] = {
    str: {
        'expand': lambda x: x,
        '__eq__': str.__eq__,
        '__repr__': str.__repr__,
    }
}


def _extension_type(t: T) -> type:
    for typ in EXTENSIONS:
        if (isinstance(t, type) and issubclass(t, typ)) or isinstance(t, typ):
            return typ
        if isinstance(t, tuple):
            for i in t:
                return _extension_type(i)
    raise ValueError(f"No type of {t} found in extensions.")


def get_extension_func(t: T, name: str) -> Callable:
    return EXTENSIONS[_extension_type(t)][name]


def _extension_expand(t: T) -> Callable[[T], TreeElem[T]]:
    return get_extension_func(t, 'expand')


def _extension_eq(t: T) -> Callable[[T, T], bool]:
    return get_extension_func(t, '__eq__')


def _extension_repr(t: T) -> Callable[[T], str]:
    return get_extension_func(t, '__repr__')


def tree_elem_expand(elem: TreeElem[T]) -> TreeElem[T]:
    if isinstance(elem, StateEff):
        elem.elem = tree_elem_expand(elem.elem)
        return elem
    if isinstance(elem, TreePattern):
        for i, e in enumerate(elem.elems):
            elem.elems[i] = tree_elem_expand(e)
        return elem
    return _extension_expand(elem)(elem)


def tree_elem_equals(elem_a: TreeElem[T], elem_b: TreeElem[T]) -> bool:
    if isinstance(elem_a, (TreePattern, StateEff)):
        return elem_a == elem_b
    return _extension_eq(elem_a)(elem_a, elem_b)


def tree_elem_repr(elem: TreeElem[T]) -> str:
    if isinstance(elem, (TreePattern, StateEff)):
        return repr(elem)
    return _extension_repr(elem)(elem)


class TreePattern(ABC, Generic[T]):
    __slots__ = 'elems',

    def __init__(self, *elems: TreeElem[T]) -> None:
        if not elems:
            raise ValueError(f"{type(self).__name__} cannot be empty.")
        self.elems: List[TreeElem[T]] = list(elems)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TreePattern):
            return NotImplemented
        zipped = zip_longest(self.elems, other.elems, fillvalue=None)
        return type(self) is type(other) and all(tree_elem_equals(i, j) for i, j in zipped)

    def __len__(self) -> int:
        return len(self.elems)

    def __iter__(self) -> Iterator[TreeElem[T]]:
        yield from self.elems

    def __getitem__(self, item: int) -> TreeElem[T]:
        return self.elems[item]

    def __setitem__(self, key: int, value: Union[TreeElem[T], Iterable[TreeElem[T]]]) -> None:
        self.elems[key] = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(tree_elem_repr(e) for e in self.elems)})"

    # -- Canonical Normal Form --
    # Let f be a function where:
    #   f(x) = Branch(x)    when x is not a TreePattern
    #   f(x) = x            otherwise
    #
    # Let x, y ∈ TreeElem[T], and let n ∈ ℕ.
    # Let Ta, Tb, ... ∈ TreePattern, and let Fa, Fb, ... ∈ ForkPattern.
    # Then, given concrete TreePattern classes Branch, And, Then and Or, we
    # have rewrite rules:
    #
    #   1) Branch(x1, ..., xn, Branch(y1, ..., yn)) => Branch(x1, ..., xn, y1, ..., yn)
    #   2) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    #   3) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    #   4) Fa(x) => Branch(x)
    #   5) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index == Fb.index V Fa is Or and Fb is Or
    #   6) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    #   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
    #   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
    #
    @abstractmethod
    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> 'TreePattern':
        raise NotImplementedError

    @abstractmethod
    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        raise NotImplementedError


class Branch(TreePattern):
    __slots__ = "id",
    count: int = 0

    def __init__(self, *elems: TreeElem[T]) -> None:
        super().__init__(*elems)
        self.id = f"B{Branch.count}"
        Branch.count += 1
        if any(isinstance(e, TreePattern) for e in elems[:-1]):
            raise ValueError(f'Seq may only contain one BranchPattern '
                             f'at the end of elems; found: {self}')

    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> TreePattern:
        *fst_elems, last = self.elems
        if isinstance(last, TreePattern):
            return last.canonical_nf(index + len(fst_elems), *elems, *fst_elems)
        self.elems[:0] = elems
        return self

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        yield {self.id: self}, self.id, self.id


class ForkPattern(TreePattern, ABC):
    __slots__ = "index",

    def __init__(self, *elems: TreeElem[T]) -> None:
        super().__init__(*elems)
        self.index: int = 0

    @property
    def ord(self) -> Type[Ord]:
        return Partial

    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> TreePattern:
        self.index = index
        includes_or = False
        self_elems = self.elems
        offset = 0
        for i in range(len(self_elems)):
            elem = self_elems[i]
            if isinstance(elem, TreePattern):
                normal = elem.canonical_nf(index, *elems)
                if isinstance(normal, type(self)) and normal.index == self.index:
                    self_elems[offset + i:offset + i + 1] = normal.elems
                    offset += len(normal)
                else:
                    self_elems[offset + i] = normal
                    if isinstance(normal, Or):
                        includes_or = True
            else:
                self_elems[offset + i] = Branch(*elems, elem)
        if len(self_elems) == 1:
            return self_elems[0]
        if includes_or:
            return Or(*self.disjunctive_normalise())
        return self

    def disjunctive_normalise(self) -> Iterator[TreePattern]:
        splat_or = (e.elems if isinstance(e, Or) else [e] for e in self.elems)
        for elems in product(*splat_or):
            new = type(self)(*elems)
            new.index = self.index
            offset = 0
            for i in range(len(new.elems)):
                elem = new.elems[offset + i]
                if isinstance(elem, type(self)) and elem.index == self.index:
                    new.elems[offset + i:offset + i + 1] = elem.elems
                    offset += len(elem)
            yield new

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        alias_iter, sib_iter, ord_iter = zip(*(next(e.to_exprs()) for e in self.elems))
        aliases = {k: v for d in alias_iter for k, v in d.items()}
        sib = Sib(self.index, *sib_iter)
        ord_ = self.ord(*ord_iter)
        yield aliases, sib, ord_


class And(ForkPattern):
    pass


class Then(ForkPattern):
    @property
    def ord(self) -> Type[Ord]:
        return Total


class Or(ForkPattern):
    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> TreePattern:
        self_elems = self.elems
        offset = 0
        for i in range(len(self_elems)):
            elem = self_elems[i]
            if isinstance(elem, TreePattern):
                normal = elem.canonical_nf(index, *elems)
                if isinstance(normal, Or):
                    self_elems[offset + i:offset + i + 1] = normal.elems
                    offset += len(normal)
                else:
                    self_elems[offset + i] = normal
            else:
                self_elems[offset + i] = Branch(*elems, elem)
        if len(self_elems) == 1:
            return self_elems[0]
        return self

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        for elem in self.elems:
            yield from elem.to_exprs()


if __name__ == '__main__':
    aa, ss, oo = (next(Then('A', And('B', 'C')).canonical_nf().to_exprs()))
    print(aa, ss.constraint(), oo, oo.to_dag())
