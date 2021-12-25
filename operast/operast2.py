
__all__ = ['BX', 'Scope', 'Let', 'Sub', 'HasChild', 'Not', 'Or', 'Basic',
           'StateAffect', 'Until', 'While', 'START', 'Transition']

import ast
# import astpretty
from functools import partial
# import inspect
import operator
from ast import AST
from dataclasses import dataclass
from typing import Optional, Type, Tuple, Dict, \
    Callable, Iterator, Union, Any, TypeVar, cast


ASTOptMutate = Callable[[AST], Optional[AST]]
ASTOptMutateThunk = Callable[[], Optional[AST]]

ASTElem = Union[AST, Type[AST]]
State = int
UnaryBoolOp = Callable[[bool], bool]
BinaryBoolOp = Callable[[bool, bool], bool]


START: State = 0
VISIT_ATTR = '__visit__'

T = TypeVar('T')
U = TypeVar('U')


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

    def __setitem__(self, key, value) -> None:
        self.context[key] = value

    def __getitem__(self, item) -> Any:
        return self.context[item]

    def __delitem__(self, key) -> None:
        del self.context[key]

    def __contains__(self, item) -> bool:
        return item in self.context


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
    return attr in scope and scope[attr].get(sub.name, _NonValue) == value


# noinspection PyUnusedLocal
def _value_eq(value: Any, scope: Scope, other: Any) -> bool:
    return value == other


def _get_filter_attrs(node: ast.AST) -> Dict[str, ValuePredicate]:
    filters = {}
    # todo: using node.__dict__ will fail as this include _attributes of a node
    #  as well as all _fields
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
def _check_class(node: ast.AST, scope: Scope, _cls: Type[ast.AST]) -> bool:
    return issubclass(type(node), _cls)


# noinspection PyUnusedLocal
def _any_node(node: ast.AST, scope: Scope) -> bool:
    return True  # pragma: no cover


def _as_pred(e: Union['NodePredicate', ASTElem]) -> ASTPredicate:
    return e.func if isinstance(e, NodePredicate) else node_identity(e)


# This is not really a compose of all the functions, rather we have g o (f1, f2, ...)
def compose_n(g: Callable[..., U], *fs: Callable[..., T]) -> Callable[..., U]:
    return lambda *args, **kwargs: g(*(f(*args, **kwargs) for f in fs))


def conjoin_n(*fs: Callable[..., bool]) -> Callable[..., bool]:
    return lambda *args, **kwargs: all(f(*args, **kwargs) for f in fs)


def node_identity(node: ASTElem) -> ASTPredicate:
    # node is AST class, indicating use as wildcard
    if node is AST:
        return _any_node
    # node is a type or an instance of some type in the ast hierarchy
    if isinstance(node, type) and issubclass(node, AST):
        return cast('ASTPredicate', partial(_check_class, _cls=node))
    if isinstance(node, AST):
        cls_func = partial(_check_class, _cls=type(node))
        filters = _get_filter_attrs(node)
        if filters:
            attrs_func = partial(_check_attrs, filters=filters)
            return conjoin_n(cls_func, attrs_func)
        return cast('ASTPredicate', cls_func)
    raise ValueError(f'node must be one of: {ASTElem}')


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


# noinspection PyUnusedLocal
def _to_state(state: State, to: State) -> State:
    """intended for partial application"""
    return to


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

    @classmethod
    def goto(cls, succeed: Optional[State] = None,
             fail: Optional[State] = None) -> 'StateAffect':
        s = _next_state if succeed is None else partial(_to_state, to=succeed)
        f = _start_state if fail is None else partial(_to_state, to=fail)
        return cls(succeed=s, fail=f)

    def succeed_end(self) -> None:
        """Change only default succeed behaviour to return START"""
        if self.succeed is _next_state:
            self.succeed = _start_state


Basic = StateAffect()
Until = StateAffect(fail=_this_state)
While = StateAffect(succeed=_this_state)


PatternElement = Union[StateAffect, PredOrNodeElem]


def _as_affect(e: PatternElement) -> StateAffect:
    return e if isinstance(e, StateAffect) else Basic(e)


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
        if self.predicate(node, scope):
            scope.action = partial(self.action, node)
            return node, self.succeed(self.state)
        return node, self.fail(self.state)


@dataclass
class TransitionEnd(Transition):
    def __call__(self, node: AST, scope: Scope) -> Tuple[Optional[AST], State]:
        if self.predicate(node, scope):
            assert scope.action is not None  # invariant, should never be false
            scope.action()
            return node, self.succeed(self.state)
        return node, self.fail(self.state)


# Turn FSM after 'at' into an acceptor instead of mealy machine, which
# corresponds to it's use as a function returning a boolean

# impl function as returning iterator[opt[bool]] with True for accepting,
# None if proceeding but not empty children, False otherwise. Visitor to take
# action if iter yields True.


def acceptor_iter(start: State, state: State, accepting: State, node: AST,
                  fsa: Callable[[State, AST], State]) -> Iterator[Optional[bool]]:
    children = list(ast.iter_child_nodes(node))

    yield False


# todo: This class is actually a finite state transducer (non-accepting)
#   in fact, this class just represents the transition function of a mealy machine
@dataclass(unsafe_hash=True)
class FiniteStateMachine:
    __slots__ = 'state_table'
    state_table: Dict[State, Transition]

    def __call__(self, node: AST, state: State, scope: Scope) -> Tuple[Optional[AST], State]:
        return self.state_table[state](node, scope)

    @property
    def start(self) -> Transition:
        return self.state_table[START]


# todo: validate state access for FSM, i.e., warn if state not reachable,
#  error if accepting state not reachable, error if state not in table


def _make_fsm(pattern: Tuple[PatternElement, ...], action: ASTOptMutate,
              action_state: State) -> FiniteStateMachine:
    end_state = len(pattern) - 1  # zero based
    state_table: Dict[State, Transition] = {}

    for state, elem in enumerate(pattern):
        affect = _as_affect(elem)
        if state == action_state and state == end_state:
            affect.succeed_end()
            transition = TransitionAction.build_action(affect, state, action)
        elif state == action_state and state != end_state:
            transition = TransitionFuture.build_action(affect, state, action)
        elif state != action_state and state == end_state:
            affect.succeed_end()
            transition = TransitionEnd.build(affect, state)
        else:
            transition = Transition.build(affect, state)
        state_table[state] = transition

    return FiniteStateMachine(state_table=state_table)


# todo: validator function & repr for pretty print (maybe matplotlib?)

# drawback: have to check spelling of attributes

# Use this tool to generate a non-deterministic automata for some body of code

# if __name__ == '__main__':
#     print()
#     print(_test7(FunctionDef(name='f', store='hhh', sub=10), td2))

# if not pattern:
#     raise ValueError('Pattern cannot be empty')
# end_state = len(pattern) - 1  # zero based
# action_state = end_state if at is None else at
# if action_state > end_state:
#     raise ValueError('param: "at" > length of pattern')

# Delete method: D1

Deleted = set()


def __del__(self):
    Deleted.add(id(self))
    for node in ast.iter_child_nodes(self):
        assert hasattr(node, '__del__')
        del node


"""
--- PLAN 1 for suffix checking ---

1. start AT some node
    add direct children 
2. iterate through children adding delete method (D1) to children as we go
3. if fsa returns START then STOP
4. if fsa returns state such that START < state < ACCEPTING, then yield state
5. if fsa returns ACCEPTING then yield True
(default yield False)
6. if visitor receives True then apply function and check result:
    if None then Stop suffix check and continue matching
    if Some(node) then check


--- PLAN 2 for suffix checking ---

Just have a finite state transducer where we have state X node -> state. 
Structure this as an iterator which yields nothing on non-accepting, yields 
True on accepting and yields False only once all possible progeny nodes are 
checked. If True is yielded then we need to check provenance to ensure we only 
continue running for nodes which still exist. To do this we check node id's 
against previously cached existing nodes. If any link is broken then we stop 
processing on nodes further down the chain.
"""
