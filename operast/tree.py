
__all__ = [
    "And",
    "Branch",
    "Fork",
    "Or",
    "Op",
    "Then",
    "TreeElem",
    "Tree",
]

from abc import ABC, abstractmethod
from itertools import product, zip_longest
from operast._ext import get_ext_eq, get_ext_repr
from operast.constraints import Ord, OrdElem, Sib, SibElem, Total, Partial
from operast.operator import Op
from typing import Dict, Generic, Iterator, \
    Tuple, Type, TypeVar, Union, Iterable


T = TypeVar('T')

TreeElem = Union['Tree[T]', Op[T], T]
Aliases = Dict[str, 'Branch[T]']


def tree_elem_eq(a: TreeElem[T], b: TreeElem[T]) -> bool:
    if isinstance(a, (Tree, Op)):
        return a == b
    eq = get_ext_eq(a if isinstance(a, type) else type(a))
    return eq(a, b)


def tree_elem_repr(a: TreeElem[T]) -> str:
    if isinstance(a, (Tree, Op)):
        return repr(a)
    _repr = get_ext_repr(a if isinstance(a, type) else type(a))
    return _repr(a)


class Tree(ABC, list, Generic[T]):
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tree):
            return NotImplemented
        zipped = zip_longest(self, other, fillvalue=None)
        return type(self) is type(other) and all(tree_elem_eq(i, j) for i, j in zipped)

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({', '.join(tree_elem_repr(e) for e in self)})"

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
    #       iff Fa.loc == Fb.loc V Fa is Or and Fb is Or
    #   6) Branch(x1, ..., xn, Fa(y1, ..., yn)) =>
    #       Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    #   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
    #   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
    #
    @abstractmethod
    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> 'Tree[T]':
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        raise NotImplementedError  # pragma: no cover


class Branch(Tree[T]):
    __slots__ = "id",
    count: int = 0

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T]) -> None:
        list.__init__(self, [elem, *elems])
        self.id = f"B{Branch.count}"
        Branch.count += 1
        if any(isinstance(e, Tree) for e in self[:-1]):
            raise ValueError(f'{Branch.__name__} may only contain {Tree.__name__} '
                             f'instances at the end of elems; found: {self}')

    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> Tree[T]:
        *rest, last = self
        if isinstance(last, Tree):
            return last.canonical_nf(loc + len(rest), *elems, *rest)
        self[:0] = elems
        return self

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        yield {self.id: self}, self.id, self.id


FT = TypeVar('FT', bound='Fork')


def flat(t: Type[FT], elems: Iterable[Tree[T]], loc: int) -> Iterator[Tree[T]]:
    for elem in elems:
        if isinstance(elem, t) and loc == elem.loc:
            yield from elem
        else:
            yield elem


class Fork(Tree[T], ABC):
    __slots__ = "loc",

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T], loc: int = 0) -> None:
        trees = (e if isinstance(e, Tree) else Branch(e) for e in (elem, *elems))
        list.__init__(self, trees)
        self.loc: int = loc

    @property
    def order(self) -> Type[Ord]:
        return Partial

    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> Tree[T]:
        if len(self) == 1:
            return self[0].canonical_nf(loc, *elems)
        norms = (e.canonical_nf(loc, *elems) for e in self)
        new = type(self)(*flat(type(self), norms, loc), loc=loc)
        if any(isinstance(e, Or) for e in new):
            return Or(*new._disjunctive_normalise(loc))
        return new

    def _disjunctive_normalise(self, loc: int) -> Iterator[Tree[T]]:
        splat_or = (e if isinstance(e, Or) else [e] for e in self)
        for elems in product(*splat_or):
            yield type(self)(*flat(type(self), elems, loc), loc=loc)

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        # The call to next may be used blindly since after canonical_nf has
        # been called, the elems of And and Then will only include Branch, And
        # and Then, each of which only ever yields a single tuple.
        alias_iter, sib_iter, ord_iter = zip(*(next(e.to_exprs()) for e in self))
        aliases = dict(t for d in alias_iter for t in d.items())
        sib = Sib(self.loc, *sib_iter)
        order = self.order(*ord_iter)
        yield aliases, sib, order


class And(Fork[T]):
    pass


class Then(Fork[T]):
    @property
    def order(self) -> Type[Ord]:
        return Total


class Or(Fork[T]):
    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> Tree[T]:
        norms = (e.canonical_nf(loc, *elems) for e in self)
        return next(norms) if len(self) == 1 else Or(*flat(Or, norms, 0))

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        for elem in self:
            yield from elem.to_exprs()
