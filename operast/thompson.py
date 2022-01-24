
__all__ = [
    "Inst",
    "Unit",
    "UnitList",
    "AnyUnit",
    "UnitEq",
    "Match",
    "Jump",
    "Split",
    "thompson_vm"
]

from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar


T = TypeVar('T')

UnitEq = Callable[[T, T], bool]


class Inst(Generic[T]):
    pass


@dataclass
class Unit(Inst[T]):
    __slots__ = "unit",
    unit: T


@dataclass
class UnitList(Inst[T]):
    __slots__ = "units",
    units: List[T]


@dataclass
class AnyUnit(Inst[T]):
    pass


@dataclass
class Match(Inst[T]):
    pass


@dataclass
class Jump(Inst[T]):
    __slots__ = "goto",
    goto: int


@dataclass
class Split(Inst[T]):
    __slots__ = "goto_x", "goto_y"
    goto_x: int
    goto_y: int


__NO_MATCH = object()


# why not implement a JIT compiler that produces super-ops which reduce the
# number of epsilon transitions as much as possible.
def thompson_vm(program: List[Inst[T]], sequence: List[T], ident: UnitEq) -> bool:
    c_list: List[int] = [0]

    for item in [*sequence, __NO_MATCH]:
        n_list: List[int] = []
        for program_counter in c_list:
            inst = program[program_counter]
            if isinstance(inst, Unit):
                if item is __NO_MATCH or not ident(item, inst.unit):
                    continue
                n_list.append(program_counter + 1)
            elif isinstance(inst, UnitList):
                if item is __NO_MATCH or not any(ident(item, u) for u in inst.units):
                    continue
                n_list.append(program_counter + 1)
            elif isinstance(inst, AnyUnit):
                n_list.append(program_counter + 1)
            elif isinstance(inst, Match):
                return True
            elif isinstance(inst, Jump):
                c_list.append(inst.goto)
            elif isinstance(inst, Split):
                c_list.extend([inst.goto_x, inst.goto_y])
            else:  # pragma: no cover
                raise ValueError('Unreachable!')

        c_list = n_list

    return False
