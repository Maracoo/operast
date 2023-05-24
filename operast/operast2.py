__all__ = [
    "BX",
    "Scope",
    "Let",
    "Sub",
    "HasChild",
    "Not",
    "Or",
    "Basic",
    "StateAffect",
    "Until",
    "While",
    "START",
]

import ast

# import inspect
import operator
from ast import AST
from collections.abc import Callable
from dataclasses import dataclass

# import astpretty
from functools import partial
from typing import Any, TypeVar, Union, cast

ASTOptMutate = Callable[[AST], AST | None]
ASTOptMutateThunk = Callable[[], AST | None]

ASTElem = Union[AST, type[AST]]
State = int
UnaryBoolOp = Callable[[bool], bool]
BinaryBoolOp = Callable[[bool, bool], bool]


START: State = 0
VISIT_ATTR = "__visit__"

T = TypeVar("T")
U = TypeVar("U")


class Scope:
    __slots__ = "_action", "_context"

    def __init__(
        self,
        action: ASTOptMutateThunk | None = None,
        context: dict[str, Any] | None = None,
    ):
        self._action = action
        self._context = {} if context is None else context

    @property
    def action(self) -> ASTOptMutateThunk | None:
        return self._action

    @action.setter
    def action(self, f: ASTOptMutateThunk) -> None:
        if self._action is not None:
            msg = "Action already set on scope"
            raise AttributeError(msg)
        self._action = f

    @property
    def context(self) -> dict[str, Any]:
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

    __slots__ = "func"
    func: ValuePredicate


class _NonValue:
    pass


@dataclass
class Let:
    __slots__ = "name"
    name: str


def _let(value: Any, scope: Scope, attr: str, let: Let) -> bool:
    scope.context[attr] = {let.name: value}
    return True


@dataclass
class Sub:
    __slots__ = "name"
    name: str


def _sub(value: Any, scope: Scope, attr: str, sub: Sub) -> bool:
    return attr in scope and scope[attr].get(sub.name, _NonValue) == value


# noinspection PyUnusedLocal
def _value_eq(value: Any, scope: Scope, other: Any) -> bool:
    return value == other


def _get_filter_attrs(node: ast.AST) -> dict[str, ValuePredicate]:
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


def _check_attrs(
    node: ast.AST, scope: Scope, filters: dict[str, ValuePredicate]
) -> bool:
    return all(
        predicate(getattr(node, attr, _NonValue), scope)
        for attr, predicate in filters.items()
    )


# noinspection PyUnusedLocal
def _check_class(node: ast.AST, scope: Scope, _cls: type[ast.AST]) -> bool:
    return issubclass(type(node), _cls)


# noinspection PyUnusedLocal
def _any_node(node: ast.AST, scope: Scope) -> bool:
    return True  # pragma: no cover


def _as_pred(e: Union["NodePredicate", ASTElem]) -> ASTPredicate:
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
        return cast("ASTPredicate", partial(_check_class, _cls=node))
    if isinstance(node, AST):
        cls_func = partial(_check_class, _cls=type(node))
        filters = _get_filter_attrs(node)
        if filters:
            attrs_func = partial(_check_attrs, filters=filters)
            return conjoin_n(cls_func, attrs_func)
        return cast("ASTPredicate", cls_func)
    msg = f"node must be one of: {ASTElem}"
    raise ValueError(msg)


PredOrNodeElem = Union["NodePredicate", ASTElem]


# todo: call it language predicate in the future
@dataclass
class NodePredicate:
    __slots__ = "func"
    func: ASTPredicate

    def __call__(self, e: PredOrNodeElem) -> "NodePredicate":
        return NodePredicate(conjoin_n(self.func, _as_pred(e)))


@dataclass
class UnaryNodeProposition:
    __slots__ = "func"
    func: UnaryBoolOp

    def __call__(self, e: PredOrNodeElem) -> NodePredicate:
        return NodePredicate(compose_n(self.func, _as_pred(e)))


@dataclass
class BinaryNodeProposition:
    __slots__ = "func"
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
    __slots__ = "succeed", "fail", "predicate"

    def __init__(
        self,
        succeed: StateChange = _next_state,
        fail: StateChange = _start_state,
        predicate: ASTPredicate = _any_node,
    ):
        self.succeed = succeed
        self.fail = fail
        self.predicate = predicate

    def __call__(self, e: PredOrNodeElem) -> "StateAffect":
        if not (
            isinstance(e, NodePredicate | AST)
            or (isinstance(e, type) and issubclass(e, AST))
        ):
            msg = (
                f"StateAffect can only be called with objects of type: {PredOrNodeElem}"
            )
            raise ValueError(msg)
        return StateAffect(succeed=self.succeed, fail=self.fail, predicate=_as_pred(e))

    # todo: do not support goto
    @classmethod
    def goto(
        cls, succeed: State | None = None, fail: State | None = None
    ) -> "StateAffect":
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
