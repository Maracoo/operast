
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
    "compile_regex"
]

from abc import ABC, abstractmethod
from dataclasses import dataclass
from operast._ext import get_ext_eq, get_ext_repr
from operast.thompson import *
from typing import Generic, Iterable, Iterator, List, TypeVar, Union

T = TypeVar('T')


class ProgramCounter:
    __slots__ = "_val",

    def __init__(self) -> None:
        self._val = 0

    @property
    def val(self) -> int:  # Use property to avoid accidental assigns to val
        return self._val

    def inc(self) -> None:
        self._val += 1


class Op(ABC, Generic[T]):
    @abstractmethod
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        raise NotImplementedError  # pragma: no cover


OpElem = Union[T, Op[T]]


def op_elem_eq(a: OpElem[T], b: OpElem[T]) -> bool:
    if isinstance(a, Op):
        return a == b
    return get_ext_eq(a if isinstance(a, type) else type(a))(a, b)


def op_elem_repr(a: OpElem[T]) -> str:  # pragma: no cover
    if isinstance(a, Op):
        return repr(a)
    return get_ext_repr(a if isinstance(a, type) else type(a))(a)


def compile_elements(es: Iterable[OpElem[T]], pc: ProgramCounter) -> Iterator[Inst]:
    for e in es:
        if isinstance(e, Op):
            yield from e.compile(pc)
        else:
            pc.inc()  # The only location where we increment pc for Unit
            yield Unit(e)


class Quantifier(Op[T], ABC):
    __slots__ = "elems", "greedy"

    def __init__(self, e: OpElem, *es: OpElem, greedy: bool = True) -> None:
        self.elems: List[OpElem] = [e, *es]
        self.greedy: bool = greedy

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return (all(op_elem_eq(a, b) for a, b in zip(self.elems, other.elems))
                and self.greedy == other.greedy)

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ', '.join(op_elem_repr(a) for a in self.elems)
        return f"{type(self).__name__}({elems_repr}, greedy={self.greedy})"


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
            split.t2 = pc.val
        else:
            split.t1 = pc.val
        yield Jump(start)


class QMark(Quantifier[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self.elems, pc)
        if self.greedy:
            split.t2 = pc.val
        else:
            split.t1 = pc.val


@dataclass(eq=False, repr=False)
class Alt(Op[T]):
    __slots__ = "left", "right"
    left: List[OpElem[T]]
    right: List[OpElem[T]]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Alt):
            return NotImplemented
        all_left = all(op_elem_eq(a, b) for a, b in zip(self.left, other.left))
        all_right = all(op_elem_eq(a, b) for a, b in zip(self.right, other.right))
        return all_left and all_right

    def __repr__(self) -> str:  # pragma: no cover
        left_repr = ', '.join(op_elem_repr(a) for a in self.left)
        right_repr = ', '.join(op_elem_repr(a) for a in self.right)
        return f"{Alt.__name__}([{left_repr}], [{right_repr}])"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
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
    __slots__ = "elems",

    def __init__(self, e: T, *es: T) -> None:
        self.elems: List[T] = [e, *es]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all(op_elem_eq(a, b) for a, b in zip(self.elems, other.elems))

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ', '.join(op_elem_repr(a) for a in self.elems)
        return f"{type(self).__name__}({elems_repr})"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()
        yield UnitList(self.elems)


@dataclass
class Dot(Op[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()
        yield AnyUnit()


class Repeat(Op[T]):
    __slots__ = "count", "elems"

    def __init__(self, e: OpElem, *es: OpElem, count: int = 1) -> None:
        self.count: int = count
        self.elems: List[OpElem] = [e, *es]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return (all(op_elem_eq(a, b) for a, b in zip(self.elems, other.elems))
                and self.count == other.count)

    def __repr__(self) -> str:  # pragma: no cover
        elems_repr = ', '.join(op_elem_repr(a) for a in self.elems)
        return f"{type(self).__name__}({elems_repr}, count={self.count})"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        for _ in range(self.count):
            yield from compile_elements(self.elems, pc)


def compile_regex(seq: Iterable[OpElem[T]]) -> List[Inst]:
    return [*compile_elements(seq, ProgramCounter()), Match()]
