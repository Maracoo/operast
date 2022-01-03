
import ast
from itertools import zip_longest
from operast.pattern import EXTENSIONS, TreePattern, StateEff, TreeElem, Branch, And, Then, tree_elem_expand
from typing import Any, Iterator, List, Optional, Set, Tuple, Type, Union


AnyAST = Union[ast.AST, Type[ast.AST]]
ASTElem = Union[AnyAST, Tuple[str, AnyAST]]


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
    if isinstance(elem, tuple):
        return elem
    if isinstance(elem, StateEff):
        elem.elem = (name, elem.elem)
        return elem
    else:
        pat_range = 1 if isinstance(elem, Branch) else len(elem.elems)
        for i in range(pat_range):
            elem = elem.elems[i]
            if isinstance(elem, TreePattern):
                pushdown_fieldname(name, elem)
            else:
                elem.elems[i] = (name, elem)
        return elem


def ast_expand_cases(name: str, item: Any) -> Optional[TreeElem[ASTElem]]:
    if isinstance(item, ast.AST):
        pat = ast_fields_expand(item)
        return (name, item) if pat is None else Branch((name, item), pat)
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


def ast_expand(elem: ASTElem) -> TreeElem[ASTElem]:
    if isinstance(elem, tuple):
        name, node = elem
        expanded = tree_elem_expand(node)
        if isinstance(expanded, TreePattern):
            return pushdown_fieldname(name, expanded)
        return name, expanded
    if isinstance(elem, ast.AST):
        pat = ast_fields_expand(elem)
        return elem if pat is None else Branch(elem, pat)
    if isinstance(elem, type) and issubclass(elem, ast.AST):
        return elem


def ast_equals(elem_a: ASTElem, elem_b: ASTElem) -> bool:
    if isinstance(elem_a, tuple) and isinstance(elem_b, tuple):
        (label_a, node_a), (label_b, node_b) = elem_a, elem_b
        return label_a == label_b and ast_equals(node_a, node_b)
    if isinstance(elem_a, ast.AST) and isinstance(elem_b, ast.AST):
        zipped = zip_longest(iter_ast(elem_a), iter_ast(elem_b), fillvalue=None)
        return type(elem_a) is type(elem_b) and all(i == j for i, j in zipped)
    if isinstance(elem_a, type):
        return elem_a is elem_b
    return False


def ast_repr(elem: ASTElem) -> str:
    if isinstance(elem, tuple):
        label, elem = elem
        return f"('{label}', {ast_repr(elem)})"
    if isinstance(elem, type):
        return elem.__name__
    field_reprs = ', '.join(f'{f}={repr(v)}' for f, v in iter_ast(elem))
    return f'{type(elem).__name__}({field_reprs})'


EXTENSIONS.update({ast.AST: {
    'expand': ast_expand,
    '__eq__': ast_equals,
    '__repr__': ast_repr,
}})
