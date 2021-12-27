
from operast.operast3 import *


def test_branch_equals_false_1():
    a = Branch(ast.ClassDef(name='SomeClass'))
    b = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    result = branch_equals(a, b)
    assert not result


def test_branch_equals_false_2():
    a = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    b = Branch(ast.ClassDef(name='SomeClass'), And(Then(('something', ast.Assign))))
    result = branch_equals(a, b)
    assert not result


def test_branch_equals_false_3():
    a = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    b = Branch(ast.ClassDef(name='SomeClass'), And(Then(ast.Assign)))
    result = branch_equals(a, b)
    assert not result


def test_branch_equals_false_4():
    a = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    b = Branch(ast.ClassDef(name='SomeClass'), And(And(('body', ast.Assign))))
    result = branch_equals(a, b)
    assert not result


def test_branch_equals_true():
    a = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    b = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    result = branch_equals(a, b)
    assert result


def test_branch_expand_ast_inst():
    ast_inst = ast.ClassDef(
        name='SomeClass',
        body=[ast.Assign],
    )
    expanded = branch_expand(ast_inst)
    expected = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
    result = branch_equals(expanded, expected)
    assert result, (expanded, expected)


def test_branch_expand_ast_type():
    ast_type = ast.ClassDef
    expanded = branch_expand(ast_type)
    expected = ast.ClassDef
    result = branch_equals(expanded, expected)
    assert result, (expanded, expected)


def test_branch_expand_branch_pattern():
    branch_pattern = And(ast.ClassDef(
        name='SomeClass',
        body=[ast.Assign],
    ))
    expanded = branch_expand(branch_pattern)
    expected = And(Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign)))))
    result = branch_equals(expanded, expected)
    assert result, (expanded, expected)


def test_branch_expand_tuple_ast_type():
    tuple_ast_type = ('body', ast.ClassDef)
    expanded = branch_expand(tuple_ast_type)
    expected = ('body', ast.ClassDef)
    result = branch_equals(expanded, expected)
    assert result, (expanded, expected)


def test_branch_expand_tuple_ast_inst():
    tuple_ast_inst = ('body', ast.Name(ctx=ast.Load()))
    expanded = branch_expand(tuple_ast_inst)
    expected = Branch(('body', ast.Name()), And(('ctx', ast.Load())))
    result = branch_equals(expanded, expected)
    assert result, (expanded, expected)


def test_branch_pattern_len():
    bp1 = Branch(ast.ClassDef, ast.FunctionDef, ast.Name)
    res1 = len(bp1) == 3
    assert res1

    bp2 = And(Branch(ast.Name, ast.Load), ast.ClassDef)
    res2 = len(bp2) == 2
    assert res2


def test_branch_pattern_iter():
    bp = Branch(ast.Assign, ast.And, ast.Or, ast.alias)
    bp_list = [i for i in bp]
    expected = [ast.Assign, ast.And, ast.Or, ast.alias]
    assert bp_list == expected


def test_branch_pattern_repr():
    bp1 = Branch(ast.Name)
    repr1 = "Seq(<class '_ast.Name'>)"
    result1 = str(bp1) == repr1
    assert result1, (str(bp1), repr1)

    bp2 = Then(Branch(ast.Name), ast.FunctionDef)
    repr2 = "Then(Seq(<class '_ast.Name'>), <class '_ast.FunctionDef'>)"
    result2 = str(bp2) == repr2
    assert result2, (str(bp2), repr2)


def test_seq_first_normal():
    pass
