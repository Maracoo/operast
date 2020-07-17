
import ast
# import astpretty
from functools import partial
# import inspect
import operator
from ast import AST, FunctionDef, Call
from dataclasses import dataclass
from typing import Optional, Type, Generator, Set, List, Generic, \
    Tuple, Dict, Callable, Union, Any, TypeVar, cast as as_typ


ASTOptMutate = Callable[[AST], Optional[AST]]

ASTElem = Union[AST, Type[AST]]
State = int
VisitF = Callable[[AST], Optional[AST]]
UnaryBoolOp = Callable[[bool], bool]
BinaryBoolOp = Callable[[bool, bool], bool]
Predicate = Callable[..., bool]
TransitionFunc = Callable[[AST, State], Tuple[Optional[AST], State]]


START: State = 0
VISIT_ATTR = '__visit__'

T = TypeVar('T')
U = TypeVar('U')


Scope = Dict[str, Any]
ValuePredicate = Callable[[Any, Scope], bool]
ASTPredicate = Callable[[AST, Scope], bool]


@dataclass
class BX:
    """Boolean Expression"""
    __slots__ = 'func'
    func: ValuePredicate


class _NonValue:
    pass


@dataclass
class Let:
    __slots__ = 'name'
    name: str


def _let(attr: str, let: Let, value: Any, scope: Scope) -> bool:
    scope[attr] = {let.name: value}
    return True


@dataclass
class Sub:
    __slots__ = 'name'
    name: str


def _sub(attr: str, sub: Sub, value: Any, scope: Scope) -> bool:
    return attr in scope and scope[attr].get(sub.name, _NonValue) == value


# noinspection PyUnusedLocal
def _value_eq(v1: Any, v2: Any, scope: Scope) -> bool:
    return v1 == v2


def _get_filter_attrs(node: ast.AST) -> Dict[str, Predicate]:
    filters = {}
    for attr, value in node.__dict__.items():
        if isinstance(value, BX):
            filters[attr] = value.func
        elif isinstance(value, Let):
            filters[attr] = partial(_let, attr, value)
        elif isinstance(value, Sub):
            filters[attr] = partial(_sub, attr, value)
        else:
            filters[attr] = partial(_value_eq, v1=value)
    return filters


# noinspection PyUnusedLocal
def _has_children(node: AST, scope: Scope) -> bool:
    return next((True for _ in ast.iter_child_nodes(node)), False)


def _check_attrs(node: ast.AST, scope: Scope, filters: Dict[str, ValuePredicate]) -> bool:
    return all(predicate(getattr(node, attr, _NonValue), scope)
               for attr, predicate in filters.items())


# noinspection PyUnusedLocal
def _check_class(node: ast.AST, scope: Scope, _cls: Type[AST]) -> bool:
    return issubclass(node.__class__, _cls)


# noinspection PyUnusedLocal
def _any_node(node: ast.AST, scope: Scope) -> bool:
    return True


def _as_pred(e: Union['NodePredicate', ASTElem]) -> ASTPredicate:
    return e.func if isinstance(e, NodePredicate) else node_identity(e)


def compose_n(g: Callable[..., U], *fs: Callable[..., T]) -> Callable[..., U]:
    return lambda *args, **kwargs: g(*(f(*args, **kwargs) for f in fs))


def conjoin_n(*fs: Callable[..., bool]) -> Callable[..., bool]:
    return lambda *args, **kwargs: all(f(*args, **kwargs) for f in fs)


def as_ast_pred(call: Union[Callable, partial]) -> ASTPredicate:
    return as_typ(ASTPredicate, call)


def node_identity(node: ASTElem) -> ASTPredicate:
    # node is instance of some class in the ast hierarchy
    if isinstance(node, AST):
        cls_func = partial(_check_class, _cls=node.__class__)
        filters = _get_filter_attrs(node)
        if filters:
            attrs_func = partial(_check_attrs, filters=filters)
            return conjoin_n(cls_func, attrs_func)
        return as_ast_pred(cls_func)
    return as_ast_pred(partial(_check_class, _cls=node))


@dataclass
class NodePredicate:
    __slots__ = 'func'
    func: ASTPredicate

    def __call__(self, e: Union['NodePredicate', ASTElem]) -> 'NodePredicate':
        return NodePredicate(conjoin_n(self.func, _as_pred(e)))


PatternElem = Union[NodePredicate, ASTElem]


@dataclass
class UnaryNodeProposition:
    __slots__ = 'func'
    func: UnaryBoolOp

    def __call__(self, e: PatternElem) -> NodePredicate:
        return NodePredicate(compose_n(self.func, _as_pred(e)))


@dataclass
class BinaryNodeProposition:
    __slots__ = 'func'
    func: BinaryBoolOp

    def __call__(self, e1: PatternElem, e2: PatternElem) -> NodePredicate:
        return NodePredicate(compose_n(self.func, _as_pred(e1), _as_pred(e2)))


HasChild = NodePredicate(_has_children)
Not = UnaryNodeProposition(operator.not_)
Or = BinaryNodeProposition(operator.or_)


StateChange = Callable[[State], State]


def _next_state(state: State) -> State:
    return state + 1


# noinspection PyUnusedLocal
def _start_state(state: State) -> State:
    return START


def _this_state(state: State) -> State:
    return state


@dataclass
class StateAffect:
    succeed: StateChange = _next_state
    fail: StateChange = _start_state
    predicate: ASTPredicate = _any_node

    def __call__(self, e: PatternElem) -> 'StateAffect':
        return StateAffect(succeed=self.succeed,
                           fail=self.fail,
                           predicate=_as_pred(e))


Until = StateAffect(fail=_this_state)
While = StateAffect(succeed=_this_state)
Always = StateAffect(succeed=_this_state, fail=_this_state)


@dataclass
class Transition:
    __slots__ = 'predicate', 'succeed', 'fail', 'state'
    predicate: ASTPredicate
    succeed: StateChange
    fail: StateChange
    state: State

    def __call__(self, node: AST, scope: Scope) -> Tuple[Optional[AST], State]:
        if self.predicate(node, scope):
            return node, self.succeed(self.state)
        return node, self.fail(self.state)


@dataclass
class TransitionMutate(Transition):
    __slots__ = 'mutate'
    mutate: ASTOptMutate

    def __call__(self, node: AST, scope: Scope) -> Tuple[Optional[AST], State]:
        if self.predicate(node, scope):
            return self.mutate(node), self.succeed(self.state)
        return node, self.fail(self.state)


_test1 = node_identity(FunctionDef(name='f'))
_test2 = Or(Call, Not(FunctionDef(name='f'))).func
_test3 = Not(HasChild(ast.stmt)).func

td = {'a': 1}
_test4 = node_identity(AST(name='f', store=Let('s')))
_test5 = node_identity(AST(name=BX(lambda x, scope: x != 'f')))

td2 = {'sub': {'s': 10}}
_test6 = node_identity(AST(sub=Sub('s')))
_test7 = Not(AST(sub=Sub('s'))).func


# drawback: have to check spelling of attributes

# def test_1():
#     assert True


if __name__ == '__main__':
    print(_test7(FunctionDef(name='f', store='hhh', sub=10), td2))
