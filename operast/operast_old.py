# """Operast"""
#
# import ast
# import inspect
# import astpretty
# from dataclasses import dataclass
# from typing import Optional, Type, Generator, Set, List, \
#     Tuple, Dict, Callable, Union, Any, cast as as_typ
# from functools import partial, lru_cache
# from collections import defaultdict
# import operator
#
# # Design Goal: To cleanly separate the logic for ast navigation
# # from the logic applied by the visitor to a visited node
#
# # Separate code for building state machines from code that manages running
# # multiple state machines.
#
#
# ################################################################################
# # GENERAL
# ################################################################################
#
# ASTOptMutate = Callable[[ast.AST], Optional[ast.AST]]
# ASTPredicate = Callable[[ast.AST], bool]
# PatternElem = Union[ast.AST, Type[ast.AST]]
# State = int
# VisitF = Callable[[ast.AST], ast.AST]
#
# START: State = 0
# VISIT_ATTR = '__visit__'
#
#
# def _visit_wrapper(func: VisitF, pattern: List[PatternElem], at: int) -> VisitF:
#     setattr(func, VISIT_ATTR, _VisitorParams(pattern, at))
#     return func
#
#
# def visit(*pattern: PatternElem, at: Optional[int] = None):
#     _pattern = list(pattern)
#     if not _pattern:
#         raise ValueError('Pattern must contain at least one element')
#     at = len(_pattern) if at is None else at
#     if at > len(_pattern):
#         raise ValueError('Param "at" > pattern length')
#     _wrap = partial(_visit_wrapper, pattern=pattern, at=at)
#     return _wrap
#
#
# ################################################################################
# # NEW_IMPLEMENTATION
# ################################################################################
#
#
# Trans = Callable[[ast.AST], State]
#
#
# @dataclass(eq=False, frozen=True)
# class _NodeFSM2:
#     __slots__ = 'state_table'
#     state_table: Dict[State, Trans]
#
#     def __call__(self, state: State, node: ast.AST) -> State:
#         return self.state_table[state](node)
#
#
# def _make_transition_func() -> Trans:
#     pass
#
#
# def _make_state_table(pattern: List[PatternElem]) -> Dict[State, Trans]:
#     pass
#
#
# ################################################################################
# # OLD_IMPLEMENTATION
# ################################################################################
#
#
# Result = Tuple[Optional[ast.AST], State]
# Transition = Callable[[ast.AST], Result]
#
#
# @dataclass(eq=False, frozen=True)
# class _NodeFSM:
#     __slots__ = 'state_table'
#     state_table: Dict[State, Transition]
#
#     def __call__(self, node: ast.AST, state: State) -> Result:
#         return self.state_table[state](node)
#
#
# FSMTrack = Dict[_NodeFSM, Set[State]]
#
#
# def _elem_name(elm: PatternElem) -> str:
#     return elm.__class__.__name__ if isinstance(elm, ast.AST) else elm.__name__
#
#
# def _calls(inst: object) -> Generator[Callable, None, None]:
#     return (v for v in inst.__class__.__dict__.values() if callable(v))
#
#
# @dataclass
# class OR:
#     __slots__ = 'values'
#
#     def __init__(self, *values: Any):
#         self.values = list(values)
#
#
# class _NonValue:
#     pass
#
#
# _NON_VALUE = _NonValue()
#
#
# def _n_attrs(node: ast.AST) -> Dict[str, List[Any]]:
#     return {attr: v.values if isinstance(v, OR) else [v]
#             for attr, v in ast.iter_fields(node)}
#
#
# def _has_children(node: ast.AST) -> bool:
#     return next((True for _ in ast.iter_child_nodes(node)), False)
#
#
# def _no_children(node: ast.AST) -> bool:
#     return next((False for _ in ast.iter_child_nodes(node)), True)
#
#
# def _apply_all(node: ast.AST, fs: List[ASTPredicate]) -> bool:
#     return all(f(node) for f in fs)
#
#
# def _check_class(node: ast.AST, name: str) -> bool:
#     return node.__class__.__name__ == name
#
#
# def _check_class_not(node: ast.AST, name: str) -> bool:
#     return node.__class__.__name__ != name
#
#
# def _check_attrs(node: ast.AST, filters: Dict[str, List[Any]]) -> bool:
#     for attr, values in filters.items():
#         if getattr(node, attr, _NonValue) not in values:
#             return False
#     return True
#
#
# def _check_attrs_not(node: ast.AST, filters: Dict[str, List[Any]]) -> bool:
#     for attr, values in filters.items():
#         if getattr(node, attr, _NonValue) not in values:
#             return True
#     return False
#
#
# def _check_children_loop(node: ast.AST, state: State, ts: List[Transition]) -> bool:
#     if not ts:
#         # Nothing left to check, therefore check succeeded
#         return True
#     # Discard any node mutations
#     _, new_state = ts[0](node)
#     if new_state == START:
#         # A transition condition failed, therefore check failed
#         return False
#     children = list(ast.iter_child_nodes(node))
#     if new_state == state:
#         # Retry 'Until' we fulfil current condition or hit end of branch
#         return any(_check_children_loop(n, state, ts) for n in children)
#     if not ts[1:] and not children:
#         # Return early to avoid calling any() with empty iterable as
#         # this returns False regardless of empty conditions list
#         return True
#     return any(_check_children_loop(n, new_state, ts[1:]) for n in children)
#
#
# def _check_children(node: ast.AST, state: State, ts: List[Transition]) -> bool:
#     children = ast.iter_child_nodes(node)
#     return any(_check_children_loop(n, state, ts) for n in children)
#
#
# def _transition_visit(node: ast.AST, cond: ASTPredicate, true: State,
#                       false: State, visitor: ASTOptMutate) -> Result:
#     return (visitor(node), true) if cond(node) else (node, false)
#
#
# def _transition(node: ast.AST, cond: ASTPredicate,
#                 true: State, false: State) -> Result:
#     return (node, true) if cond(node) else (node, false)
#
#
# def as_ast_pred(call: Union[Callable, partial]) -> ASTPredicate:
#     return as_typ(ASTPredicate, call)
#
#
# def _check_identity(node: PatternElem) -> List[ASTPredicate]:
#     pass
#
#
# UnaryOp = Callable[[bool], bool]
# BinaryOp = Callable[[bool, bool], bool]
# ElemOp = Union[UnaryOp, BinaryOp, ASTPredicate]
#
#
# @dataclass
# class ElemCondition:
#     __slots__ = 'op'
#     op: ElemOp
#
#     def __call__(self, elem: Union[PatternElem, List[ElemOp]]) -> List[ElemOp]:
#         if isinstance(elem, list):
#             elem.append(self.op)
#             return elem
#         else:
#             return [*_check_identity(elem), self.op]
#
#
# NoChild2 = ElemCondition(_no_children)
# Not2 = ElemCondition(operator.not_)
#
#
# @dataclass(eq=False)
# class TransitionFactory:
#     elem: PatternElem
#     state: State
#     ahead: Optional[List[Transition]] = None
#     visitor: Optional[ASTOptMutate] = None
#
#     def __post_init__(self):
#         self.if_cond: State = self.state + 1 if self.visitor is None else START
#         self.not_cond: State = START
#         self.node_not: bool = False
#         self.conditions: List[ASTPredicate] = []
#         # Apply any modifications to the factory, this
#         # expression MUST occur at this point in __post_init__
#         if isinstance(self.elem, ModTransition):
#             self.elem: PatternElem = self.elem.modify(self)
#
#         if self.elem is not ast.AST:
#             if isinstance(self.elem, ast.AST) and _n_attrs(self.elem):
#                 check_class = partial(_check_class, name=_elem_name(self.elem))
#                 attr_func = _check_attrs_not if self.node_not else _check_attrs
#                 check_attrs = partial(attr_func, filters=_n_attrs(self.elem))
#                 self.conditions.extend([as_ast_pred(check_class), as_ast_pred(check_attrs)])
#             else:
#                 name_func = _check_class_not if self.node_not else _check_class
#                 check_class = partial(name_func, name=_elem_name(self.elem))
#                 self.conditions.append(as_ast_pred(check_class))
#
#         if self.ahead:
#             check_children = partial(_check_children, state=self.state, ts=self.ahead)
#             self.conditions.append(as_ast_pred(check_children))
#
#     def make(self) -> Transition:
#         condition = partial(_apply_all, fs=self.conditions)
#
#         if self.visitor is None:
#             transition = partial(_transition,
#                                  cond=condition,
#                                  true=self.if_cond,
#                                  false=self.not_cond)
#         else:
#             transition = partial(_transition_visit,
#                                  cond=condition,
#                                  true=self.if_cond,
#                                  false=self.not_cond,
#                                  visitor=self.visitor)
#
#         return as_typ(Transition, transition)
#
#
# @dataclass(eq=False)
# class ModTransition(ast.AST):
#     __slots__ = 'elem'
#     elem: PatternElem
#
#     def _modify(self, factory: TransitionFactory) -> None:
#         raise NotImplementedError
#
#     def modify(self, factory: TransitionFactory) -> PatternElem:
#         self._modify(factory)
#         if isinstance(self.elem, ModTransition):
#             return self.elem.modify(factory)
#         return self.elem
#
#
# class Until(ModTransition):
#     def _modify(self, factory: TransitionFactory) -> None:
#         factory.not_cond = factory.state
#
#
# class NoChild(ModTransition):
#     def _modify(self, factory: TransitionFactory) -> None:
#         factory.conditions.append(_no_children)
#
#
# class HasChild(ModTransition):
#     def _modify(self, factory: TransitionFactory) -> None:
#         factory.conditions.append(_has_children)
#
#
# class NodeNot(ModTransition):
#     def _modify(self, factory: TransitionFactory) -> None:
#         factory.node_not = True
#
#
# def _make_fsm(pattern: List[PatternElem], visitor: ASTOptMutate, at: int) -> _NodeFSM:
#     _ahead = (tup for tup in enumerate(pattern[at:], at + 1))
#     ahead = [TransitionFactory(elem, state).make() for state, elem in _ahead]
#     state_table: Dict[State, Transition] = {}
#     for state, elem in enumerate(pattern[:at]):
#         if state + 1 == at:
#             state_table[state] = TransitionFactory(elem, state, ahead, visitor).make()
#         else:
#             state_table[state] = TransitionFactory(elem, state).make()
#     return _NodeFSM(state_table)
#
#
# @dataclass(eq=False)
# class _VisitorParams:
#     __slots__ = 'pattern', 'at', 'init_name'
#     pattern: List[PatternElem]
#     at: int
#
#     def __post_init__(self):
#         self.init_name = _elem_name(self.pattern[0])
#
#
# def _iter_fsm_dicts(*fsm_dicts: FSMTrack) -> Generator[Tuple[_NodeFSM, State], None, None]:
#     for fsm_dict in fsm_dicts:
#         for fsm, state_set in fsm_dict.items():
#             for state in state_set:
#                 yield fsm, state
#
#
# class NodePatternVisitor:
#     def __init__(self):
#         self._all_fsm = self._make_all_fsm()
#         self._wild_card_fsm = self._all_fsm.pop(ast.AST.__name__, {})
#
#     def _make_all_fsm(self) -> Dict[str, FSMTrack]:
#         fsm_dict: Dict[str, FSMTrack] = defaultdict(as_typ('Callable[..., FSMTrack]', dict))
#         for func in _calls(self):
#             if hasattr(func, VISIT_ATTR):
#                 params: _VisitorParams = getattr(func, VISIT_ATTR)
#                 visit_func = as_typ('ASTOptMutate', partial(func, self))
#                 fsm = _make_fsm(params.pattern, visit_func, params.at)
#                 fsm_dict[params.init_name].update({fsm: {START}})
#         return fsm_dict
#
#     def visit(self, node: ast.AST):
#         return self._visit(node, fsm_dict=defaultdict(set))
#
#     def _visit(self, node: ast.AST, fsm_dict: FSMTrack) -> Optional[Union[ast.AST, list]]:
#         node_name = node.__class__.__name__
#         updated: Dict[_NodeFSM, Set[State]] = defaultdict(set)
#         init_fsm_dict = self._all_fsm.get(node_name, {})
#         for fsm, state in _iter_fsm_dicts(fsm_dict, init_fsm_dict, self._wild_card_fsm):
#             _node, new_state = fsm(node, state)
#             if _node is None:
#                 return None
#             else:
#                 node = _node
#             if new_state != START:
#                 updated[fsm].add(new_state)
#         return self._visit_loop(node, updated)
#
#     def _visit_loop(self, node: ast.AST, fsm_dict: FSMTrack):
#         if node is not None:
#             for field, value in ast.iter_fields(node):
#                 if isinstance(value, list):
#                     for item in value:
#                         if isinstance(item, ast.AST):
#                             self._visit(item, fsm_dict)
#                 elif isinstance(value, ast.AST):
#                     self._visit(value, fsm_dict)
#
#
# class NodePatternTransformer(NodePatternVisitor):
#     def _visit_loop(self, node: ast.AST, fsm_dict: FSMTrack):
#         if node is not None:
#             for field, old_value in ast.iter_fields(node):
#                 if isinstance(old_value, list):
#                     new_values: List[Union[ast.AST, Any]] = []
#                     for value in old_value:
#                         if isinstance(value, ast.AST):
#                             value = self._visit(value, fsm_dict)
#                             if value is None:
#                                 continue
#                             elif not isinstance(value, ast.AST):
#                                 new_values.extend(value)
#                                 continue
#                         new_values.append(value)
#                     old_value[:] = new_values
#                 elif isinstance(old_value, ast.AST):
#                     new_node = self._visit(old_value, fsm_dict)
#                     if new_node is None:
#                         delattr(node, field)
#                     else:
#                         setattr(node, field, new_node)
#         return node
#
#
# class NodePatternPrinter(NodePatternVisitor):
#     def __init__(self):
#         self.all = []
#         super(NodePatternPrinter, self).__init__()
#
#     # @visit(ast.AST, ast.ClassDef, at=1)
#     # def before_class(self, node: ast.AST):
#     #     print('before class def', node)
#     #     return node
#     #
#     # @visit(ast.Module, ast.AST)
#     # def after_module(self, node: ast.AST):
#     #     print('after module', node)
#     #     return node
#     #
#     # @visit(ast.ClassDef, ast.AST)
#     # def after_class(self, node: ast.AST):
#     #     print('after class', node)
#     #     return node
#
#     @visit(ast.AST)
#     def all(self, node: ast.AST):
#         self.all.append(node.__class__.__name__)
#         return node
#
#     @visit(ast.FunctionDef, Until(ast.Assign), Until(NoChild(ast.AST)), at=2)
#     def pa(self, node: ast.AST):
#         print('Until', node)
#         return node
#
#     @visit(ast.Module, ast.ClassDef, ast.AnnAssign, ast.Call, ast.Name(id='CV'), at=3)
#     def print_node(self, node: ast.AnnAssign):
#         print('works', node, node.annotation.id)  # type: ignore
#         return node
#
#     @visit(ast.Module, ast.AST, ast.AnnAssign, ast.AST, ast.Name(id='CV'), at=3)
#     def print_node2(self, node: ast.AnnAssign):
#         print('works 2', node, node.annotation.id)  # type: ignore
#         return node
#
#     @visit(ast.Call, ast.Name(id='CV'))
#     def a(self, node: ast.Name):
#         print('name', node, node.id)
#         return node
#
#     @visit(ast.FunctionDef, ast.Name(id='cached property'), ast.Load, at=1)
#     def fd(self, node: ast.FunctionDef):
#         astpretty.pprint(node)
#         print(node.name, node.decorator_list)
#         return node
#
#     # @visit(ast.Assign)
#     # def pretty(self, node: ast.Assign):
#     #     astpretty.pprint(node)
#     #     return node
#
#     @visit(ast.Assign, ast.Num)
#     def print_assign_num(self, node: ast.Num):
#         print('Assign Num', node.n)
#         return node
#
#     @visit(ast.Assign, ast.Str)
#     def print_assign_str(self, node: ast.Str):
#         print('Assign Str', node.s)
#         return node
#
#     # @visit(ast.Module, ast.ClassDef, ast.FunctionDef(name='__new__'))
#     # def print_new(self, node: ast.FunctionDef):
#     #     astpretty.pprint(node)
#     #     return node
#
#
# def configuration2(_cls):
#     cls_ast = ast.parse(inspect.getsource(_cls), mode='exec')
#     print()
#     context = {}
#     npp = NodePatternPrinter()
#     npp.visit(cls_ast)
#     print(npp.all)
#     exec(compile(cls_ast, '<ast>', mode='exec'), globals(), context)
#
#     astpretty.pprint(cls_ast)
#     return context[_cls.__name__]
#
#
# def cached_property(method) -> property:
#     return property(lru_cache(maxsize=1)(method))
#
#
# class CV:
#     def __init__(self, *args, **kwargs):
#         pass
#
#
# class Conf:
#     def __init__(self, d):
#         self.d = d
#
#     # noinspection PyMethodMayBeStatic,PyUnusedLocal
#     def get_as(self, *args, **kwargs):
#         return 10
#
#
# conf = Conf({'a': 10})
#
#
# # noinspection PyUnusedLocal
# @configuration2
# class AA:
#     aa: int = CV(path='aa')
#     bb = conf.get_as(typ=int, path='a')
#     xx: bool = bool(0)
#     v = 5
#
#     class NN:
#         bb: str = CV(path='bb')
#         w = 'hi'
#
#     def __init__(self, d: bool, ll: int = 99):
#         self.b: str = 'hi'
#         self.d = d
#         cc: int = 10
#         self.ccc = conf.get_as(typ=int, path='a')
#         self.ll: int = ll
#
#         def something(*, x: int = 88, **k):
#             pass
#
#     def __new__(cls, *args, **kwargs):
#         return super().__new__(cls)
#
#     @cached_property
#     def dd(self):
#         jj = 1 + 10
#         return self.d
#
#
# # if __name__ == '__main__':
# #     a_v = AA(d=False).b
# #     pass
