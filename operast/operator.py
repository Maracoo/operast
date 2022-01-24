
__all__ = ["Op", "Repetition", "Plus", "Star", "QMark", "Alt", "Lst", "Dot", "compile_regex"]

from abc import ABC, abstractmethod
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
    def val(self) -> int:  # Make property to avoid accidental assigns to val
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


class Op(ABC, list, Generic[T]):
    def __init__(self, e: OpElem, *es: OpElem) -> None:
        list.__init__(self, [e, *es])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all(op_elem_eq(a, b) for a, b in zip(self, other))

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({', '.join(op_elem_repr(a) for a in self)})"

    @abstractmethod
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        raise NotImplementedError


class Repetition(Op[T], ABC):
    __slots__ = "greedy",

    def __init__(self, e: OpElem, *es: OpElem, greedy: bool = True) -> None:
        self.greedy: bool = greedy
        super().__init__(e, *es)


class Plus(Repetition[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        start = pc.val
        yield from compile_elements(self, pc)
        pc.inc()  # increment for split
        if self.greedy:
            yield Split(start, pc.val)
        else:
            yield Split(pc.val, start)


class Star(Repetition[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        start = pc.val
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self, pc)
        pc.inc()  # increment for jump
        if self.greedy:
            split.goto_y = pc.val
        else:
            split.goto_x = pc.val
        yield Jump(start)


class QMark(Repetition[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()  # increment for split
        split = Split(pc.val, pc.val)
        yield split
        yield from compile_elements(self, pc)
        if self.greedy:
            split.goto_y = pc.val
        else:
            split.goto_x = pc.val


class Alt(Op[T]):
    __slots__ = "left", "right"

    def __init__(self, left: List[OpElem[T]], right: List[OpElem[T]]) -> None:
        self.left = left
        self.right = right
        super().__init__(self, [])  # todo: init intentionally empty, explain why.

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Alt):
            return NotImplemented
        left_zip = zip(self.left, other.left)
        right_zip = zip(self.right, other.right)
        return (all(op_elem_eq(a, b) for a, b in left_zip) and
                all(op_elem_eq(a, b) for a, b in right_zip))

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
        split.goto_y = pc.val
        yield from compile_elements(self.right, pc)
        jump.goto = pc.val


class Lst(Op[T]):
    def __init__(self, e: T, *es: T) -> None:
        super().__init__(e, *es)

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()
        yield UnitList(self)


class Dot(Op[T]):
    def __init__(self):
        super().__init__(None)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dot)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{Dot.__name__}()"

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.inc()
        yield AnyUnit()


class Interval(Op[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pass


def compile_regex(seq: Iterable[OpElem[T]]) -> List[Inst]:
    return [*compile_elements(seq, ProgramCounter()), Match()]
