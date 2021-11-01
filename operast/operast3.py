import ast
import astpretty
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union


class StateEff:
    def __init__(self, node: Union[ast.AST, Type[ast.AST]]):
        self.node = node


PatternElem = Union[
    ast.AST, Type[ast.AST], StateEff,
    Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
]
BranchElem = Union['BranchPattern', PatternElem]
BranchExpr = Union[str, List[Union[str, 'BranchExpr']]]
Aliases = Dict[str, 'Seq']


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


def expand_cases(name: str, elem: Any) -> Union['BranchPattern', PatternElem, None]:
    # case: ast.AST
    if isinstance(elem, ast.AST):
        pat = node_expand(elem)
        return (name, elem) if pat is None else Seq((name, elem), pat)
    # case: Type[ast.AST]
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return name, elem
    # case: BranchPattern
    if isinstance(elem, BranchPattern):
        return elem.pushdown_fieldname(name).expand()
    # case: StateEff
    if isinstance(elem, StateEff):
        return name, elem
    return None


def node_expand(node: ast.AST) -> Optional['BranchPattern']:
    # possible elements inside the fields of an AST node:
    # ast.AST, Type[ast.AST], BranchPattern
    and_elements = []
    for name, field in ast.iter_fields(node):
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
    return And(*and_elements) if and_elements else None


def branch_expand(elem: BranchElem) -> BranchElem:
    # case: Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
    if isinstance(elem, tuple):
        name, node = elem
        expanded = branch_expand(node)
        if isinstance(expanded, BranchPattern):
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
    if isinstance(elem, BranchPattern):
        return elem.expand()


def node_equals(a: ast.AST, b: ast.AST) -> bool:
    if a.__class__ is not b.__class__:
        return False
    a_fields = list(ast.iter_fields(a))
    b_fields = list(ast.iter_fields(b))
    return (len(a_fields) == len(b_fields)
            and all(a == b for a, b in zip(a_fields, b_fields)))


def pattern_elem_equals(a: PatternElem, b: PatternElem) -> bool:
    # case: Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
    if isinstance(a, tuple) and isinstance(b, tuple):
        (label_a, elem_a), (label_b, elem_b) = a, b
        return label_a == label_b and pattern_elem_equals(elem_a, elem_b)
    # case: ast.AST
    if isinstance(a, ast.AST) and isinstance(b, ast.AST):
        return node_equals(a, b)
    # case: Type[ast.AST]
    if isinstance(a, type) and isinstance(b, type):
        return a is b
    # case: StateEff
    if isinstance(a, StateEff) and isinstance(b, StateEff):
        return node_equals(a.node, b.node)
    return False


class BranchPattern(ABC):
    __slots__ = 'elems',

    def __init__(self, *elems: BranchElem):
        if not elems:
            raise ValueError(f"{self.__class__.__name__} cannot be empty.")
        self.elems = elems

    def __len__(self) -> int:
        return len(self.elems)

    def __iter__(self) -> Iterator[BranchElem]:
        yield from self.elems

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(repr(e) for e in self.elems)})"

    @abstractmethod
    def normalise(self, *elems: PatternElem) -> 'BranchPattern':
        raise NotImplementedError

    @abstractmethod
    def pushdown_fieldname(self, name: str) -> 'BranchPattern':
        raise NotImplementedError

    @abstractmethod
    def _alias(self, counter: int, aliases: Aliases) -> Tuple[int, Aliases, BranchExpr]:
        raise NotImplementedError

    def alias(self, offset: int = 0) -> Tuple[Aliases, BranchExpr]:
        _, aliases, expr = self._alias(offset, {})
        return aliases, expr

    def expand(self) -> 'BranchPattern':
        return self.__class__(*(branch_expand(e) for e in self.elems))


class Seq(BranchPattern):
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Seq):
            return NotImplemented
        return all(pattern_elem_equals(i, j) for i, j in zip(self, other))

    def normalise(self, *elems: PatternElem) -> BranchPattern:
        for i, elem in enumerate(self.elems):
            if isinstance(elem, BranchPattern):
                if len(self.elems) > i + 1:
                    raise ValueError(
                        f"pattern elems found after branch pattern in {self}"
                    )
                return elem.normalise(*elems, *self.elems[:i])
        return Seq(*elems, *self.elems)

    def pushdown_fieldname(self, name: str) -> BranchPattern:
        first = self.elems[0]
        if isinstance(first, BranchPattern):
            return Seq(first.pushdown_fieldname(name), *self.elems[1:])
        return Seq((name, first), *self.elems[1:])

    def _alias(self, counter: int, aliases: Aliases) -> Tuple[int, Aliases, BranchExpr]:
        counter += 1
        expr = f"S{counter}"
        aliases[expr] = self
        return counter, aliases, expr


class And(BranchPattern):
    def _normalise_iter(self, *elems: PatternElem) -> Iterator[BranchPattern]:
        for elem in self.elems:
            if isinstance(elem, BranchPattern):
                normalised = elem.normalise(*elems)
                # if classes are the same then we can merge these branch
                # patterns, i.e., And(And(...)) becomes And(...)
                if normalised.__class__ is self.__class__:
                    yield from normalised.elems
                else:
                    yield normalised
            else:
                yield Seq(*elems, elem)

    def normalise(self, *elems: PatternElem) -> BranchPattern:
        if len(self) == 1:
            elem = self.elems[0]
            if isinstance(elem, BranchPattern):
                return elem.normalise(*elems)
            return Seq(*elems, elem)
        return self.__class__(*self._normalise_iter(*elems))

    def _pushdown_fieldname_iter(self, name: str) -> Iterator[BranchElem]:
        for elem in self.elems:
            if isinstance(elem, BranchPattern):
                yield elem.pushdown_fieldname(name)
            else:
                yield name, elem

    def pushdown_fieldname(self, name: str) -> BranchPattern:
        return self.__class__(*self._pushdown_fieldname_iter(name))

    def _alias(self, counter: int, aliases: Aliases) -> Tuple[int, Aliases, BranchExpr]:
        expr_list = [self.__class__.__name__]
        for elem in self.elems:
            counter, aliases, expr = elem._alias(counter, aliases)
            expr_list.append(expr)
        return counter, aliases, expr_list


class Then(And):
    pass


class Or(And):
    pass


class Until(StateEff):
    pass


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


# def build_recr(seq: Seq):
#     for e in seq:
#         pass


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


def print_ast(obj: Any) -> None:
    _ast = ast.parse(inspect.getsource(obj), mode='exec')
    astpretty.pprint(_ast)
    # print(ast.dump(_ast))


def func(x: int) -> str:
    b = ' no '
    a = ' blah'
    c = 9
    return str(x) + a + b + str(c)


if __name__ == '__main__':
    # from ast import *

    # print_ast(blah)

    # Module(
    #     body=[
    #         FunctionDef(
    #             name='func',
    #             args=arguments(
    #                 args=[
    #                     arg(arg='x', annotation=Name(id='int', ctx=Load()))
    #                 ],
    #                 vararg=None,
    #                 kwonlyargs=[],
    #                 kw_defaults=[],
    #                 kwarg=None,
    #                 defaults=[]
    #             ),
    #             body=[
    #                 Assign(targets=[Name(id='b', ctx=Store())], value=Str(s=' no ')),
    #                 Assign(targets=[Name(id='a', ctx=Store())], value=Str(s=' blah')),
    #                 Assign(targets=[Name(id='c', ctx=Store())], value=Num(n=9)),
    #                 Return(
    #                     value=BinOp(
    #                         left=BinOp(
    #                             left=BinOp(
    #                                 left=Call(
    #                                     func=Name(id='str', ctx=Load()),
    #                                     args=[Name(id='x', ctx=Load())],
    #                                     keywords=[]
    #                                 ),
    #                                 op=Add(),
    #                                 right=Name(id='a', ctx=Load())),
    #                             op=Add(),
    #                             right=Name(id='b', ctx=Load())),
    #                         op=Add(),
    #                         right=Call(
    #                             func=Name(id='str', ctx=Load()),
    #                             args=[Name(id='c', ctx=Load())],
    #                             keywords=[]
    #                         )
    #                     )
    #                 )
    #             ],
    #             decorator_list=[],
    #             returns=Name(id='str', ctx=Load())
    #         )
    #     ]
    # )

    ex1, _ = example.normalise().alias()
    print(example.normalise())

    ex2, _ = example_unexpanded.expand().normalise().alias()
    print(example_unexpanded.expand().normalise())

    # for key in ex1:
    #     print(ex1[key] == ex2[key])

    # print(Seq(ast.ClassDef(
    #     body=[
    #         Seq(ast.Assign, ast.Name(id='b', ctx=ast.Store())),
    #         ast.FunctionDef
    #     ]
    # )).expand().normalise())

    s40 = And(Seq(ast.Name(id='b'))).normalise()
    print(s40)

    print(And(And(And(ast.Call))).normalise())

    s30 = Seq(And(Seq(ast.Name(id='b')))).normalise()
    print(s30)

    print(s30 == s40)

    print(And(Then(Or(And(Then(Seq(ast.Call))), ast.AST))).normalise().alias())

    print(pattern_elem_equals(ast.Name(id='b'), ast.Name(id='b')))
