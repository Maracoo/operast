
__all__ = [
    "__EXTENSIONS",
    "EXT_EQUALS",
    "EXT_REPR",
    "And",
    "Branch",
    "Or",
    "Operator",
    "Then",
    "TreeElem",
    "TreePattern",
]

from abc import ABC, abstractmethod
from functools import lru_cache
from itertools import product, zip_longest
from operast.constraints import Ord, OrdElem, Sib, SibElem, Total, Partial
from typing import Callable, Dict, Generic, Iterator, \
    List, Optional, Tuple, Type, TypeVar, Union

T = TypeVar('T')


class Operator(Generic[T]):
    __slots__ = "elem", "_cls"

    def __init__(self, elem: T):
        self.elem = elem
        self._cls = elem if isinstance(elem, type) else type(elem)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Operator):
            return NotImplemented
        method = get_ext_method(self._cls, EXT_EQUALS, self._cls.__eq__)
        return method(self.elem, other.elem)

    def __repr__(self) -> str:  # pragma: no cover
        method = get_ext_method(self._cls, EXT_REPR, self._cls.__repr__)
        elem_repr = method(self.elem)
        return f'{type(self).__name__}({elem_repr})'


TreeElem = Union['TreePattern', Operator, T]
Aliases = Dict[str, 'Branch']


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
    if isinstance(elem_a, (TreePattern, Operator)):
        return elem_a == elem_b
    _cls = elem_a if isinstance(elem_a, type) else type(elem_a)
    return get_ext_method(_cls, EXT_EQUALS, _cls.__eq__)(elem_a, elem_b)


def tree_elem_repr(elem: TreeElem[T]) -> str:
    if isinstance(elem, (TreePattern, Operator)):
        return repr(elem)
    _cls = elem if isinstance(elem, type) else type(elem)
    return get_ext_method(_cls, EXT_REPR, _cls.__repr__)(elem)


class TreePattern(ABC, Generic[T]):
    __slots__ = 'elems',

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T]) -> None:
        self.elems: List[TreeElem[T]] = [elem, *elems]

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

    def __setitem__(self, key: int, value: TreeElem[T]) -> None:
        self.elems[key] = value

    def __repr__(self) -> str:  # pragma: no cover
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
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def to_exprs(self) -> Iterator[Tuple[Aliases, SibElem, OrdElem]]:
        raise NotImplementedError  # pragma: no cover


class Branch(TreePattern):
    __slots__ = "id",
    count: int = 0

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T]) -> None:
        super().__init__(elem, *elems)
        self.id = f"B{Branch.count}"
        Branch.count += 1
        if any(isinstance(e, TreePattern) for e in self.elems[:-1]):
            raise ValueError(f'{Branch.__name__} may only contain one '
                             f'{TreePattern.__name__} at the end of '
                             f'elems; found: {repr(self)}')

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

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T]) -> None:
        super().__init__(elem, *elems)
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
        # The call to next may be used blindly since after canonical_nf has
        # been called, the elems of And and Then will only include Branch, And
        # and Then, each of which only ever yields a single tuple.
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
