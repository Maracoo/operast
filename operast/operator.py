
__all__ = [
    "Op",
    "Quantifier",
    "Plus",
    "Star",
    "QMark",
    "Alt",
    "Lst",
    "Dot",
    "Repeat",
    # "Clamp",
    "compile_regex"
]

from abc import ABC, abstractmethod
from dataclasses import dataclass
from operast._ext import get_ext_eq, get_ext_repr
from operast.thompson import *
from typing import Generic, Iterable, Iterator, List, TypeVar, Union

T = TypeVar('T')

OpElem = Union[T, 'Operator[T]']


def op_elem_eq(a: OpElem[T], b: OpElem[T]) -> bool:
    if isinstance(a, Op):
        return a == b
    return get_ext_eq(a if isinstance(a, type) else type(a))(a, b)


def op_elem_repr(a: OpElem[T]) -> str:
    if isinstance(a, Op):
        return repr(a)
    return get_ext_repr(a if isinstance(a, type) else type(a))(a)


class ProgramCounter:
    __slots__ = "_val",

    def __init__(self) -> None:
        self._val = 0

    @property
    def val(self) -> int:  # Use property to avoid accidental assigns to val
        return self._val

    def inc(self) -> None:
        self._val += 1


def compile_elements(es: Iterable[OpElem[T]], pc: ProgramCounter) -> Iterator[Inst]:
    for e in es:
        if isinstance(e, Op):
            yield from e.compile(pc)
        else:
            pc.inc()  # The only location where we increment for Unit
            yield Unit(e)


class Op(ABC, Generic[T]):
    def __ne__(self, other: object) -> bool:
        return not self == other

    @abstractmethod
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        raise NotImplementedError  # pragma: no cover


@dataclass(init=False)
class Quantifier(Op[T], ABC):
    __slots__ = "elems", "greedy"
    elems: List[OpElem]
    greedy: bool

    def __init__(self, e: OpElem, *es: OpElem, greedy: bool = True) -> None:
        self.elems: List[OpElem] = [e, *es]
        self.greedy: bool = greedy


class Plus(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        start = pc.val
        yield from compile_elements(self.elems, pc)
        pc.inc()  # increment for split
        if self.greedy:
            yield Split(start, pc.val)
        else:
            yield Split(pc.val, start)


class Star(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        start = pc.val
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.elems, pc)
        pc.inc()  # increment for jump
        if self.greedy:
            split.goto_y = pc.val
        else:
            split.goto_x = pc.val
        yield Jump(start)


class QMark(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.elems, pc)
        if self.greedy:
            split.goto_y = pc.val
        else:
            split.goto_x = pc.val


@dataclass
class Alt(Op[T]):
    __slots__ = "left", "right"
    left: List[OpElem[T]]
    right: List[OpElem[T]]

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.left, pc)
        pc.inc()  # increment for jump
        jump = Jump(pc.val)
        yield jump
        split.goto_y = pc.val
        yield from compile_elements(self.right, pc)
        jump.goto = pc.val


@dataclass(init=False)
class Lst(Op[T]):
    __slots__ = "elems",
    elems: List[T]

    def __init__(self, e: T, *es: T) -> None:
        self.elems: List[T] = [e, *es]

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()
        yield UnitList(self.elems)


@dataclass
class Dot(Op[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()
        yield AnyUnit()


@dataclass(init=False)
class Repeat(Op[T]):
    __slots__ = "count", "elems"
    count: int
    elems: List[OpElem]

    def __init__(self, e: OpElem, *es: OpElem, count: int) -> None:
        self.count: int = count
        self.elems: List[OpElem] = [e, *es]

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        for _ in range(self.count):
            yield from compile_elements(self.elems, pc)


# @dataclass(init=False)
# class Clamp(Op[T]):
#     __slots__ = "elems", "min", "max"
#     elems: List[OpElem]
#     min: int
#     max: Optional[int]
#
#     def __init__(
#         self,
#         e: OpElem,
#         *es: OpElem,
#         min_: int = 0,
#         max_: Optional[int] = None
#     ) -> None:
#         if isinstance(max_, int) and min_ > max_:
#             raise ValueError(f"min > max: {min_} > {max_}")
#         self.elems: List[OpElem] = [e, *es]
#         self.min: int = min_
#         self.max: Optional[int] = max_
#
#     def diff(self) -> int:
#         abs_max = 0 if self.max is None else self.max
#         return abs(abs_max - self.min)
#
#     def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
#         pass


def compile_regex(seq: Iterable[OpElem[T]]) -> List[Inst]:
    return [*compile_elements(seq, ProgramCounter()), Match()]
