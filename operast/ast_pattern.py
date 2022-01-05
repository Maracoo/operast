
__all__ = ["ASTElem", "Tag"]

import ast
from itertools import zip_longest
from operast.pattern import *
from typing import Any, Iterator, List, Optional, Set, Tuple, Type, Union


AnyAST = Union[ast.AST, Type[ast.AST]]


class Tag:
    __slots__ = "field", "node"

    def __init__(self, field: str, node: AnyAST) -> None:
        self.field = field
        self.node = node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented
        return self.field == other.field and ast_equals(self.node, other.node)

    def __repr__(self) -> str:
        return f"Tag('{self.field}', {ast_repr(self.node)})"

    def te_expand(self) -> TreeElem['Tag']:
        expanded = ast_expand(self.node)
        if isinstance(expanded, TreePattern):
            return pushdown_fieldname(self.field, expanded)
        self.node = expanded
        return self


setattr(Tag, EXT_EQUALS, Tag.__eq__)
setattr(Tag, EXT_REPR, Tag.__repr__)


ASTElem = Union[AnyAST, Tag]


# noinspection PyProtectedMember
def get_all_ast_fields() -> Set[str]:
    return {field for obj in ast.__dict__.values() if isinstance(obj, type) and
            issubclass(obj, ast.AST) for field in obj._fields}


PY_AST_FIELDS = get_all_ast_fields()


def iter_ast(node: ast.AST) -> Iterator[Tuple[str, Any]]:
    yield from ((k, v) for k, v in node.__dict__.items() if k in PY_AST_FIELDS)


def pushdown_fieldname(name: str, elem: TreeElem[ASTElem]) -> TreeElem[ASTElem]:
    if isinstance(elem, (ast.AST, type)):
        return name, elem
    if isinstance(elem, Tag):
        return elem
    if isinstance(elem, StateEff):
        elem.elem = Tag(name, elem.elem)
        return elem
    else:
        pat_range = 1 if isinstance(elem, Branch) else len(elem.elems)
        for i in range(pat_range):
            elem = elem.elems[i]
            if isinstance(elem, TreePattern):
                pushdown_fieldname(name, elem)
            else:
                elem.elems[i] = Tag(name, elem)
        return elem


def ast_expand_cases(name: str, item: Any) -> Optional[TreeElem[ASTElem]]:
    if isinstance(item, ast.AST):
        pat = ast_fields_expand(item)
        return Tag(name, item) if pat is None else Branch(Tag(name, item), pat)
    if isinstance(item, (type, TreePattern, StateEff)):
        return pushdown_fieldname(name, item)
    return None


def ast_fields_expand(node: ast.AST) -> Optional['TreePattern']:
    # possible elements inside the fields of an AST node:
    # ast.AST, Type[ast.AST], BranchPattern
    and_elements: List[TreeElem[ASTElem]] = []
    for name, field in iter_ast(node):
        if isinstance(field, list):
            then_elements = []
            offset = 0
            for i, item in enumerate(field):
                expanded: Optional[TreeElem[ASTElem]] = ast_expand_cases(name, item)
                if expanded is not None:
                    then_elements.append(expanded)
                    del field[offset+i:offset+i+1]
                    offset -= 1
            if then_elements:
                and_elements.append(Then(*then_elements))
                if not field:
                    delattr(node, name)
        else:
            expanded = ast_expand_cases(name, field)
            if expanded is not None:
                and_elements.append(expanded)
                delattr(node, name)
    if and_elements:
        return And(*and_elements)
    return None


def ast_expand(elem: AnyAST) -> TreeElem[AnyAST]:
    if isinstance(elem, ast.AST):
        pat = ast_fields_expand(elem)
        return elem if pat is None else Branch(elem, pat)
    return elem


def ast_equals(elem_a: AnyAST, elem_b: AnyAST) -> bool:
    if isinstance(elem_a, ast.AST) and isinstance(elem_b, ast.AST):
        zipped = zip_longest(iter_ast(elem_a), iter_ast(elem_b), fillvalue=None)
        return type(elem_a) is type(elem_b) and all(i == j for i, j in zipped)
    return elem_a is elem_b


def ast_repr(elem: AnyAST) -> str:
    if isinstance(elem, ast.AST):
        field_reprs = ', '.join(f'{f}={repr(v)}' for f, v in iter_ast(elem))
        return f'{type(elem).__name__}({field_reprs})'
    return elem.__name__


__EXTENSIONS.update({
    ast.AST: {
        EXT_EXPAND: ast_expand,
        EXT_EQUALS: ast_equals,
        EXT_REPR: ast_repr,
    }
})
