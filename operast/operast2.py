
__all__ = ['BX', 'Scope', 'Let', 'Sub', 'HasChild', 'Not', 'Or', 'Basic',
           'StateAffect', 'Until', 'While', 'Always', 'START', 'Transition']

import ast
# import astpretty
from functools import partial
# import inspect
import operator
from ast import AST
from dataclasses import dataclass
from typing import Optional, Type, Tuple, Dict, \
    Callable, Union, Any, TypeVar, cast


ASTOptMutate = Callable[[AST], Optional[AST]]
ASTOptMutateThunk = Callable[[], Optional[AST]]

ASTElem = Union[AST, Type[AST]]
State = int
VisitF = Callable[[AST], Optional[AST]]
UnaryBoolOp = Callable[[bool], bool]
BinaryBoolOp = Callable[[bool, bool], bool]
TransitionFunc = Callable[[AST, State], Tuple[Optional[AST], State]]


START: State = 0
VISIT_ATTR = '__visit__'

T = TypeVar('T')
U = TypeVar('U')


@dataclass(init=False)
class Scope:
    __slots__ = '_action', '_context'

    def __init__(self, action: Optional[ASTOptMutateThunk] = None,
                 context: Optional[Dict[str, Any]] = None):
        self._action = action
        self._context = {} if context is None else context

    @property
    def action(self) -> Optional[ASTOptMutateThunk]:
        return self._action

    @action.setter
    def action(self, f: ASTOptMutateThunk) -> None:
        if self._action is not None:
            raise AttributeError('Action already set on scope')
        self._action = f

    @property
    def context(self) -> Dict[str, Any]:
        return self._context


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


def _let(value: Any, scope: Scope, attr: str, let: Let) -> bool:
    scope.context[attr] = {let.name: value}
    return True


@dataclass
class Sub:
    __slots__ = 'name'
    name: str


def _sub(value: Any, scope: Scope, attr: str, sub: Sub) -> bool:
    return attr in scope.context and scope.context[attr].get(sub.name, _NonValue) == value


# noinspection PyUnusedLocal
def _value_eq(value: Any, scope: Scope, other: Any) -> bool:
    return value == other


def _get_filter_attrs(node: ast.AST) -> Dict[str, ValuePredicate]:
    filters = {}
    for attr, expr in node.__dict__.items():
        if isinstance(expr, BX):
            filters[attr] = expr.func
        elif isinstance(expr, Let):
            filters[attr] = partial(_let, attr=attr, let=expr)
        elif isinstance(expr, Sub):
            filters[attr] = partial(_sub, attr=attr, sub=expr)
        else:
            filters[attr] = partial(_value_eq, other=expr)
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
    return True  # pragma: no cover


def _as_pred(e: Union['NodePredicate', ASTElem]) -> ASTPredicate:
    return e.func if isinstance(e, NodePredicate) else node_identity(e)


def compose_n(g: Callable[..., U], *fs: Callable[..., T]) -> Callable[..., U]:
    return lambda *args, **kwargs: g(*(f(*args, **kwargs) for f in fs))


def conjoin_n(*fs: Callable[..., bool]) -> Callable[..., bool]:
    return lambda *args, **kwargs: all(f(*args, **kwargs) for f in fs)


def node_identity(node: ASTElem) -> ASTPredicate:
    # node is a type or an instance of some type in the ast hierarchy
    if isinstance(node, AST):
        cls_func = partial(_check_class, _cls=node.__class__)
        filters = _get_filter_attrs(node)
        if filters:
            attrs_func = partial(_check_attrs, filters=filters)
            return conjoin_n(cls_func, attrs_func)
        return cast('ASTPredicate', cls_func)
    return cast('ASTPredicate', partial(_check_class, _cls=node))


PredOrNodeElem = Union['NodePredicate', ASTElem]


@dataclass
class NodePredicate:
    __slots__ = 'func'
    func: ASTPredicate

    def __call__(self, e: PredOrNodeElem) -> 'NodePredicate':
        return NodePredicate(conjoin_n(self.func, _as_pred(e)))


@dataclass
class UnaryNodeProposition:
    __slots__ = 'func'
    func: UnaryBoolOp

    def __call__(self, e: PredOrNodeElem) -> NodePredicate:
        return NodePredicate(compose_n(self.func, _as_pred(e)))


@dataclass
class BinaryNodeProposition:
    __slots__ = 'func'
    func: BinaryBoolOp

    def __call__(self, e1: PredOrNodeElem, e2: PredOrNodeElem) -> NodePredicate:
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


@dataclass(init=False)
class StateAffect:
    __slots__ = 'succeed', 'fail', 'predicate'

    def __init__(self, succeed: StateChange = _next_state,
                 fail: StateChange = _start_state,
                 predicate: ASTPredicate = _any_node):
        self.succeed = succeed
        self.fail = fail
        self.predicate = predicate

    def __call__(self, e: PredOrNodeElem) -> 'StateAffect':
        if not (isinstance(e, (NodePredicate, AST)) or
                (isinstance(e, type) and issubclass(e, AST))):
            raise ValueError(f'StateAffect can only be called '
                             f'with objects of type: {PredOrNodeElem}')
        return StateAffect(succeed=self.succeed,
                           fail=self.fail,
                           predicate=_as_pred(e))


Basic = StateAffect()
Until = StateAffect(fail=_this_state)
While = StateAffect(succeed=_this_state)
Always = StateAffect(succeed=_this_state, fail=_this_state)


PatternElement = Union[StateAffect, PredOrNodeElem]


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

    @classmethod
    def build(cls, affect: StateAffect, state: State) -> 'Transition':
        return cls(affect.predicate, affect.succeed, affect.fail, state)


@dataclass
class TransitionAction(Transition):
    __slots__ = 'action'
    action: ASTOptMutate

    def __call__(self, node: AST, scope: Scope) -> Tuple[Optional[AST], State]:
        if self.predicate(node, scope):
            return self.action(node), self.succeed(self.state)
        return node, self.fail(self.state)

    @classmethod
    def build_action(cls, affect: StateAffect, state: State, action: ASTOptMutate) -> 'TransitionAction':
        return cls(affect.predicate, affect.succeed, affect.fail, state, action)


@dataclass
class TransitionFuture(TransitionAction):
    def __call__(self, node: AST, scope: Scope) -> Tuple[Optional[AST], State]:
        scope.action = partial(self.action, node)
        if self.predicate(node, scope):
            return node, self.succeed(self.state)
        return node, self.fail(self.state)


@dataclass
class TransitionEnd(Transition):
    def __call__(self, node: AST, scope: Scope) -> Tuple[Optional[AST], State]:
        if self.predicate(node, scope):
            assert scope.action is not None  # invariant, should never be false
            return scope.action(), self.succeed(self.state)
        return node, self.fail(self.state)


@dataclass
class FiniteStateMachine:
    __slots__ = 'state_table'
    state_table: Dict[State, Transition]

    def __call__(self, node: AST, state: State, scope: Scope) -> Tuple[Optional[AST], State]:
        return self.state_table[state](node, scope)


def make_fsm(*pattern: PatternElement, action: ASTOptMutate,
             at: Optional[State] = None) -> FiniteStateMachine:
    if not pattern:
        raise ValueError
    end_state = len(pattern) - 1  # zero based
    _at = end_state if at is None else at
    if _at > end_state:
        raise ValueError

    state_table: Dict[State, Transition] = {}

    for state, elem in enumerate(pattern):
        state_affect = elem if isinstance(elem, StateAffect) else Basic(elem)
        if state == _at and state == end_state:
            transition = TransitionAction.build_action(state_affect, state, action)
        elif state == _at:
            transition = TransitionFuture.build_action(state_affect, state, action)
        elif state != _at and state_table == end_state:
            transition = TransitionEnd.build(state_affect, state)
        else:
            transition = Transition.build(state_affect, state)
        state_table[state] = transition

    return FiniteStateMachine(state_table=state_table)


# Have a TransitionEnd class to indicate when the action should fire
# And have a TransitionFuture class which passes alone it's ASTOptMutate in the scope waiting to be called


# drawback: have to check spelling of attributes


# if __name__ == '__main__':
#     print(_test7(FunctionDef(name='f', store='hhh', sub=10), td2))
