import ast
import astpretty
import inspect
from typing import Any, Iterator, List, Sequence, Tuple


BranchIndex = Tuple[int, ...]


def iter_child_names_nodes(node: ast.AST) -> Iterator[Tuple[str, ast.AST]]:
    """
    Yield all pairs of (field name, child node) for direct children of *node*.
    I.e., all field names and values where the values are nodes and all items
    of fields that are lists of nodes paired with the name of that field.

    An extension of the std lib ast.iter_child_nodes function.
    """
    for name, field in ast.iter_fields(node):
        if isinstance(field, ast.AST):
            yield name, field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, ast.AST):
                    yield name, item


def index_traverse_nodes(node: ast.AST, index: Tuple[int, ...] = (),
                         pos: int = 1) -> Iterator[Tuple[Tuple[int, ...], ast.AST]]:
    new_index = (*index, pos)
    yield new_index, node
    for breadth, child in enumerate(ast.iter_child_nodes(node), start=1):
        yield from index_traverse_nodes(child, new_index, breadth)


def compare_index_lineage(a: Sequence[int], b: Sequence[int], at: List[int]) -> bool:
    max_index = max(at)
    if max_index > len(a) or max_index > len(b):
        return False
    return all(a[i] == b[i] for i in at)


def digits_gte(a: Sequence[int], b: Sequence[int]) -> bool:
    return all(i >= j for i, j in zip(a, b)) or len(a) >= len(a)


def digits_gt(a: Sequence[int], b: Sequence[int]) -> bool:
    for i, j in zip(a, b):
        if i > j:
            return True
        if i < j:
            return False
    return len(a) > len(b)


def digits_lt(a: Sequence[int], b: Sequence[int]) -> bool:
    for i, j in zip(a, b):
        if i > j:
            return False
        if i < j:
            return True
    return len(a) < len(b)


def blah():
    class A:
        b = 9

        def c(self):
            pass

    A()


def to_ast(x: Any) -> ast.AST:
    return ast.parse(inspect.getsource(x), mode='exec')


def print_ast(obj: Any) -> None:
    _ast = ast.parse(inspect.getsource(obj), mode='exec')
    astpretty.pprint(_ast)
    print(ast.dump(_ast))


def func(x: int) -> str:
    b = ' no '
    a = ' blah'
    c = 9
    return str(x) + a + b + str(c)


if __name__ == '__main__':
    # import math
    # import itertools

    # print_ast(blah)

    some_ast = ast.Module(
        body=[
            ast.FunctionDef(
                name='func',
                args=ast.arguments(
                    args=[
                        ast.arg(arg='x', annotation=ast.Name(id='int', ctx=ast.Load()))
                    ],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[]
                ),
                body=[
                    ast.Assign(targets=[ast.Name(id='b', ctx=ast.Store())], value=ast.Str(s=' no ')),
                    ast.Assign(targets=[ast.Name(id='a', ctx=ast.Store())], value=ast.Str(s=' blah')),
                    ast.Assign(targets=[ast.Name(id='c', ctx=ast.Store())], value=ast.Num(n=9)),
                    ast.Return(
                        value=ast.BinOp(
                            left=ast.BinOp(
                                left=ast.BinOp(
                                    left=ast.Call(
                                        func=ast.Name(id='str', ctx=ast.Load()),
                                        args=[ast.Name(id='x', ctx=ast.Load())],
                                        keywords=[]
                                    ),
                                    op=ast.Add(),
                                    right=ast.Name(id='a', ctx=ast.Load())),
                                op=ast.Add(),
                                right=ast.Name(id='b', ctx=ast.Load())),
                            op=ast.Add(),
                            right=ast.Call(
                                func=ast.Name(id='str', ctx=ast.Load()),
                                args=[ast.Name(id='c', ctx=ast.Load())],
                                keywords=[]
                            )
                        )
                    )
                ],
                decorator_list=[],
                returns=ast.Name(id='str', ctx=ast.Load())
            )
        ]
    )


    def digits_to_number(digits: Sequence[int], radix: int) -> int:
        if radix == 1:
            return len(digits) - 1
        return sum(radix ** i * d for i, d in enumerate(digits[::-1]))


    def number_to_digits_iter(number: int, radix: int) -> Iterator[int]:
        while number > 0:
            (number, digit) = divmod(number, radix)
            yield digit


    def number_to_digits(number: int, radix: int) -> List[int]:
        if radix == 1:
            return [0 for _ in range(number + 1)]
        return list(number_to_digits_iter(number, radix))[::-1]

    # print(number_to_digits(6, 2))

    # cur_max = 1
    # cur_len = 1
    # zeroes = itertools.repeat(0)
    #
    # previous_idx = None
    # previous_num = None
    #
    # for x_idx, x_node in index_traverse_nodes(some_ast):
    #     cur_max = max(cur_max, max(x_idx) + 1)
    #     cur_len = max(cur_len, len(x_idx))
    #
    #     full_idx = list(itertools.islice(itertools.chain(x_idx, zeroes), cur_len))
    #     num = digits_to_number(full_idx, cur_max)
    #
    #     if previous_idx is not None:
    #         print('<', digits_lt(previous_idx, full_idx), previous_num < num)
    #
    #     print(num, full_idx)
    #
    #     previous_idx = full_idx
    #     previous_num = num

    # idx1 = (0, 0, 1, 0, 0)
    # idx2 = (0, 0, 1, 1)
    # print(compare_index_lineage(idx1, idx2, [0, 2, 9]))

    # print(digits_lt([1, 2, 1], [1, 1, 2]))
    # print(digits_to_number([1, 2, 1], 3), digits_to_number([1, 1, 2], 3))
    #
    # print(digits_lt([1, 1, 6], [1, 2, 1]))
    # print(digits_to_number([1, 1, 6], 7), digits_to_number([1, 2, 1], 7))
    #
    # print(digits_lt([1, 1, 6], [1, 1, 6]))
    # print(digits_to_number([1, 1, 6], 7), digits_to_number([1, 1, 6], 7))
    #
    # print(digits_lt([1, 6, 5], [1, 6, 6]))
    # print(digits_to_number([1, 6, 5], 7), digits_to_number([1, 6, 6], 7))
    #
