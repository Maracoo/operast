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
    "compile_regex",
]

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from itertools import zip_longest
from operast._ext import get_ext_eq, get_ext_repr
from operast.thompson import AnyUnit, Inst, Jump, Match, Split, Unit, UnitList
from typing import Generic, TypeVar

T = TypeVar("T")


class ProgramCounter:
    __slots__ = ("_val",)

    def __init__(self) -> None:
        self._val = 0

    @property
    def val(self) -> int:  # Use property to avoid accidental assigns to val
        return self._val

    def inc(self) -> None:
        self._val += 1


class Op(ABC, Generic[T]):
    @abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        raise NotImplementedError  # pragma: no cover


OpElem = T | Op[T]


def op_elem_eq(a: OpElem[T], b: OpElem[T]) -> bool:
    if isinstance(a, Op):
        return a == b
    eq = get_ext_eq(a if isinstance(a, type) else type(a))
    return eq(a, b)


def op_elems_eq(es1: Iterable[OpElem[T]], es2: Iterable[OpElem[T]]) -> bool:
    return all(op_elem_eq(a, b) for a, b in zip_longest(es1, es2, fillvalue=None))


def op_elem_repr(a: OpElem[T]) -> str:  # pragma: no cover
    if isinstance(a, Op):
        return repr(a)
    _repr = get_ext_repr(a if isinstance(a, type) else type(a))
    return _repr(a)


def compile_elements(es: Iterable[OpElem[T]], pc: ProgramCounter) -> Iterator[Inst[T]]:
    for e in es:
        if isinstance(e, Op):
            yield from e.compile(pc)
        else:
            pc.inc()  # The only location where we increment pc for Unit
            yield Unit(e)


class Quantifier(Op[T], ABC):
    __slots__ = "elems", "greedy"

    def __init__(self, e: OpElem, *es: OpElem, greedy: bool = True) -> None:
        self.elems: list[OpElem] = [e, *es]
        self.greedy: bool = greedy

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return op_elems_eq(self.elems, other.elems) and self.greedy == other.greedy

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ", ".join(op_elem_repr(a) for a in self.elems)
        return f"{type(self).__name__}({elems_repr}, greedy={self.greedy})"


class Plus(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        start = pc.val
        yield from compile_elements(self.elems, pc)
        pc.inc()  # increment for split
        if self.greedy:
            yield Split(start, pc.val)
        else:
            yield Split(pc.val, start)


class Star(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        start = pc.val
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.elems, pc)
        pc.inc()  # increment for jump
        if self.greedy:
            split.t2 = pc.val
        else:
            split.t1 = pc.val
        yield Jump(start)


class QMark(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.elems, pc)
        if self.greedy:
            split.t2 = pc.val
        else:
            split.t1 = pc.val


class Alt(Op[T]):
    __slots__ = "left", "right"

    def __init__(self, left: list[OpElem[T]], right: list[OpElem[T]]) -> None:
        self.left = left
        self.right = right

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Alt):
            return NotImplemented
        return op_elems_eq(self.left, other.left) and op_elems_eq(
            self.right, other.right
        )

    def __repr__(self) -> str:  # pragma: no cover
        left_repr = ", ".join(op_elem_repr(a) for a in self.left)
        right_repr = ", ".join(op_elem_repr(a) for a in self.right)
        return f"{Alt.__name__}([{left_repr}], [{right_repr}])"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.left, pc)
        pc.inc()  # increment for jump
        jump = Jump(pc.val)
        yield jump
        split.t2 = pc.val
        yield from compile_elements(self.right, pc)
        jump.goto = pc.val


class Lst(Op[T]):
    __slots__ = ("elems",)

    def __init__(self, e: T, *es: T) -> None:
        self.elems: list[T] = [e, *es]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Lst):
            return NotImplemented
        return op_elems_eq(self.elems, other.elems)

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ", ".join(op_elem_repr(a) for a in self.elems)
        return f"{type(self).__name__}({elems_repr})"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        pc.inc()
        yield UnitList(self.elems)


class Dot(Op[T]):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dot)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{Dot.__name__}()"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        pc.inc()
        yield AnyUnit()


class Repeat(Op[T]):
    __slots__ = "count", "elems"

    def __init__(self, e: OpElem, *es: OpElem, count: int = 1) -> None:
        self.count: int = count
        self.elems: list[OpElem] = [e, *es]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Repeat):
            return NotImplemented
        return op_elems_eq(self.elems, other.elems) and self.count == other.count

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ", ".join(op_elem_repr(a) for a in self.elems)
        return f"{type(self).__name__}({elems_repr}, count={self.count})"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst[T]]:
        for _ in range(self.count):
            yield from compile_elements(self.elems, pc)


def compile_regex(seq: Iterable[OpElem[T]]) -> list[Inst[T]]:
    return [*compile_elements(seq, ProgramCounter()), Match()]
