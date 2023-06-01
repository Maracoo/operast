from abc import ABC, abstractmethod
from collections.abc import Iterator
from itertools import zip_longest
from operast._ext import get_ext_eq, get_ext_repr
from operast.thompson import AnyUnit, Instruction
from typing import Final, Generic, TypeAlias, TypeVar

T = TypeVar("T")

TreeElem: TypeAlias = T | "TreeNode[TreeElem[T]]"


def tree_elem_eq(a: TreeElem[T] | None, b: TreeElem[T] | None) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, TreeNode):
        return a == b
    eq = get_ext_eq(a if isinstance(a, type) else type(a))
    return eq(a, b)


def tree_elem_repr(a: TreeElem[T]) -> str:
    if isinstance(a, TreeNode):
        return repr(a)
    _repr = get_ext_repr(a if isinstance(a, type) else type(a))
    return _repr(a)


class ProgramCounter:
    __slots__ = ("_val",)

    def __init__(self) -> None:
        self._val = 0

    @property
    def val(self) -> int:  # Use property to avoid accidental assigns to val
        return self._val

    def inc(self) -> None:
        self._val += 1


class TreeNode(ABC, Generic[T]):
    """Abstract class for all tree nodes."""

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    @abstractmethod
    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> "TreeNode[T]":
        raise NotImplementedError

    @abstractmethod
    def compile(self, pc: ProgramCounter) -> Iterator[Instruction[T]]:
        raise NotImplementedError


class TreeListNode(TreeNode[T], list, ABC):
    """Abstract class for a TreeNode which contains a sequence of elements."""

    def __eq__(self, other: object) -> bool:
        # type identity check implies isinstance(other, TreeElems), hence if the
        # left hand side of the and is true, then `other` must be an instance of
        # TreeElems, and thus must be iterable, which justifies the use of zip_longest.
        return type(self) is type(other) and all(
            tree_elem_eq(i, j) for i, j in zip_longest(self, other, fillvalue=None)  # type: ignore[call-overload] # noqa: E501
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(tree_elem_repr(e) for e in self)})"


class Branch(TreeListNode[T]):
    __slots__ = ("id",)
    id_count: int = 0

    def __init__(self, elem: TreeElem[T], *elems: TreeElem[T]) -> None:
        list.__init__(self, [elem, *elems])
        self.id = f"B{Branch.id_count}"
        Branch.id_count += 1
        if any(isinstance(e, And | Then) for e in self[:-1]):
            msg = (
                f"{Branch.__name__} may only contain {And.__name__} or "
                f"{Then.__name__} instances at the end of elems; found: {self}"
            )
            raise TypeError(msg)

    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> "TreeNode[T]":
        pass

    def compile(self, pc: ProgramCounter) -> Iterator[Instruction[T]]:
        pass


class Fork(TreeListNode[T], ABC):
    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> "TreeNode[T]":
        pass

    def compile(self, pc: ProgramCounter) -> Iterator[Instruction[T]]:
        pass


class And(Fork[T]):
    pass


class Then(Fork[T]):
    pass


class Or(Fork[T]):
    pass


class AnyTag:
    def __eq__(self, other: object) -> bool:
        return isinstance(other, str | AnyTag)


ANY_TAG: Final[AnyTag] = AnyTag()


# todo: every non-tag ast elem should be wrapped in a tag, defaulting to AnyTag
#  when no explicit tag is given.
class Tag(TreeNode[T]):
    __slots__ = "tag", "elem"

    def __init__(self, tag: str | AnyTag, elem: T) -> None:
        self.tag = tag
        self.elem = elem

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return False
        return other.tag == self.tag and tree_elem_eq(self.elem, other.elem)

    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> "TreeNode[T]":
        pass

    def compile(self, pc: ProgramCounter) -> Iterator[Instruction[T]]:
        pass


class Quantifier(TreeListNode[T], ABC):
    __slots__ = ("greedy",)

    def __init__(
        self, elem: TreeElem[T], *elems: TreeElem[T], greedy: bool = True
    ) -> None:
        list.__init__(self, [elem, *elems])
        self.greedy = greedy

    def __eq__(self, other: object) -> bool:
        # If the left hand side of the and is true then "greedy" must be an
        # attribute of `other` because TreeElems.__eq__ includes a check against
        # type(self). Hence it is safe to reference without checking hasattr.
        return TreeListNode.__eq__(self, other) and self.greedy == other.greedy  # type: ignore[attr-defined] # noqa: E501

    def __repr__(self) -> str:
        elems_repr = ", ".join(tree_elem_repr(a) for a in self)
        return f"{type(self).__name__}({elems_repr}, greedy={self.greedy})"


class Plus(Quantifier[T]):
    pass


class Star(Quantifier[T]):
    pass


class QMark(Quantifier[T]):
    pass


class List(TreeListNode[T]):
    def __init__(self, elem: T, *elems: T) -> None:
        list.__init__(self, [elem, *elems])
        if any(isinstance(e, TreeNode) for e in self):
            msg = f"{type(self).__name__} cannot contain tree nodes."
            raise TypeError(msg)

    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> "TreeNode[T]":
        pass

    def compile(self, pc: ProgramCounter) -> Iterator[Instruction[T]]:
        pass


class Dot(TreeNode[T]):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dot)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    # todo: check
    def canonical_nf(self, loc: int = 0, *elems: TreeElem[T]) -> "TreeNode[T]":
        return self

    def compile(self, pc: ProgramCounter) -> Iterator[Instruction[T]]:
        pc.inc()
        yield AnyUnit()


class Repeat(TreeListNode[T]):
    pass
