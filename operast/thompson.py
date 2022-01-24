
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

from typing import Callable, Generic, List, TypeVar


T = TypeVar('T')

UnitEq = Callable[[T, T], bool]


class Inst(Generic[T]):
    pass


class Unit(Inst[T]):
    __slots__ = "unit",

    def __init__(self, unit: T) -> None:
        self.unit = unit

    def __repr__(self) -> str:  # pragma: no cover
        return f"Unit({repr(self.unit)})"


class UnitList(Inst[T]):
    __slots__ = "units",

    def __init__(self, units: List[T]) -> None:
        self.units = units

    def __repr__(self) -> str:  # pragma: no cover
        return f"UnitClass({repr(self.units)})"


class AnyUnit(Inst[T]):
    def __repr__(self) -> str:
        return "AnyUnit"


class Match(Inst[T]):
    def __repr__(self) -> str:  # pragma: no cover
        return "Match"


class Jump(Inst[T]):
    __slots__ = "goto",

    def __init__(self, goto: int) -> None:
        self.goto = goto

    def __repr__(self) -> str:  # pragma: no cover
        return f"Jump({self.goto})"


class Split(Inst[T]):
    __slots__ = "goto_inst",

    def __init__(self, x: int, y: int) -> None:
        self.goto_inst = [x, y]

    def __repr__(self) -> str:  # pragma: no cover
        return f"Split({self.goto_inst[0]}, {self.goto_inst[1]})"


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
                c_list.extend(inst.goto_inst)
            else:  # pragma: no cover
                raise ValueError('Unreachable!')

        c_list = n_list

    return False
