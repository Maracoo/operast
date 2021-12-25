import ast
import astpretty
import inspect
from abc import ABC, abstractmethod
from copy import copy
from typing import Any, Dict, Generic, Iterator, List, Optional, Sequence, Set, Tuple, Type, TypeVar, Union, Hashable


K = TypeVar('K', bound=Hashable)
V = TypeVar('V', bound=Hashable)


# noinspection PyProtectedMember
def get_all_ast_fields() -> Set[str]:
    return {field for obj in ast.__dict__.values() if isinstance(obj, type) and
            issubclass(obj, ast.AST) for field in obj._fields}


PY_AST_FIELDS = get_all_ast_fields()


class BiMap(Generic[K, V]):
    # right: mapping K -> V
    # left: mapping K <- V
    def __init__(self, d: Dict[K, V]) -> None:
        left = {}
        for k, v in d.items():
            if v in left:
                raise ValueError(f'Cannot map value {v} to multiple keys: {k}, {left[v]}')
            left[v] = k
        self._right = copy(d)
        self._left = left

    @property
    def right(self) -> Dict[K, V]:
        return self._right

    @property
    def left(self) -> Dict[V, K]:
        return self._left

    def __setitem__(self, key: K, value: V) -> None:
        self._right[key] = value
        self._left[value] = key

    def get_r(self, key: K) -> Optional[V]:
        return self._right.get(key)

    def get_l(self, key: V) -> Optional[K]:
        return self._left.get(key)

    def update_r(self, other: Union['BiMap[K, V]', Dict[K, V]]) -> None:
        update = other.right if isinstance(other, BiMap) else other
        self._right.update(update)
        self._left = {v: k for k, v in self._right.items()}

    def update_l(self, other: Union['BiMap[K, V]', Dict[V, K]]) -> None:
        update = other.left if isinstance(other, BiMap) else other
        self._left.update(update)
        self._right = {v: k for k, v in self._left.items()}


class StateEff:
    def __init__(self, node: Union[ast.AST, Type[ast.AST]]):
        self.node = node

    def __repr__(self) -> str:
        return f'{type(self).__name__}({branch_repr(self.node)})'


BranchIndex = Tuple[int, ...]


class Term:
    def __init__(self, name: str, value: Optional['Seq'] = None):
        self.name = name
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.value == other.value


SibElem = Union[Term, 'Sibling']


class Sibling:
    def __init__(self, index: int, *elems: SibElem):
        self.index = index
        self.elems = list(elems)

    def __getitem__(self, item: int) -> SibElem:
        return self.elems[item]

    def __setitem__(self, key: int, value: SibElem) -> None:
        self.elems[key] = value

    # Rules:
    #   1) Sib(x, A, B) -> [Sib(x, A, B)]
    #   2) Sib(x, A, Sib(y, B, C)) -> [Sib(x, A, B), Sib(y, B, C)]
    #   3) Sib(x, Sib(y, A, B), C) -> [Sib(x, A, C), Sib(y, A, B)]
    def flatten(self) -> List['Sibling']:
        ret = [self]
        for i in range(len(self.elems)):
            if isinstance(self[i], Term):
                continue
            flattened = self[i].flatten()
            ret.extend(flattened)
            self[i] = flattened[0][0]
        return ret


class Node:
    def __init__(self, term: Term):
        self.term = term
        self.children: List[Node] = []

    def __repr__(self) -> str:
        if self.children:
            children_repr = ', '.join(repr(c) for c in self.children)
            return f"Node('{self.term.name}', children=[{children_repr}])"
        return f"Node('{self.term.name}')"

    def add_children(self, children: List['Node']) -> None:
        self.children.extend(children)


OrdElem = Union[Term, 'Ordered', List[Union[Term, 'Ordered']]]


class Ordered:
    def __init__(self, *elems: OrdElem):
        self.elems = elems

    def __getitem__(self, item: int) -> OrdElem:
        return self.elems[item]

    # Rules:
    #   1) Ord(A, B) => A -> B
    #   2) Ord(A, [B, C]) => A -> B, A -> C
    #   3) Ord([A, B], C) => A -> C, B -> C
    #   4) Ord(A, [Ord(B, C), D]) => A -> B -> C, A -> D
    #   5) Ord([A, Ord(B, C)], D) => A -> D, B -> C -> D
    #   6) Ord(A, [Ord([B, C], D), E]) => Ord(A, [B -> D, C -> D, E]) => A -> B -> D, A -> C -> D, A -> E
    def graph(self) -> Tuple[List[Node], List[Node]]:
        first: List[Node] = []
        last: List[Node] = []

        for elem in self.elems:
            if isinstance(elem, Term):
                node = Node(elem)
                new_first, new_last = [node], [node]
            elif isinstance(elem, Ordered):
                new_first, new_last = elem.graph()
            elif isinstance(elem, list):
                new_first, new_last = [], []
                for sub_e in elem:
                    if isinstance(sub_e, Term):
                        node = Node(sub_e)
                        new_first.append(node)
                        new_last.append(node)
                    else:
                        _fst, _lst = sub_e.graph()
                        new_first.extend(_fst)
                        new_last.extend(_lst)
            else:
                raise ValueError('Unreachable')
            if not first:
                first = new_first
            for node in last:
                node.add_children(new_first)
            last = new_last
        return first, last


class Conjunction:
    def __init__(self, *elems: Union[Term, Sibling, Ordered]):
        self.elems = elems


class Disjunction:
    def __init__(self, terms: BiMap[str, Term], *elems: Conjunction):
        self.terms = terms
        self.elems = elems


PatternElem = Union[
    ast.AST, Type[ast.AST], StateEff,
    Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
]
BranchElem = Union['TreePattern', PatternElem]
BranchExpr = Union[str, List['BranchExpr']]
Aliases = Dict[int, 'Seq']


def iter_child_names_nodes(node: ast.AST) -> Iterator[Tuple[str, ast.AST]]:
    """
    Yield all pairs of (field name, child node) for direct children of *node*.
    I.e., all field names and values where the values are nodes and all items
    of fields that are lists of nodes paired with the name of that field.

    An extension of the std lib ast.iter_child_nodes function.
    """
    for name, field in ast.iter_fields(node):
        if isinstance(field, ast.AST):
            yield name, field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, ast.AST):
                    yield name, item


def iter_all_fields(node: ast.AST) -> Iterator[Tuple[str, Any]]:
    for field in PY_AST_FIELDS:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def expand_cases(name: str, elem: Any) -> Optional[BranchElem]:
    # case: ast.AST
    if isinstance(elem, ast.AST):
        pat = node_expand(elem)
        return (name, elem) if pat is None else Seq((name, elem), pat)
    # case: Type[ast.AST]
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return name, elem
    # case: BranchPattern
    if isinstance(elem, TreePattern):
        return elem.pushdown_fieldname(name).expand()
    # case: StateEff
    if isinstance(elem, StateEff):
        return name, elem
    return None


def node_expand(node: ast.AST) -> Optional['TreePattern']:
    # possible elements inside the fields of an AST node:
    # ast.AST, Type[ast.AST], BranchPattern
    and_elements = []
    for name, field in iter_all_fields(node):
        if isinstance(field, list):
            then_elements = []
            non_expand_elements = []
            for item in field:
                expanded = expand_cases(name, item)
                if expanded is None:
                    non_expand_elements.append(item)
                else:
                    then_elements.append(expanded)

            if then_elements:
                and_elements.append(Then(*then_elements))
                if non_expand_elements:
                    setattr(node, name, non_expand_elements)
                else:
                    delattr(node, name)
        else:
            expanded = expand_cases(name, field)
            if expanded is not None:
                and_elements.append(expanded)
                delattr(node, name)

    if and_elements:
        return And(*and_elements)
    return None


def branch_expand(elem: BranchElem) -> BranchElem:
    # case: Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
    if isinstance(elem, tuple):
        name, node = elem
        expanded = branch_expand(node)
        if isinstance(expanded, TreePattern):
            return expanded.pushdown_fieldname(name)
        return name, expanded
    # case: ast.AST
    if isinstance(elem, ast.AST):
        pat = node_expand(elem)
        return elem if pat is None else Seq(elem, pat)
    # case: Type[ast.AST]
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return elem
    # case: StateEff
    if isinstance(elem, StateEff):
        return elem
    # case: BranchPattern
    if isinstance(elem, TreePattern):
        return elem.expand()


def node_pattern_equals(a: ast.AST, b: ast.AST) -> bool:
    return (type(a) is type(b) and len(a.__dict__) == len(b.__dict__) and
            all(i == j for i, j in zip(iter_all_fields(a), iter_all_fields(b))))


def pattern_equals(a: PatternElem, b: PatternElem) -> bool:
    # case: Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
    if isinstance(a, tuple) and isinstance(b, tuple):
        (label_a, elem_a), (label_b, elem_b) = a, b
        return label_a == label_b and pattern_equals(elem_a, elem_b)
    # case: ast.AST
    if isinstance(a, ast.AST) and isinstance(b, ast.AST):
        return node_pattern_equals(a, b)
    # case: Type[ast.AST]
    if isinstance(a, type) and isinstance(b, type):
        return a is b
    # case: StateEff
    if isinstance(a, StateEff) and isinstance(b, StateEff):
        return node_pattern_equals(a.node, b.node)
    return False


def branch_equals(a: BranchElem, b: BranchElem) -> bool:
    if isinstance(a, TreePattern):
        return (type(a) is type(b) and len(a) == len(b) and
                all(branch_equals(i, j) for i, j in zip(a, b)))
    return pattern_equals(a, b)


def ast_repr(node: ast.AST) -> str:
    field_reprs = ', '.join(f'{f}={repr(v)}' for f, v in iter_all_fields(node))
    return f'{type(node).__name__}({field_reprs})'


def branch_repr(a: BranchElem) -> str:
    if isinstance(a, TreePattern) or isinstance(a, StateEff):
        return repr(a)
    if isinstance(a, tuple):
        label, elem = a
        return f"('{label}', {branch_repr(elem)})"
    if isinstance(a, ast.AST):
        return ast_repr(a)
    if isinstance(a, type):
        return a.__name__
    return ''


class TreePattern(ABC):
    __slots__ = 'elems',

    def __init__(self, *elems: BranchElem) -> None:
        if not elems:
            raise ValueError(f"{type(self).__name__} cannot be empty.")
        self.elems = elems

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TreePattern) and branch_equals(self, other)

    def __len__(self) -> int:
        return len(self.elems)

    def __iter__(self) -> Iterator[BranchElem]:
        yield from self.elems

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(branch_repr(e) for e in self.elems)})"

    # First normal form is reached by applying the following rewrite rules:
    #   1) BP(x1, ..., xn, BP(y1, ..., yn)) -> BP(x1, ..., xn, y1, ..., yn)
    #   for all BP in {Seq, And, Then, Or}
    #   2) BP(x1, ..., xn) -> BP(S(x1), ..., S(xn)) for all BP in {And, Then, Or}
    #   where S: x if x is in {Seq, And, Then, Or}, Seq(x) otherwise
    #   3) BP(x1) -> Seq(x1) for all BP in {And, Then, Or}
    @abstractmethod
    def first_normal(self) -> 'TreePattern':
        raise NotImplementedError

    # Second normal form is reached by applying all 1st NF rules plus the
    # following rewrite rules:
    #   1) Seq(x1, ..., xn, BP(y1, ..., yn)) -> BP(Seq(x1, ..., xn, y1), ..., Seq(x1, ..., xn, yn))
    #   for all BP in {And, Then, Or}
    @abstractmethod
    def second_normal(self, index: int = 0, *elems: PatternElem) -> 'TreePattern':
        raise NotImplementedError

    @abstractmethod
    def pushdown_fieldname(self, name: str) -> 'TreePattern':
        raise NotImplementedError

    @abstractmethod
    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        raise NotImplementedError

    def expand(self) -> 'TreePattern':
        return type(self)(*(branch_expand(e) for e in self.elems))


# Seq is a kind of branch pattern
class Seq(TreePattern):
    def __init__(self, *elems: BranchElem) -> None:
        super().__init__(*elems)
        if any(isinstance(e, TreePattern) for e in elems[:-1]):
            raise ValueError(f'Seq may only contain one BranchPattern '
                             f'at the end of elems; found: {self}')

    def __hash__(self) -> int:
        if not self.simple():
            raise ValueError('Cannot hash complex Seq')
        return self.elems.__hash__()

    def simple(self) -> bool:
        return not isinstance(self.elems[-1], TreePattern)

    def first_normal(self) -> 'TreePattern':
        *seq_elems, last = self.elems
        if isinstance(last, TreePattern):
            normal = last.first_normal()
            if isinstance(normal, Seq):
                return Seq(*seq_elems, *normal.elems)
            return Seq(*seq_elems, normal)
        return self

    def second_normal(self, index: int = 0, *elems: PatternElem) -> 'TreePattern':
        *seq_elems, last = self.elems
        if isinstance(last, TreePattern):
            return last.second_normal(index + len(seq_elems), *elems, *seq_elems)
        return Seq(*elems, *self.elems)

    def pushdown_fieldname(self, name: str) -> TreePattern:
        first = self.elems[0]
        if isinstance(first, TreePattern):  # ensures len(self) == 1
            assert len(self) == 1
            return Seq(first.pushdown_fieldname(name))
        return Seq((name, first), *self.elems[1:])

    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        alias = len(aliases)
        aliases[alias] = self
        return aliases, f"P{alias}"


class ForkPattern(TreePattern, ABC):
    index: int = 0

    @classmethod
    def indexed(cls, index: int, *elems: PatternElem) -> 'ForkPattern':
        instance = cls(*elems)
        instance.index = index
        return instance

    @abstractmethod
    def expanded_expression(self, expr: List[BranchExpr]) -> BranchExpr:
        raise NotImplementedError

    def _first_normal_iter(self) -> Iterator[TreePattern]:
        for elem in self.elems:
            if type(elem) is type(self):
                yield from elem.first_normal().elems
            elif isinstance(elem, TreePattern):
                yield elem.first_normal()
            else:
                yield Seq(elem)

    def first_normal(self) -> 'TreePattern':
        normal_elems = tuple(self._first_normal_iter())
        if len(normal_elems) == 1:
            return Seq(*normal_elems)
        return type(self)(*normal_elems)

    def _second_normal_iter(self, index: int, *elems: PatternElem) -> Iterator[TreePattern]:
        for elem in self.elems:
            # always run 2nd normal after 1st, so all elems are BranchPattern
            assert isinstance(elem, TreePattern), elem
            normal = elem.second_normal(index, *elems)
            if type(normal) is type(self):
                yield from normal.elems
            else:
                yield normal

    def second_normal(self, index: int = 0, *elems: PatternElem) -> 'TreePattern':
        return type(self).indexed(index, *self._second_normal_iter(index, *elems))

    def _pushdown_fieldname_iter(self, name: str) -> Iterator[BranchElem]:
        for elem in self.elems:
            if isinstance(elem, TreePattern):
                yield elem.pushdown_fieldname(name)
            else:
                yield name, elem

    def pushdown_fieldname(self, name: str) -> TreePattern:
        return type(self)(*self._pushdown_fieldname_iter(name))

    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        # expr is an S-Expression
        expr = [f'{type(self).__name__}_{self.index}']

        expr_primitives = []
        expr_sub_exprs = []
        for elem in self.elems:
            aliases, expr_elem = elem.alias(aliases)
            if isinstance(expr_elem, list):
                expr_sub_exprs.append(expr_elem)
            else:
                expr_primitives.append(expr_elem)

        return aliases, [self.expanded_expression(expr_primitives), *expr_sub_exprs]


class And(ForkPattern):
    def expanded_expression(self, expr: List[BranchExpr]) -> BranchExpr:
        blah_ = " & ".join(str(e) for e in expr)
        blah2 = ", ".join(str(e) for e in expr)
        return f"{blah_} & siblings({self.index}, {blah2})"


class Then(ForkPattern):
    def expanded_expression(self, expr: List[BranchExpr]) -> BranchExpr:
        blah_ = " & ".join(str(e) for e in expr)
        blah2 = ", ".join(str(e) for e in expr)
        return f"{blah_} & siblings({self.index}, {blah2}) & ordered({blah2})"


class Or(ForkPattern):
    def expanded_expression(self, expr: List[BranchExpr]) -> BranchExpr:
        blah_ = " | ".join(str(e) for e in expr)
        return f"{blah_}"


class Until(StateEff):
    pass


def index_traverse_nodes(node: ast.AST, index: Tuple[int, ...] = (),
                         pos: int = 1) -> Iterator[Tuple[Tuple[int, ...], ast.AST]]:
    new_index = (*index, pos)
    yield new_index, node
    for breadth, child in enumerate(ast.iter_child_nodes(node), start=1):
        yield from index_traverse_nodes(child, new_index, breadth)


def compare_index_lineage(a: Sequence[int], b: Sequence[int], at: List[int]) -> bool:
    max_index = max(at)
    if max_index > len(a) or max_index > len(b):
        return False
    return all(a[i] == b[i] for i in at)


def digits_gte(a: Sequence[int], b: Sequence[int]) -> bool:
    return all(i >= j for i, j in zip(a, b)) or len(a) >= len(a)


def digits_gt(a: Sequence[int], b: Sequence[int]) -> bool:
    for i, j in zip(a, b):
        if i > j:
            return True
        if i < j:
            return False
    return len(a) > len(b)


def digits_lt(a: Sequence[int], b: Sequence[int]) -> bool:
    for i, j in zip(a, b):
        if i > j:
            return False
        if i < j:
            return True
    return len(a) < len(b)


def blah():
    class A:
        b = 9

        def c(self):
            pass

    A()


# User input: (list match is implicit 'Then')
example_unexpanded = Seq(
    ast.FunctionDef,
    And(
        ast.ClassDef(
            body=[
                Seq(ast.Assign, ast.Name(id='b', ctx=ast.Store())),
                ast.FunctionDef
            ]
        ),
        Until(ast.Call)
    )
)

# + FunctionDef
# |    |
# |    +- ClassDef
# |    |    |
# |    |    +- Assign, Name, Store
# |    |    +- FunctionDef
# |    |
# |    +- Call

# FunctionDef, ClassDef, Assign, Name, Store
# FunctionDef, Call


# becomes
example = Seq(
    ast.FunctionDef,
    And(
        Seq(
            ast.ClassDef(),
            Then(
                Seq(
                    ('body', ast.Assign),
                    ast.Name(id='b'),
                    ('ctx', ast.Store())
                ),
                ('body', ast.FunctionDef)
            )
        ),
        Until(ast.Call)
    )
)

# becomes
p1 = Seq(ast.FunctionDef, ast.ClassDef, ('body', ast.Assign), ast.Name(id='b'), ('ctx', ast.Store))
p2 = Seq(ast.FunctionDef, ast.ClassDef, ('body', ast.FunctionDef))
p3 = Seq(ast.FunctionDef, Until(ast.Call))


# implement AND as an all(any(fsm(branches)))?
#
# to ensure we only loop once through the branches:
# all(any(t) for t in zip(*(tuple(f(b) for f in fsm) for b in branches)))

# T F F      T F F
# F T F  ->  F T T
# F T F      F F F


# We have to use dfs, we move fsm's in and out of scope as we enter and exit
# their stacks, and we track the state of a stack as we go. So when we enter
# into an 'And' stack we produce state to track whether all branches have been
# satisfied, and then we go until all true or until we run out of nodes in this
# sub-tree. Indeed once we have satisfied one of the 'And' fsm's we can stop
# checking it as an optimisation. Once all 'And' fsm's have been satisfied we
# are able to traverse to the next stack once we finish traversing the nodes
# for this sub-tree, in this way the stacks traverse by bfs.

# register 'return' (callback) points for all fsm's to report back to, when
# they get to their accepting states they will return True to this location.

# use collections.deque to implement an "action stack" of (func, node) pairs
# that we build up as we match the tree, these will be pushed, popped and run
# in FIFO order. Could also be a stack of partially applied functions.


def to_ast(x: Any) -> ast.AST:
    return ast.parse(inspect.getsource(x), mode='exec')


def print_ast(obj: Any) -> None:
    _ast = ast.parse(inspect.getsource(obj), mode='exec')
    astpretty.pprint(_ast)
    print(ast.dump(_ast))


def func(x: int) -> str:
    b = ' no '
    a = ' blah'
    c = 9
    return str(x) + a + b + str(c)


if __name__ == '__main__':
    import math
    import itertools

    # print_ast(blah)

    some_ast = ast.Module(
        body=[
            ast.FunctionDef(
                name='func',
                args=ast.arguments(
                    args=[
                        ast.arg(arg='x', annotation=ast.Name(id='int', ctx=ast.Load()))
                    ],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[]
                ),
                body=[
                    ast.Assign(targets=[ast.Name(id='b', ctx=ast.Store())], value=ast.Str(s=' no ')),
                    ast.Assign(targets=[ast.Name(id='a', ctx=ast.Store())], value=ast.Str(s=' blah')),
                    ast.Assign(targets=[ast.Name(id='c', ctx=ast.Store())], value=ast.Num(n=9)),
                    ast.Return(
                        value=ast.BinOp(
                            left=ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.Call(
                                        func=ast.Name(id='str', ctx=ast.Load()),
                                        args=[ast.Name(id='x', ctx=ast.Load())],
                                        keywords=[]
                                    ),
                                    op=ast.Add(),
                                    right=ast.Name(id='a', ctx=ast.Load())),
                                op=ast.Add(),
                                right=ast.Name(id='b', ctx=ast.Load())),
                            op=ast.Add(),
                            right=ast.Call(
                                func=ast.Name(id='str', ctx=ast.Load()),
                                args=[ast.Name(id='c', ctx=ast.Load())],
                                keywords=[]
                            )
                        )
                    )
                ],
                decorator_list=[],
                returns=ast.Name(id='str', ctx=ast.Load())
            )
        ]
    )

    # ex1, _ = example.normalise().alias()
    # print(example.first_normal().second_normal().alias({}))
    #
    # ex2, _ = example_unexpanded.expand().first_normal().second_normal().alias()
    # print(example_unexpanded.expand().first_normal().second_normal())

    # for key in ex1:
    #     print(ex1[key] == ex2[key])

    # print(Seq(ast.ClassDef(
    #     body=[
    #         Seq(ast.Assign, ast.Name(id='b', ctx=ast.Store())),
    #         ast.FunctionDef
    #     ]
    # )).expand().first_normal().second_normal())

    s40 = And(Seq(ast.Name(id='b'))).first_normal().second_normal()
    # print(s40)

    # print(And(And(And(ast.Call))).first_normal().second_normal())

    s30 = Seq(And(Seq(ast.Name(id='b')))).first_normal().second_normal()

    # print(s30)

    # print(s30 == s40)

    # print(And(Then(Or(And(Then(Seq(ast.Call))), ast.AST))).first_normal().second_normal().alias())
    #
    # print(pattern_elem_equals(ast.Name(id='b'), ast.Name(id='b')))

    # print(get_all_ast_fields())


    def digits_to_number(digits: Sequence[int], radix: int) -> int:
        if radix == 1:
            return len(digits) - 1
        return sum(radix ** i * d for i, d in enumerate(digits[::-1]))


    def number_to_digits_iter(number: int, radix: int) -> Iterator[int]:
        while number > 0:
            (number, digit) = divmod(number, radix)
            yield digit


    def number_to_digits(number: int, radix: int) -> List[int]:
        if radix == 1:
            return [0 for _ in range(number + 1)]
        return list(number_to_digits_iter(number, radix))[::-1]

    # print(number_to_digits(6, 2))

    # cur_max = 1
    # cur_len = 1
    # zeroes = itertools.repeat(0)
    #
    # previous_idx = None
    # previous_num = None
    #
    # for x_idx, x_node in index_traverse_nodes(some_ast):
    #     cur_max = max(cur_max, max(x_idx) + 1)
    #     cur_len = max(cur_len, len(x_idx))
    #
    #     full_idx = list(itertools.islice(itertools.chain(x_idx, zeroes), cur_len))
    #     num = digits_to_number(full_idx, cur_max)
    #
    #     if previous_idx is not None:
    #         print('<', digits_lt(previous_idx, full_idx), previous_num < num)
    #
    #     print(num, full_idx)
    #
    #     previous_idx = full_idx
    #     previous_num = num

    # idx1 = (0, 0, 1, 0, 0)
    # idx2 = (0, 0, 1, 1)
    # print(compare_index_lineage(idx1, idx2, [0, 2, 9]))

    # print(digits_lt([1, 2, 1], [1, 1, 2]))
    # print(digits_to_number([1, 2, 1], 3), digits_to_number([1, 1, 2], 3))
    #
    # print(digits_lt([1, 1, 6], [1, 2, 1]))
    # print(digits_to_number([1, 1, 6], 7), digits_to_number([1, 2, 1], 7))
    #
    # print(digits_lt([1, 1, 6], [1, 1, 6]))
    # print(digits_to_number([1, 1, 6], 7), digits_to_number([1, 1, 6], 7))
    #
    # print(digits_lt([1, 6, 5], [1, 6, 6]))
    # print(digits_to_number([1, 6, 5], 7), digits_to_number([1, 6, 6], 7))
    #
    # print(Seq(to_ast(func)).expand().first_normal().second_normal().alias({})[1])

    # Rules:
    #   1) Ord(A, B) => A -> B ☑️
    #   2) Ord(A, [B, C]) => A -> B, A -> C ☑️
    #   3) Ord([A, B], C) => A -> C, B -> C ☑️
    #   4) Ord(A, [Ord(B, C), D]) => A -> B -> C, A -> D ☑️
    #   5) Ord([A, Ord(B, C)], D) => A -> D, B -> C -> D ☑️
    #   6) Ord(A, [Ord([B, C], D), E]) => Ord(A, [B -> D, C -> D, E]) => A -> B -> D, A -> C -> D, A -> E ☑️

    print(Ordered(Term('A'), [Ordered([Term('B'), Term('C')], Term('D')), Term('E')]).graph())
    # Ordered(Term('A'), [Ordered(Term('B'), Term('C')), Term('D')]).graph()
