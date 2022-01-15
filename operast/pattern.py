
__all__ = [
    "__EXTENSIONS",
    "EXT_EQUALS",
    "EXT_REPR",
    "And",
    "Branch",
    "Fork",
    "Or",
    "Operator",
    "Then",
    "TreeElem",
    "Tree",
]

from abc import ABC, abstractmethod
from functools import lru_cache
from itertools import product, zip_longest
from operast.constraints import Ord, OrdElem, Sib, SibElem, Total, Partial
from typing import Callable, Dict, Generic, Iterator, \
    Optional, Tuple, Type, TypeVar, Union, Iterable

T = TypeVar('T')


class Operator(Generic[T]):
    __slots__ = "elem", "_cls"

    def __init__(self, elem: T):
        self.elem = elem
        self._cls = elem if isinstance(elem, type) else type(elem)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        method = get_ext_method(self._cls, EXT_EQUALS, self._cls.__eq__)
        return method(self.elem, other.elem)

    def __repr__(self) -> str:  # pragma: no cover
        method = get_ext_method(self._cls, EXT_REPR, self._cls.__repr__)
        elem_repr = method(self.elem)
        return f'{type(self).__name__}({elem_repr})'


TreeElem = Union['Tree[T]', Operator[T], T]
Aliases = Dict[str, 'Branch[T]']


EXT_EQUALS = 'te_equals'
EXT_REPR = 'te_repr'


__EXTENSIONS: Dict[type, Dict[str, Callable]] = {}


def _extension_type(_cls: type) -> Optional[Dict[str, Callable]]:
    if _cls in __EXTENSIONS:
        return __EXTENSIONS[_cls]
    for typ in __EXTENSIONS:
        if issubclass(_cls, typ):
            return __EXTENSIONS[typ]
    return None


@lru_cache(maxsize=None)
def get_ext_method(_cls: Type[T], method: str, default: Callable) -> Callable:
    func: Callable = getattr(_cls, method, None)
    if func is None:
        method_dict = _extension_type(_cls)
        if method_dict is not None:
            func = method_dict[method]
    if func is None:
        func = default
    return func


def tree_elem_equals(elem_a: TreeElem[T], elem_b: TreeElem[T]) -> bool:
    if isinstance(elem_a, (Tree, Operator)):
        return elem_a == elem_b
    _cls = elem_a if isinstance(elem_a, type) else type(elem_a)
    return get_ext_method(_cls, EXT_EQUALS, _cls.__eq__)(elem_a, elem_b)


def tree_elem_repr(elem: TreeElem[T]) -> str:
    if isinstance(elem, (Tree, Operator)):
        return repr(elem)
    _cls = elem if isinstance(elem, type) else type(elem)
    return get_ext_method(_cls, EXT_REPR, _cls.__repr__)(elem)


class Tree(list, ABC, Generic[T]):
    __slots__ = 'elems',

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tree):
            return NotImplemented
        zipped = zip_longest(self, other, fillvalue=None)
        return type(self) is type(other) and all(tree_elem_equals(i, j) for i, j in zipped)

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
    #       iff Fa.index == Fb.index V Fa is Or and Fb is Or
    #   6) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    #   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
    #   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
    #
    @abstractmethod
    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> 'Tree[T]':
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
            raise ValueError(f'{Branch.__name__} may only contain one '
                             f'{Tree.__name__} at the end of '
                             f'elems; found: {repr(self)}')

    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> Tree[T]:
        *fst_elems, last = self
        if isinstance(last, Tree):
            return last.canonical_nf(index + len(fst_elems), *elems, *fst_elems)
        self[:0] = elems
        return self

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        yield {self.id: self}, self.id, self.id


class Fork(Tree[T], ABC):
    __slots__ = "index",

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T], index: int = 0) -> None:
        trees = [e if isinstance(e, Tree) else Branch(e) for e in (elem, *elems)]
        list.__init__(self, trees)
        self.index: int = index

    @property
    def ord(self) -> Type[Ord]:
        return Partial

    def flatten(self, elems: Iterable[Tree[T]], index: int) -> Iterator[Tree[T]]:
        for elem in elems:
            if isinstance(elem, type(self)) and index == elem.index:
                yield from elem
            else:
                yield elem

    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> Tree[T]:
        if len(self) == 1:
            return self[0].canonical_nf(index, *elems)
        es = (e.canonical_nf(index, *elems) for e in self)
        new = type(self)(*self.flatten(es, index), index=index)
        if any(isinstance(e, Or) for e in new):
            return Or(*new.disjunctive_normalise())
        return new

    def disjunctive_normalise(self) -> Iterator[Tree[T]]:
        splat_or = (e if isinstance(e, Or) else [e] for e in self)
        for elems in product(*splat_or):
            yield type(self)(*self.flatten(elems, self.index), index=self.index)

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        # The call to next may be used blindly since after canonical_nf has
        # been called, the elems of And and Then will only include Branch, And
        # and Then, each of which only ever yields a single tuple.
        alias_iter, sib_iter, ord_iter = zip(*(next(e.to_exprs()) for e in self))
        aliases = {k: v for d in alias_iter for k, v in d.items()}
        sib = Sib(self.index, *sib_iter)
        ord_ = self.ord(*ord_iter)
        yield aliases, sib, ord_


class And(Fork[T]):
    pass


class Then(Fork[T]):
    @property
    def ord(self) -> Type[Ord]:
        return Total


class Or(Fork[T]):
    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T]) -> None:
        super().__init__(elem, *elems, index=0)  # or index is always 0

    def canonical_nf(self, index: int = 0, *elems: TreeElem[T]) -> Tree[T]:
        if len(self) == 1:
            return self[0].canonical_nf(index, *elems)
        es = (e.canonical_nf(index, *elems) for e in self)
        return Or(*self.flatten(es, self.index))

    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        for elem in self:
            yield from elem.to_exprs()
