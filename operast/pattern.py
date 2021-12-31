
__all__ = ["And", "Branch", "Or", "StateEff", "Then"]

import ast
from abc import ABC, abstractmethod
from itertools import product
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Type, Union


# noinspection PyProtectedMember
def get_all_ast_fields() -> Set[str]:
    return {field for obj in ast.__dict__.values() if isinstance(obj, type) and
            issubclass(obj, ast.AST) for field in obj._fields}


PY_AST_FIELDS = get_all_ast_fields()


class StateEff:
    def __init__(self, node: Union[ast.AST, Type[ast.AST]]):
        self.node = node

    def __repr__(self) -> str:
        return f'{type(self).__name__}({tree_elem_repr(self.node)})'


PatternElem = Union[
    ast.AST, Type[ast.AST], StateEff,
    Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
]
TreeElem = Union['TreePattern', PatternElem]
BranchExpr = Union[str, List['BranchExpr']]
Aliases = Dict[str, 'Branch']


def iter_all_ast_fields(node: ast.AST) -> Iterator[Tuple[str, Any]]:
    for field in PY_AST_FIELDS:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def ast_expand_cases(name: str, elem: Any) -> Optional[TreeElem]:
    # case: ast.AST
    if isinstance(elem, ast.AST):
        pat = ast_expand(elem)
        return (name, elem) if pat is None else Branch((name, elem), pat)
    # case: Type[ast.AST]
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return name, elem
    # case: TreePattern
    if isinstance(elem, TreePattern):
        elem.pushdown_fieldname(name)
        return elem.expand()
    # case: StateEff
    if isinstance(elem, StateEff):
        return name, elem
    return None


def ast_expand(node: ast.AST) -> Optional['TreePattern']:
    # possible elements inside the fields of an AST node:
    # ast.AST, Type[ast.AST], BranchPattern
    and_elements = []
    for name, field in iter_all_ast_fields(node):
        if isinstance(field, list):
            then_elements = []
            non_expand_elements = []
            for item in field:
                expanded = ast_expand_cases(name, item)
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
            expanded = ast_expand_cases(name, field)
            if expanded is not None:
                and_elements.append(expanded)
                delattr(node, name)

    if and_elements:
        return And(*and_elements)
    return None


def tree_elem_expand(elem: TreeElem) -> TreeElem:
    # case: Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
    if isinstance(elem, tuple):
        name, node = elem
        expanded = tree_elem_expand(node)
        if isinstance(expanded, TreePattern):
            expanded.pushdown_fieldname(name)
            return expanded
        return name, expanded
    # case: ast.AST
    if isinstance(elem, ast.AST):
        pat = ast_expand(elem)
        return elem if pat is None else Branch(elem, pat)
    # case: Type[ast.AST]
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return elem
    # case: StateEff
    if isinstance(elem, StateEff):
        return elem
    # case: BranchPattern
    if isinstance(elem, TreePattern):
        return elem.expand()


def ast_equals(a: ast.AST, b: ast.AST) -> bool:
    return (type(a) is type(b) and len(a.__dict__) == len(b.__dict__) and
            all(i == j for i, j in zip(iter_all_ast_fields(a), iter_all_ast_fields(b))))


def pattern_elem_equals(a: PatternElem, b: PatternElem) -> bool:
    # case: Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
    if isinstance(a, tuple) and isinstance(b, tuple):
        (label_a, elem_a), (label_b, elem_b) = a, b
        return label_a == label_b and pattern_elem_equals(elem_a, elem_b)
    # case: ast.AST
    if isinstance(a, ast.AST) and isinstance(b, ast.AST):
        return ast_equals(a, b)
    # case: Type[ast.AST]
    if isinstance(a, type) and isinstance(b, type):
        return a is b
    # case: StateEff
    if isinstance(a, StateEff) and isinstance(b, StateEff):
        return ast_equals(a.node, b.node)
    return False


def tree_elem_equals(a: TreeElem, b: TreeElem) -> bool:
    if isinstance(a, TreePattern):
        return (type(a) is type(b) and len(a) == len(b) and
                all(tree_elem_equals(i, j) for i, j in zip(a, b)))
    return pattern_elem_equals(a, b)


def ast_repr(node: ast.AST) -> str:
    field_reprs = ', '.join(f'{f}={repr(v)}' for f, v in iter_all_ast_fields(node))
    return f'{type(node).__name__}({field_reprs})'


def tree_elem_repr(a: TreeElem) -> str:
    if isinstance(a, TreePattern) or isinstance(a, StateEff):
        return repr(a)
    if isinstance(a, tuple):
        label, elem = a
        return f"('{label}', {tree_elem_repr(elem)})"
    if isinstance(a, ast.AST):
        return ast_repr(a)
    if isinstance(a, type):
        return a.__name__
    return ''


class TreePattern(ABC):
    __slots__ = 'elems',

    def __init__(self, *elems: TreeElem) -> None:
        if not elems:
            raise ValueError(f"{type(self).__name__} cannot be empty.")
        self.elems: List[TreeElem] = list(elems)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TreePattern) and tree_elem_equals(self, other)

    def __len__(self) -> int:
        return len(self.elems)

    def __iter__(self) -> Iterator[TreeElem]:
        yield from self.elems

    def __getitem__(self, item: int) -> TreeElem:
        return self.elems[item]

    def __setitem__(self, key: int, value: Union[TreeElem, Iterable[TreeElem]]) -> None:
        self.elems[key] = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(tree_elem_repr(e) for e in self.elems)})"

    # -- Canonical Normal Form --
    # Let f be a function where:
    #   f(x) = Branch(x)    when x is not a TreePattern
    #   f(x) = x            otherwise
    #
    # Let x, y ∈ TreeElem, and let n ∈ ℕ.
    # Let Ta, Tb, ... ∈ TreePattern, and let Fa, Fb, ... ∈ ForkPattern.
    # Then, given concrete TreePattern classes Branch, And, Then and Or, we
    # have rewrite rules:
    #
    #   1) Branch(x1, ..., xn, Branch(y1, ..., yn)) => Branch(x1, ..., xn, y1, ..., yn)
    #   2) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    #   3) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    #   4) Fa(x) => Branch(x)
    #   5) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index == Fb.index V Fa is Or and Fb is Or
    #   6) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    #   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
    #   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
    #
    @abstractmethod
    def canonical_nf(self, index: int = 0, *elems: TreeElem) -> 'TreePattern':
        raise NotImplementedError

    @abstractmethod
    def pushdown_fieldname(self, name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        raise NotImplementedError

    def expand(self) -> 'TreePattern':
        return type(self)(*(tree_elem_expand(e) for e in self.elems))


class Branch(TreePattern):
    __slots__ = "id",
    count: int = 0

    def __init__(self, *elems: TreeElem) -> None:
        super().__init__(*elems)
        self.id = f"B{Branch.count}"
        Branch.count += 1
        if any(isinstance(e, TreePattern) for e in elems[:-1]):
            raise ValueError(f'Seq may only contain one BranchPattern '
                             f'at the end of elems; found: {self}')

    def canonical_nf(self, index: int = 0, *elems: TreeElem) -> TreePattern:
        *fst_elems, last = self.elems
        if isinstance(last, TreePattern):
            return last.canonical_nf(index + len(fst_elems), *elems, *fst_elems)
        self.elems[:0] = elems
        return self

    def pushdown_fieldname(self, name: str) -> None:
        first = self.elems[0]
        if isinstance(first, TreePattern):
            first.pushdown_fieldname(name)
        else:
            self.elems[0] = (name, first)

    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        aliases[self.id] = self
        return aliases, self.id


class ForkPattern(TreePattern, ABC):
    __slots__ = "index",

    def __init__(self, *elems: TreeElem) -> None:
        super().__init__(*elems)
        self.index: int = 0

    def canonical_nf(self, index: int = 0, *elems: TreeElem) -> TreePattern:
        self.index = index
        includes_or = False
        self_elems = self.elems
        offset = 0
        for i in range(len(self_elems)):
            elem = self_elems[i]
            if isinstance(elem, TreePattern):
                normal = elem.canonical_nf(index, *elems)
                if isinstance(normal, type(self)) and normal.index == self.index:
                    self_elems[offset+i:offset+i+1] = normal.elems
                    offset += len(normal)
                else:
                    self_elems[offset+i] = normal
                    if isinstance(normal, Or):
                        includes_or = True
            else:
                self_elems[offset+i] = Branch(*elems, elem)
        if len(self_elems) == 1:
            return self_elems[0]
        if includes_or:
            return Or(*self.disjunctive_normalise())
        return self

    def disjunctive_normalise(self) -> Iterator[TreePattern]:
        splat_or = (e.elems if isinstance(e, Or) else [e] for e in self.elems)
        for elems in product(*splat_or):
            new = type(self)(*elems)
            new.index = self.index
            offset = 0
            for i in range(len(new.elems)):
                elem = new.elems[offset+i]
                if isinstance(elem, type(self)) and elem.index == self.index:
                    new.elems[offset+i:offset+i+1] = elem.elems
                    offset += len(elem)
            yield new

    def pushdown_fieldname(self, name: str) -> None:
        for i, elem in enumerate(self.elems):
            if isinstance(elem, TreePattern):
                elem.pushdown_fieldname(name)
            else:
                self.elems[i] = (name, elem)

    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        # expr is an S-Expression
        expr = [f'{type(self).__name__}_{self.index}']
        for elem in self.elems:
            aliases, expr_elem = elem.alias(aliases)
            # expr.append(expr_elem)
        return aliases, expr


class And(ForkPattern):
    pass


class Then(ForkPattern):
    pass


class Or(ForkPattern):
    def canonical_nf(self, index: int = 0, *elems: TreeElem) -> TreePattern:
        self_elems = self.elems
        offset = 0
        for i in range(len(self_elems)):
            elem = self_elems[i]
            if isinstance(elem, TreePattern):
                normal = elem.canonical_nf(index, *elems)
                if isinstance(normal, Or):
                    self_elems[offset+i:offset+i+1] = normal.elems
                    offset += len(normal)
                else:
                    self_elems[offset+i] = normal
            else:
                self_elems[offset+i] = Branch(*elems, elem)
        if len(self_elems) == 1:
            return self_elems[0]
        return self
