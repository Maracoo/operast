import ast
import astpretty
import inspect
from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional, Tuple, Type, Union


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


def _node_pattern_expand(node: ast.AST) -> Optional['PatDescriptor']:
    # possible elements inside the fields of an AST node:
    # ast.AST, Type[ast.AST], PatDescriptor
    and_elements = []

    for name, field in ast.iter_fields(node):
        # case: ast.AST
        if isinstance(field, ast.AST):
            desc = _node_pattern_expand(field)
            seq = Seq((name, field)) if desc is None else Seq((name, field), desc)
            and_elements.append(seq)
            delattr(node, name)
        # case: Type[ast.AST]
        elif isinstance(field, type) and issubclass(node, ast.AST):
            and_elements.append((name, field))
            delattr(node, name)
        # case: PatDescriptor
        elif isinstance(field, PatDescriptor):
            and_elements.append(field.pushdown_fieldname(name).expand())
            delattr(node, name)
        # case: StateEff
        elif isinstance(field, StateEff):
            and_elements.append((name, field))
            delattr(node, name)

        elif isinstance(field, list):
            then_elements = []
            non_ast = []
            for item in field:
                # case: ast.AST
                if isinstance(item, ast.AST):
                    desc = _node_pattern_expand(item)
                    seq = Seq((name, item)) if desc is None else Seq((name, item), desc)
                    then_elements.append(seq)
                # case: Type[ast.AST]
                elif isinstance(item, type) and issubclass(item, ast.AST):
                    then_elements.append((name, item))
                # case: PatDescriptor
                elif isinstance(item, PatDescriptor):
                    then_elements.append(item.pushdown_fieldname(name).expand())
                # case: StateEff
                elif isinstance(item, StateEff):
                    then_elements.append(item)
                # case: non-expanding element
                else:
                    non_ast.append(item)

            if non_ast:
                setattr(node, name, non_ast)
            else:
                delattr(node, name)

            if len(then_elements) == 1:
                and_elements.append(Seq(*then_elements))
            if then_elements:
                and_elements.append(Then(*then_elements))

    if len(and_elements) == 1:
        return Seq(*and_elements)
    if and_elements:
        return And(*and_elements)
    return None


def _pattern_expand(elem: Union['PatDescriptor', PatternElem]) -> Union['PatDescriptor', PatternElem]:
    if isinstance(elem, tuple):
        name, node = elem
        # case: Tuple[str, ast.AST]
        if isinstance(node, ast.AST):
            descriptor = _node_pattern_expand(node)
            if descriptor is None:
                return name, node
            return Seq((name, node), descriptor)
        # case: Tuple[str, Type[ast.AST]]
        if isinstance(node, type) and issubclass(node, ast.AST):
            return name, node
        # case: Tuple[str, StateEff]
        if isinstance(node, StateEff):
            return name, node
    # case: ast.AST
    if isinstance(elem, ast.AST):
        descriptor = _node_pattern_expand(elem)
        if descriptor is None:
            return elem
        return Seq(elem, descriptor)
    # case: Type[ast.AST]
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return elem
    # case: StateEff
    if isinstance(elem, StateEff):
        return elem
    # case: PatDescriptor
    if isinstance(elem, PatDescriptor):
        return elem.expand()


class PatternError(Exception):
    pass


class PatDescriptor(ABC):
    __slots__ = 'elems',

    def __init__(self, *elems: Union['PatDescriptor', PatternElem]):
        self.elems = elems

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(repr(e) for e in self.elems)})"

    @abstractmethod
    def normalise(self, *elems: PatternElem) -> 'PatDescriptor':
        raise NotImplementedError

    @abstractmethod
    def pushdown_fieldname(self, name: str) -> 'PatDescriptor':
        raise NotImplementedError

    def expand(self) -> 'PatDescriptor':
        return self.__class__(*(_pattern_expand(e) for e in self.elems))


class Seq(PatDescriptor):
    def normalise(self, *elems: PatternElem) -> PatDescriptor:
        for i, elem in enumerate(self.elems):
            if isinstance(elem, PatDescriptor):
                if len(self.elems) > i + 1:
                    raise PatternError("pattern elems found after descriptor in Seq")
                return elem.normalise(*elems, *self.elems[:i])
        return Seq(*elems, *self.elems)

    def pushdown_fieldname(self, name: str) -> 'PatDescriptor':
        if self.elems:
            first = self.elems[0]
            if isinstance(first, PatDescriptor):
                return Seq(first.pushdown_fieldname(name), *self.elems[1:])
            return Seq((name, first), *self.elems[1:])
        return self


class And(PatDescriptor):
    def _normalise_iter(self, *elems: PatternElem) -> Iterator[PatDescriptor]:
        for elem in self.elems:
            if isinstance(elem, PatDescriptor):
                elem_normed = elem.normalise(*elems)
                if elem_normed.__class__ is self.__class__:
                    yield from elem_normed.elems
                else:
                    yield elem_normed
            else:
                yield Seq(*elems, elem)

    def normalise(self, *elems: PatternElem) -> PatDescriptor:
        return self.__class__(*self._normalise_iter(*elems))

    def _pushdown_fieldname_iter(self, name: str) -> Iterator[Union['PatDescriptor', PatternElem]]:
        for elem in self.elems:
            if isinstance(elem, PatDescriptor):
                yield elem.pushdown_fieldname(name)
            else:
                yield name, elem

    def pushdown_fieldname(self, name: str) -> 'PatDescriptor':
        return self.__class__(*self._pushdown_fieldname_iter(name))


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

    print(example_unexpanded.expand().normalise())

    # print(Seq(ast.ClassDef(
    #     body=[
    #         Seq(ast.Assign, ast.Name(id='b', ctx=ast.Store())),
    #         ast.FunctionDef
    #     ]
    # )).expand().normalise())
