import ast
import pytest
from operast import operast2
from operast.operast2 import *
from typing import Any


def test_scope_set_actions():
    scope = Scope()

    def ast_op1() -> ast.AST:
        return ast.FunctionDef()

    def ast_op2() -> ast.AST:
        return ast.ClassDef()

    scope.action = ast_op1

    with pytest.raises(AttributeError):
        scope.action = ast_op2

    result = isinstance(scope.action(), ast.FunctionDef)
    assert result


def test_boolean_expression():
    filter_node = ast.Name(id=BX(lambda v, _scope: v == "big_name"))
    filters = operast2._get_filter_attrs(filter_node)

    test_node_true = ast.Name(id="big_name")
    test_node_false = ast.Name(id="small_name")

    result1 = operast2._check_attrs(test_node_true, scope=Scope(), filters=filters)
    assert result1

    result2 = operast2._check_attrs(test_node_false, scope=Scope(), filters=filters)
    assert not result2


def test_let_expression():
    filter_node = ast.Name(id=Let("name"))
    filters = operast2._get_filter_attrs(filter_node)

    test_node = ast.Name(id="success")
    scope = Scope()

    operast2._check_attrs(test_node, scope=scope, filters=filters)
    assert "name" in scope.context["id"] and scope.context["id"]["name"] == "success"


def test_sub_expression():
    filter_node = ast.Name(id=Sub("name"))
    filters = operast2._get_filter_attrs(filter_node)

    test_node_true = ast.Name(id="success")
    test_node_false = ast.Name(id="fail")
    scope = Scope(context={"id": {"name": "success"}})

    result1 = operast2._check_attrs(test_node_true, scope=scope, filters=filters)
    assert result1

    result2 = operast2._check_attrs(test_node_false, scope=scope, filters=filters)
    assert not result2


def test_equals_expression():
    filter_node = ast.Name(id="success")
    filters = operast2._get_filter_attrs(filter_node)

    test_node_true = ast.Name(id="success")
    test_node_false = ast.Name(id="fail")

    result1 = operast2._check_attrs(test_node_true, scope=Scope(), filters=filters)
    assert result1

    result2 = operast2._check_attrs(test_node_false, scope=Scope(), filters=filters)
    assert not result2


def test_has_children():
    has_children = ast.FunctionDef(name="a", body=ast.FunctionDef(name="b"))

    result1 = operast2._has_children(has_children, Scope())
    assert result1

    no_children = ast.FunctionDef(name="a")
    result2 = operast2._has_children(no_children, Scope())

    assert not result2


def test_check_class():
    node = ast.Name()

    result1 = operast2._check_class(node, Scope(), ast.expr)
    assert result1

    result2 = operast2._check_class(node, Scope(), ast.AST)
    assert result2

    result3 = operast2._check_class(node, Scope(), ast.operator)
    assert not result3


def test_compose_n():
    def outer_func(num1: int, num2: int) -> int:
        return sum([num1, num2])

    def inner_func1(num: int) -> int:
        return num * 3

    def inner_func2(num: int) -> int:
        return num + 3

    composed = operast2.compose_n(outer_func, inner_func1, inner_func2)
    result = composed(num=2)

    assert result == 11


def test_conjoin_n():
    def func1(num: int) -> bool:
        return num > 3

    def func2(num: int) -> bool:
        return num < 6

    def func3(num: int) -> bool:
        return num != 5

    conjoined = operast2.conjoin_n(func1, func2, func3)

    result1 = conjoined(num=4)
    assert result1

    result2 = conjoined(num=10)
    assert not result2

    result3 = conjoined(num=2)
    assert not result3

    result4 = conjoined(num=5)
    assert not result4


def test_node_identity():
    # noinspection PyUnusedLocal
    def name_in_set(value: Any, scope: Scope) -> bool:
        return value in {"func1", "func2"}

    identity_func1 = operast2.node_identity(ast.FunctionDef(name=BX(name_in_set)))
    identity_func2 = operast2.node_identity(ast.ClassDef())

    function_def_body = ast.FunctionDef(name="func1", body=[ast.Call(func="int")])
    function_def = ast.FunctionDef(name="func3")
    class_def = ast.ClassDef(name="func1")

    result1 = identity_func1(function_def_body, Scope())
    assert result1

    result2 = identity_func1(function_def, Scope())
    assert not result2

    result3 = identity_func1(class_def, Scope())
    assert not result3

    result4 = identity_func2(class_def, Scope())
    assert result4


# noinspection PyPep8Naming
def test_HasChild():
    has_child_func = HasChild(ast.FunctionDef).func

    test_node_true = ast.FunctionDef(name="func", body=[ast.Call()])
    test_node_false = ast.FunctionDef(name="func")

    result1 = has_child_func(test_node_true, Scope())
    assert result1

    result2 = has_child_func(test_node_false, Scope())
    assert not result2


# noinspection PyPep8Naming
def test_Not():
    not_name = Not(ast.Name).func
    not_name_id_hello = operast2.Not(ast.Name(id="hello")).func

    name_id_hello = ast.Name(id="hello")
    name_id_bye = ast.Name(id="bye")
    name_no_id = ast.Name()

    result1 = not_name(name_id_hello, Scope())
    assert not result1

    result2 = not_name(name_id_bye, Scope())
    assert not result2

    result3 = not_name(name_no_id, Scope())
    assert not result3

    result4 = not_name_id_hello(name_id_hello, Scope())
    assert not result4

    result5 = not_name_id_hello(name_id_bye, Scope())
    assert result5

    result6 = not_name_id_hello(name_no_id, Scope())
    assert result6


# noinspection PyPep8Naming
def test_Or():
    name_or_function_def = operast2.Or(ast.Name, ast.FunctionDef).func

    name = ast.Name()
    function_def = ast.FunctionDef()
    class_def = ast.ClassDef()

    result1 = name_or_function_def(name, Scope())
    assert result1

    result2 = name_or_function_def(function_def, Scope())
    assert result2

    result3 = name_or_function_def(class_def, Scope())
    assert not result3


# noinspection PyPep8Naming,PyTypeChecker
def test_StateAffect_call_error():
    with pytest.raises(ValueError):
        StateAffect()(10)
