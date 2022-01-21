from typing import Callable, Generic, List, TypeVar


T = TypeVar('T')


UnitEq = Callable[[T, T], bool]


class Op(Generic[T]):
    pass


class Unit(Op[T]):
    __slots__ = "unit", "goto"

    def __init__(self, unit: T, goto: int) -> None:
        self.unit = unit
        self.goto = goto


class Match(Op[T]):
    pass


class Jump(Op[T]):
    __slots__ = "op",

    def __init__(self, op: int) -> None:
        self.op = op


class Split(Op[T]):
    __slots__ = "op_x", "op_y"

    def __init__(self, x: int, y: int) -> None:
        self.op_x = x
        self.op_y = y


def thompson_vm(program: List[Op[T]], sequence: List[T], ident: UnitEq) -> bool:

    clist = [0]
    nlist = []
    item_counter = 0
    item = sequence[item_counter]

    while clist:
        for op_idx in clist:
            op = program[op_idx]
            if isinstance(op, Unit):
                if not ident(item, op.unit):
                    continue
                nlist.append(op.goto)
            elif isinstance(op, Match):
                return True
            elif isinstance(op, Jump):
                clist.append(op.op)
            elif isinstance(op, Split):
                clist.append(op.op_x)
                clist.append(op.op_y)

        if item_counter < len(sequence):
            item = sequence[item_counter]
            item_counter += 1

        clist = nlist
        nlist = []

    return False


if __name__ == '__main__':
    _program = [Unit('a', 1), Split(0, 2), Unit('b', 3), Split(2, 4), Match()]
    print(thompson_vm(_program, ['a', 'b'], str.__eq__))
