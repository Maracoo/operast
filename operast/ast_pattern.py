
__all__ = ["ASTElem", "Tag", "ast_equals", "ast_repr", "to_pattern"]

import ast
from itertools import zip_longest
from operast.pattern import *
from typing import Any, Iterator, List, Optional, Set, Tuple, Type, Union


AnyAST = Union[ast.AST, Type[ast.AST]]


class Tag:
    __slots__ = "field", "node"

    def __init__(self, field: str, node: AnyAST) -> None:
        if not (isinstance(node, ast.AST)
                or isinstance(node, type) and issubclass(node, ast.AST)):
            raise ValueError(f"node must be an instance of AST or Type[AST]; found: {node}")
        self.field = field
        self.node = node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented
        return self.field == other.field and ast_equals(self.node, other.node)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Tag('{self.field}', {ast_repr(self.node)})"


ASTElem = Union[AnyAST, Tag]


# noinspection PyProtectedMember
def get_all_ast_fields() -> Set[str]:
    return {field for obj in ast.__dict__.values() if isinstance(obj, type) and
            issubclass(obj, ast.AST) for field in obj._fields}


PY_AST_FIELDS = get_all_ast_fields()


def iter_ast(node: ast.AST) -> Iterator[Tuple[str, Any]]:
    yield from ((k, v) for k, v in node.__dict__.items() if k in PY_AST_FIELDS)


def ast_fields(node: ast.AST) -> List[Tuple[str, Any]]:
    return [(k, v) for k, v in node.__dict__.items() if k in PY_AST_FIELDS]


Blah = Union[ASTElem, TreePattern, Operator, list, Any]


def tag_elem(elem: Blah, name: Optional[str] = None) -> Blah:
    if name is None:
        return elem
    elif isinstance(elem, Tag):
        return elem
    elif isinstance(elem, TreePattern):
        pat_range = 1 if isinstance(elem, Branch) else len(elem.elems)
        for i in range(pat_range):
            sub_elem = elem.elems[i]
            if isinstance(sub_elem, TreePattern):
                tag_elem(sub_elem, name)
            else:
                elem.elems[i] = Tag(name, sub_elem)
        return elem
    else:
        return Tag(name, elem)


def ast_type_to_pattern(elem: Type[ast.AST], name: Optional[str] = None) -> Tuple[Type[ast.AST], Optional[Any]]:
    return tag_elem(elem, name), None


def ast_to_pattern(elem: ast.AST, name: Optional[str] = None) -> Tuple[ast.AST, Optional[Any]]:
    and_elems = []
    for field, attr in ast_fields(elem):
        opt_pat, opt_any = _to_pattern(attr, field)
        if opt_pat is not None:
            and_elems.append(opt_pat)
        if opt_any is None:
            delattr(elem, field)
    tagged = tag_elem(elem, name)
    result = Branch(tagged, And(*and_elems)) if and_elems else tagged
    return result, None


def tag_to_pattern(elem: Tag) -> Tuple[Tag, Optional[Any]]:
    res, _ = _to_pattern(elem.node)
    assert res is not None
    return tag_elem(res, elem.field), None


def tree_pattern_to_pattern(elem: TreePattern) -> Tuple[TreePattern, Optional[Any]]:
    for i, sub_elem in enumerate(elem.elems):
        res, _ = _to_pattern(sub_elem)
        assert res is not None
        elem.elems[i] = res
    return elem, None


def operator_to_pattern(elem: Operator, name: Optional[str] = None) -> Tuple[Operator, Optional[Any]]:
    res, _ = _to_pattern(elem.elem)
    assert res is not None
    elem.elem = res
    return tag_elem(elem, name), None


def list_to_pattern(elem: list, name: Optional[str] = None) -> Tuple[Optional[Then], Optional[Any]]:
    then_elems = []
    offset = 0
    for i in range(len(elem)):
        opt_pat, opt_any = _to_pattern(elem[offset+i], name)
        if opt_pat is not None:
            then_elems.append(opt_pat)
        if opt_any is None:
            del elem[offset+i:offset+i+1]
            offset -= 1
    any_res = elem if elem else None
    result = Then(*then_elems) if then_elems else None
    return result, any_res


def _to_pattern(elem: Any, name: Optional[str] = None) -> Tuple[Optional[TreeElem[ASTElem]], Optional[Any]]:
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return ast_type_to_pattern(elem, name)
    elif isinstance(elem, ast.AST):
        return ast_to_pattern(elem, name)
    elif isinstance(elem, Tag):
        return tag_to_pattern(elem)
    elif isinstance(elem, TreePattern):
        return tree_pattern_to_pattern(elem)
    elif isinstance(elem, Operator):
        return operator_to_pattern(elem, name)
    elif isinstance(elem, list):
        return list_to_pattern(elem, name)
    else:
        return None, elem


def to_pattern(elem: TreeElem[ASTElem]) -> TreeElem[ASTElem]:
    result, _ = _to_pattern(elem)
    assert result is not None
    return result


def ast_equals(elem_a: AnyAST, elem_b: AnyAST) -> bool:
    if isinstance(elem_a, ast.AST) and isinstance(elem_b, ast.AST):
        zipped = zip_longest(iter_ast(elem_a), iter_ast(elem_b), fillvalue=None)
        return type(elem_a) is type(elem_b) and all(i == j for i, j in zipped)
    return elem_a is elem_b


def ast_repr(elem: AnyAST) -> str:  # pragma: no cover
    if isinstance(elem, ast.AST):
        field_reprs = ', '.join(f'{f}={repr(v)}' for f, v in iter_ast(elem))
        return f'{type(elem).__name__}({field_reprs})'
    return elem.__name__


__EXTENSIONS.update({
    ast.AST: {
        EXT_EQUALS: ast_equals,
        EXT_REPR: ast_repr,
    }
})
