import ast
import astpretty
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional, Tuple, Type, Union


class StateEff:
    def __init__(self, node: Union[ast.AST, Type[ast.AST]]):
        self.node = node


PatternElem = Union[ast.AST, Type[ast.AST], StateEff,
                    Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]]


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


def _node_pattern_expand(node: ast.AST) -> Optional['BranchPattern']:
    # possible elements inside the fields of an AST node:
    # ast.AST, Type[ast.AST], BranchPattern
    and_elements = []

    for name, field in ast.iter_fields(node):
        # case: ast.AST
        if isinstance(field, ast.AST):
            path = _node_pattern_expand(field)
            seq = (name, field) if path is None else Seq((name, field), path)
            and_elements.append(seq)
            delattr(node, name)
        # case: Type[ast.AST]
        elif isinstance(field, type) and issubclass(node, ast.AST):
            and_elements.append((name, field))
            delattr(node, name)
        # case: BranchPattern
        elif isinstance(field, BranchPattern):
            and_elements.append(field.pushdown_fieldname(name).expand())
            delattr(node, name)
        # case: StateEff
        elif isinstance(field, StateEff):
            and_elements.append((name, field))
            delattr(node, name)

        elif isinstance(field, list):
            then_elements = []
            non_pattern_elements = []
            for item in field:
                # case: ast.AST
                if isinstance(item, ast.AST):
                    pat = _node_pattern_expand(item)
                    seq = (name, item) if pat is None else Seq((name, item), pat)
                    then_elements.append(seq)
                # case: Type[ast.AST]
                elif isinstance(item, type) and issubclass(item, ast.AST):
                    then_elements.append((name, item))
                # case: BranchPattern
                elif isinstance(item, BranchPattern):
                    then_elements.append(item.pushdown_fieldname(name).expand())
                # case: StateEff
                elif isinstance(item, StateEff):
                    then_elements.append(item)
                # case: non-expanding element
                else:
                    non_pattern_elements.append(item)

            if non_pattern_elements:
                setattr(node, name, non_pattern_elements)
            else:
                delattr(node, name)

            if len(then_elements) == 1:
                and_elements.append(Seq(*then_elements))
            elif then_elements:
                and_elements.append(Then(*then_elements))

    if len(and_elements) == 1:
        return Seq(*and_elements)
    if and_elements:
        return And(*and_elements)
    return None


def _pattern_expand(elem: Union['BranchPattern', PatternElem]) -> Union['BranchPattern', PatternElem]:
    if isinstance(elem, tuple):
        name, node = elem
        # case: Tuple[str, ast.AST]
        if isinstance(node, ast.AST):
            pat = _node_pattern_expand(node)
            return (name, node) if pat is None else Seq((name, node), pat)
        # case: Tuple[str, Type[ast.AST]]
        if isinstance(node, type) and issubclass(node, ast.AST):
            return name, node
        # case: Tuple[str, StateEff]
        if isinstance(node, StateEff):
            return name, node
    # case: ast.AST
    if isinstance(elem, ast.AST):
        pat = _node_pattern_expand(elem)
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


class PatternError(Exception):
    pass


class BranchPattern(ABC):
    __slots__ = 'elems',

    def __init__(self, *elems: Union['BranchPattern', PatternElem]):
        if not elems:
            raise ValueError(f"{self.__class__.__name__} cannot be empty.")
        self.elems = elems

    def __len__(self) -> int:
        return len(self.elems)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(repr(e) for e in self.elems)})"

    @abstractmethod
    def normalise(self, *elems: PatternElem) -> 'BranchPattern':
        raise NotImplementedError

    @abstractmethod
    def pushdown_fieldname(self, name: str) -> 'BranchPattern':
        raise NotImplementedError

    @abstractmethod
    def _alias(self, counter: int, aliases: Dict[str, 'Seq']) -> Tuple[int, Dict[str, 'Seq'], Any]:
        raise NotImplementedError

    def alias(self, offset: int = 0) -> Tuple[Dict[str, 'Seq'], Any]:
        _, aliases, expr = self._alias(offset, {})
        return aliases, expr

    def expand(self) -> 'BranchPattern':
        return self.__class__(*(_pattern_expand(e) for e in self.elems))


class Seq(BranchPattern):
    def normalise(self, *elems: PatternElem) -> BranchPattern:
        for i, elem in enumerate(self.elems):
            if isinstance(elem, BranchPattern):
                if len(self.elems) > i + 1:
                    raise PatternError("pattern elems found after branch pattern in Seq")
                return elem.normalise(*elems, *self.elems[:i])
        return Seq(*elems, *self.elems)

    def pushdown_fieldname(self, name: str) -> 'BranchPattern':
        first = self.elems[0]
        if isinstance(first, BranchPattern):
            return Seq(first.pushdown_fieldname(name), *self.elems[1:])
        return Seq((name, first), *self.elems[1:])

    def _alias(self, counter: int, aliases: Dict[str, 'Seq']) -> Tuple[int, Dict[str, 'Seq'], Any]:
        counter += 1
        aliases[f"S{counter}"] = self
        return counter, aliases, f"S{counter}"


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

    def _pushdown_fieldname_iter(self, name: str) -> Iterator[Union['BranchPattern', PatternElem]]:
        for elem in self.elems:
            if isinstance(elem, BranchPattern):
                yield elem.pushdown_fieldname(name)
            else:
                yield name, elem

    def pushdown_fieldname(self, name: str) -> 'BranchPattern':
        return self.__class__(*self._pushdown_fieldname_iter(name))

    def _alias(self, counter: int, aliases: Dict[str, 'Seq']) -> Tuple[int, Dict[str, 'Seq'], Any]:
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

    print(example.normalise())

    print(example_unexpanded.expand().normalise().alias())

    # print(Seq(ast.ClassDef(
    #     body=[
    #         Seq(ast.Assign, ast.Name(id='b', ctx=ast.Store())),
    #         ast.FunctionDef
    #     ]
    # )).expand().normalise())

    print(And(Seq(ast.Name)).normalise())

    print(And(And(And(ast.Call))).normalise())

    print(Seq(And(Seq(ast.Name))).normalise().alias())

    print(And(Then(Or(And(Then(Seq(ast.Call))), ast.AST))).normalise().alias())
