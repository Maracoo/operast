__all__ = [
    "AnyUnit",
    "Instruction",
    "Jump",
    "Match",
    "Split",
    "Unit",
    "UnitList",
    "UnitEq",
    "thompson_vm",
    "vm_step",
]

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")

UnitEq: TypeAlias = Callable[[T, T], bool]


class Instruction(Generic[T]):
    pass


@dataclass
class Unit(Instruction[T]):
    __slots__ = ("e",)
    e: T


@dataclass
class UnitList(Instruction[T]):
    __slots__ = ("ls",)
    ls: list[T]


@dataclass
class AnyUnit(Instruction[T]):
    pass


@dataclass
class Match(Instruction[T]):
    pass


@dataclass
class Jump(Instruction[T]):
    __slots__ = ("goto",)
    goto: int


@dataclass
class Split(Instruction[T]):
    __slots__ = "t1", "t2"
    t1: int
    t2: int


__NO_MATCH = object()


# todo: fix threading
def thompson_vm(program: list[Instruction[T]], sequence: list[T], eq: UnitEq) -> bool:
    c_list: list[int] = [0]
    for item in [*sequence, __NO_MATCH]:
        step = vm_step(program, c_list, item, eq)
        if step is None:
            return True
        if len(step) == 0:
            return False
        c_list = step
    return False


def vm_step(
    program: list[Instruction[T]], c_list: list[int], item: T, eq: UnitEq
) -> list[int] | None:
    n_list: list[int] = []
    for program_counter in c_list:
        inst = program[program_counter]
        if isinstance(inst, Unit):
            if item is __NO_MATCH or not eq(item, inst.e):
                continue
            n_list.append(program_counter + 1)
        elif isinstance(inst, UnitList):
            if item is __NO_MATCH or not any(eq(item, i) for i in inst.ls):
                continue
            n_list.append(program_counter + 1)
        elif isinstance(inst, AnyUnit):
            n_list.append(program_counter + 1)
        elif isinstance(inst, Match):
            return None
        elif isinstance(inst, Jump):
            c_list.append(inst.goto)
        elif isinstance(inst, Split):
            c_list.extend([inst.t1, inst.t2])
        else:  # pragma: no cover
            msg = "Unreachable!"
            raise ValueError(msg)
    return n_list
