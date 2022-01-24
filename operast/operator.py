
__all__ = ["Op"]

from abc import ABC, abstractmethod
from operast._ext import EXT_EQUALS, EXT_REPR, get_ext_method
from operast.thompson import *
from typing import Generic, Iterable, Iterator, List, TypeVar, Union


T = TypeVar('T')

OpElem = Union[T, 'Operator[T]']


def op_elem_eq(a: OpElem[T], b: OpElem[T]) -> bool:
    if isinstance(a, Op):
        return a == b
    _cls = a if isinstance(a, type) else type(a)
    return get_ext_method(_cls, EXT_EQUALS, _cls.__eq__)(a, b)


def op_elem_repr(a: OpElem[T]) -> str:
    if isinstance(a, Op):
        return repr(a)
    _cls = a if isinstance(a, type) else type(a)
    return get_ext_method(_cls, EXT_REPR, _cls.__repr__)(a)


class ProgramCounter:
    __slots__ = "val",

    def __init__(self):
        self.val = 0


class Op(ABC, list, Generic[T]):
    def __init__(self, e: OpElem, *es: OpElem) -> None:
        list.__init__(self, [e, *es])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return all(op_elem_eq(a, b) for a, b in zip(self, other))

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}({', '.join(op_elem_repr(a) for a in self)})"

    def compile_elements(self, pc: ProgramCounter) -> Iterator[Inst]:
        for e in self:
            if isinstance(e, Op):
                for inst in e.compile(pc):
                    pc.val += 1
                    yield inst
            else:
                pc.val += 1
                yield Unit(e)

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
        yield from self.compile_elements(pc)
        pc.val += 1  # add one for split
        if self.greedy:
            yield Split(start, pc.val)
        else:
            yield Split(pc.val, start)


class Star(Repetition[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        start = pc.val
        pc.val += 1  # add one for split
        split = Split(pc.val, pc.val)
        yield split
        yield from self.compile_elements(pc)
        pc.val += 1  # add one for jump
        if self.greedy:
            split.goto_inst[1] = pc.val
        else:
            split.goto_inst[0] = pc.val
        yield Jump(start)


class QMark(Repetition[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.val += 1  # add one for split
        split = Split(pc.val, pc.val)
        yield split
        yield from self.compile_elements(pc)
        if self.greedy:
            split.goto_inst[1] = pc.val
        else:
            split.goto_inst[0] = pc.val


class Alt(Op[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pass


class Lst(Op[T]):
    def __init__(self, e: T, *es: T) -> None:
        super().__init__(e, *es)

    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.val += 1
        yield UnitList(self)


class Dot(Op[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pc.val += 1
        yield AnyUnit()


class Interval(Op[T]):
    def compile(self, pc: ProgramCounter) -> Iterator[Inst]:
        pass


def unit_or_compile(e: OpElem[T], pc: ProgramCounter) -> Iterator[Inst]:
    if isinstance(e, Op):
        yield from e.compile(pc)
    else:
        pc.val += 1
        yield Unit(e)


def compile_regex(seq: Iterable[OpElem[T]]) -> List[Inst]:
    pc = ProgramCounter()
    instructions = (inst for op in seq for inst in unit_or_compile(op, pc))
    return [*instructions, Match()]


if __name__ == "__main__":
    print(compile_regex(['a', QMark('b'), 'c']))
    print(compile_regex(['a', Star('b'), 'c']))
    print(compile_regex(['a', Plus('b'), 'c']))
    print(compile_regex([Plus('a'), Plus('b')]))
    print(compile_regex(['a', Lst('b', 'c'), 'd']))
