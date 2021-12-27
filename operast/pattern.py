
__all__ = ["And", "Branch", "Or", "StateEff", "Then"]

import ast
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union


# noinspection PyProtectedMember
def get_all_ast_fields() -> Set[str]:
    return {field for obj in ast.__dict__.values() if isinstance(obj, type) and
            issubclass(obj, ast.AST) for field in obj._fields}


PY_AST_FIELDS = get_all_ast_fields()


class StateEff:
    def __init__(self, node: Union[ast.AST, Type[ast.AST]]):
        self.node = node

    def __repr__(self) -> str:
        return f'{type(self).__name__}({branch_repr(self.node)})'


PatternElem = Union[
    ast.AST, Type[ast.AST], StateEff,
    Tuple[str, Union[ast.AST, Type[ast.AST], StateEff]]
]
BranchElem = Union['TreePattern', PatternElem]
BranchExpr = Union[str, List['BranchExpr']]
Aliases = Dict[int, 'Seq']


TP = TypeVar('TP', bound='TreePattern')


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
        return (name, elem) if pat is None else Branch((name, elem), pat)
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
        self.elems: List[BranchElem] = list(elems)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TreePattern) and branch_equals(self, other)

    def __len__(self) -> int:
        return len(self.elems)

    def __iter__(self) -> Iterator[BranchElem]:
        yield from self.elems

    def __getitem__(self, item: int) -> BranchElem:
        return self.elems[item]

    def __setitem__(self, key: int, value: Union[BranchElem, Iterable[BranchElem]]) -> None:
        self.elems[key] = value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(branch_repr(e) for e in self.elems)})"

    # -- Canonical Normal Form --
    # Let f be a function where:
    #   f(x) = Branch(x)    when x is not a TreePattern
    #   f(x) = x            otherwise
    #
    # Then, given T, a TreePattern, F, a fork pattern, and Branch, we have
    # rewrite rules:
    #   1) T(x1, ..., xn, T(y1, ..., yn)) => T(x1, ..., xn, y1, ..., yn)
    #   2) F(x1, ..., xn) => F(f(x1), ..., f(xn))
    #   3) F(x) => Branch(x)
    #   4) Fa(Fb(x1, ..., xn)) => Fb(x1, ..., xn)
    #   5) Branch(x1, ..., xn, F(y1, ..., yn)) =>> F(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    #
    @abstractmethod
    def canonical_nf(self, index: int = 0, *elems: PatternElem) -> 'TreePattern':
        raise NotImplementedError

    # -- Disjunctive Normal Form --
    # Given F, a ForkPattern which is not Or and is in logical normal form, Or,
    # and Bi, a Branch where i ∈ ℕ, we have rewrite rules:
    #   1) B1 => B1
    #   2) F(B1, ..., Bn) => F(B1, ..., Bn)
    #   3) F(B1, Or(B2, B3)) => Or(F(B1, B2), F(B1, B3))
    #   4) Or(B1, Or(B2, B3)) => Or(B1, B2, B3)
    #
    # Note: any implementation must ensure that ForkPattern types where order
    # of elements matters will have that order retained in normalised instances.
    #
    @abstractmethod
    def disjunctive_nf(self: TP) -> Union[TP, 'Or']:
        raise NotImplementedError

    @abstractmethod
    def pushdown_fieldname(self: TP, name: str) -> TP:
        raise NotImplementedError

    @abstractmethod
    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        raise NotImplementedError

    def expand(self) -> 'TreePattern':
        return type(self)(*(branch_expand(e) for e in self.elems))


# Seq is a kind of branch pattern
class Branch(TreePattern):  # rename branch?
    def __init__(self, *elems: BranchElem) -> None:
        super().__init__(*elems)
        if any(isinstance(e, TreePattern) for e in elems[:-1]):
            raise ValueError(f'Seq may only contain one BranchPattern '
                             f'at the end of elems; found: {self}')

    def canonical_nf(self, index: int = 0, *elems: PatternElem) -> TreePattern:
        *seq_elems, last = self.elems
        if isinstance(last, TreePattern):
            return last.canonical_nf(index + len(seq_elems), *elems, *seq_elems)
        self.elems[:0] = elems
        return self

    def disjunctive_nf(self: TP) -> TP:
        return self

    def pushdown_fieldname(self: TP, name: str) -> TP:
        first = self.elems[0]
        if isinstance(first, TreePattern):
            first.pushdown_fieldname(name)
        else:
            self.elems[0] = (name, first)
        return self

    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        alias = len(aliases)
        aliases[alias] = self
        return aliases, f"P{alias}"


class ForkPattern(TreePattern, ABC):
    def __init__(self, *elems: BranchElem) -> None:
        super().__init__(*elems)
        self.index: int = 0

    @classmethod
    def flat(cls: Type[TP], *elems: BranchElem) -> TP:
        return cls(*(a for e in elems for a in (e if type(e) is cls else [e])))

    def canonical_nf(self, index: int = 0, *elems: PatternElem) -> TreePattern:
        self.index = index
        self_elems = self.elems
        offset = 0
        for i in range(len(self_elems)):
            elem = self_elems[i]
            if isinstance(elem, TreePattern):
                normal = elem.canonical_nf(index, *elems)
            else:
                normal = Branch(*elems, elem)
            if type(normal) is type(self):
                self_elems[offset+i:offset+i+1] = normal.elems
                offset += len(normal)
            else:
                self_elems[offset+i] = normal
        if len(self_elems) == 1:
            return self_elems[0]
        return self

    def disjunctive_nf(self: TP) -> Union[TP, 'Or']:
        todo = [(0, self.elems)]
        done = []
        while todo:
            index, elems = todo.pop()
            if index == len(elems):
                done.append(elems)
                continue
            elem = elems[index]
            normal = elem.disjunctive_nf()
            assert not type(normal) is type(self)
            if isinstance(normal, Or):
                for or_elem in normal.elems:
                    new_elems = elems[:]
                    new_elems[index] = or_elem
                    todo.append((index + 1, new_elems))
            else:
                elems[index] = normal
                todo.append((index + 1, elems))
        if len(done) == 1:
            return self
        return Or(*(type(self).flat(*elems) for elems in done))

    def pushdown_fieldname(self: TP, name: str) -> TP:
        for i in range(len(self.elems)):
            elem = self.elems[i]
            if isinstance(elem, TreePattern):
                elem.pushdown_fieldname(name)
            else:
                self.elems[i] = (name, elem)
        return self

    def alias(self, aliases: Aliases) -> Tuple[Aliases, BranchExpr]:
        # expr is an S-Expression
        expr = [f'{type(self).__name__}_{self.index}']
        for elem in self.elems:
            aliases, expr_elem = elem.alias(aliases)
            expr.append(expr_elem)
        return aliases, expr


class And(ForkPattern):
    pass


class Then(ForkPattern):
    pass


class Or(ForkPattern):
    def disjunctive_nf(self) -> 'TreePattern':
        offset = 0
        elems = self.elems
        for i in range(len(elems)):
            normal = elems[i].disjunctive_nf()
            if isinstance(normal, Or):
                elems[offset+i:offset+i+1] = normal.elems
                offset += len(normal)
            else:
                elems[offset+i] = normal
        return self


if __name__ == '__main__':
    # test = Then(Or(Branch(ast.AST), Branch(ast.Name)), Or(Branch(ast.List), Branch(ast.Tuple)))
    # print(test.disjunctive_nf())

    print(Branch(ast.AST, And(Branch(ast.Name), Branch(ast.Load))).canonical_nf())
