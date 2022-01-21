
__all__ = [
    "Op",
    "Unit",
    "UnitClass",
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


class Op(Generic[T]):
    pass


class Unit(Op[T]):
    __slots__ = "unit",

    def __init__(self, unit: T) -> None:
        self.unit = unit


class UnitClass(Op[T]):
    __slots__ = "units",

    def __init__(self, units: List[T]) -> None:
        self.units = units


class AnyUnit(Op[T]):
    pass


class Match(Op[T]):
    pass


class Jump(Op[T]):
    __slots__ = "goto",

    def __init__(self, goto: int) -> None:
        self.goto = goto


class Split(Op[T]):
    __slots__ = "goto_ops",

    def __init__(self, x: int, y: int) -> None:
        self.goto_ops = [x, y]


__NO_MATCH = object()


# why not implement a JIT compiler that produces super-ops which reduce the
# number of epsilon transitions as much as possible.
def thompson_vm(program: List[Op[T]], sequence: List[T], ident: UnitEq) -> bool:
    c_list: List[int] = [0]

    for item in [*sequence, __NO_MATCH]:
        n_list: List[int] = []
        for program_counter in c_list:
            op = program[program_counter]
            if isinstance(op, Unit):
                if item is __NO_MATCH or not ident(item, op.unit):
                    continue
                n_list.append(program_counter + 1)
            elif isinstance(op, UnitClass):
                if item is __NO_MATCH or not any(ident(item, u) for u in op.units):
                    continue
                n_list.append(program_counter + 1)
            elif isinstance(op, AnyUnit):
                n_list.append(program_counter + 1)
            elif isinstance(op, Match):
                return True
            elif isinstance(op, Jump):
                c_list.append(op.goto)
            elif isinstance(op, Split):
                c_list.extend(op.goto_ops)

        c_list = n_list

    return False
