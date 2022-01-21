from typing import Callable, Generic, List, TypeVar


T = TypeVar('T')


UnitEq = Callable[[T, T], bool]


class Op(Generic[T]):
    pass


class Unit(Op[T]):
    __slots__ = "unit", "next"

    def __init__(self, unit: T, next_: int) -> None:
        self.unit = unit
        self.next = next_


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


def thompson_vm(program: List[Op[T]], sequence: List[T], ident: UnitEq) -> bool:
    clist = [0]
    nlist = []

    for item in [*sequence, __NO_MATCH]:
        for op_idx in clist:
            op = program[op_idx]
            if isinstance(op, Unit):
                if item is __NO_MATCH or not ident(item, op.unit):
                    continue
                nlist.append(op.next)
            elif isinstance(op, Match):
                return True
            elif isinstance(op, Jump):
                clist.append(op.goto)
            elif isinstance(op, Split):
                clist.extend(op.goto_ops)

        clist = nlist
        nlist = []

    return False


if __name__ == '__main__':
    # program for a+b+
    _program = [Unit('a', 1), Split(0, 2), Unit('b', 3), Split(2, 4), Match()]
    print(thompson_vm(_program, ['a', 'a', 'a', 'a', 'b', 'b', 'b'], str.__eq__))
