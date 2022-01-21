
import ast
import pytest
from operast.ast_pattern import *
from operast.pattern import *


class TestASTEquals:

    def test_ast_equals_true_1(self):
        assert ast_equals(ast.AST, ast.AST)

    def test_ast_equals_true_2(self):
        assert ast_equals(ast.Name(), ast.Name())

    def test_ast_equals_true_3(self):
        assert ast_equals(ast.AST(id='a'), ast.AST(id='a'))

    def test_ast_equals_false_1(self):
        assert not ast_equals(ast.AST, ast.Name)

    def test_ast_equals_false_2(self):
        assert not ast_equals(ast.AST(), ast.Name())

    def test_ast_equals_false_3(self):
        assert not ast_equals(ast.AST(id='a'), ast.AST(id='b'))


class TestToPattern:

    def test_tag_to_pattern_1(self):
        expand = to_pattern(Tag('body', ast.AST))
        assert expand == Tag('body', ast.AST)

    def test_tag_to_pattern_2(self):
        expand = to_pattern(Tag('body', ast.AST(id='a')))
        assert expand == Tag('body', ast.AST(id='a'))

    def test_tag_to_pattern_3(self):
        expand = to_pattern(Tag('body', ast.AST(ctx=ast.Store)))
        expected = Branch(Tag('body', ast.AST()), And(Tag('ctx', ast.Store)))
        assert expand == expected

    def test_ast_to_pattern_1(self):
        assert ast_equals(to_pattern(ast.AST), ast.AST)

    def test_ast_to_pattern_2(self):
        assert ast_equals(to_pattern(ast.Name()), ast.Name())

    def test_ast_to_pattern_3(self):
        expand = to_pattern(ast.AST(ctx=ast.Store))
        assert expand == Branch(ast.AST(), And(Tag('ctx', ast.Store)))

    def test_ast_to_pattern_4(self):
        expand = to_pattern(ast.AST(body=[ast.Assign]))
        assert expand == Branch(ast.AST(), And(Then(Tag('body', ast.Assign))))

    def test_ast_to_pattern_5(self):
        expand = to_pattern(
            ast.AST(id='a', body=[ast.Assign, ast.Return, ast.Name(id='x')])
        )
        expected = Branch(
            ast.AST(id='a'),
            And(Then(
                Tag('body', ast.Assign),
                Tag('body', ast.Return),
                Tag('body', ast.Name(id='x'))
            ))
        )
        assert expand == expected

    def test_ast_to_pattern_6(self):
        ast_inst = ast.ClassDef(
            name='SomeClass',
            body=[ast.Assign],
        )
        expand = to_pattern(ast_inst)
        expected = Branch(ast.ClassDef(name='SomeClass'), And(Then(Tag('body', ast.Assign))))
        assert expand == expected

        branch = Branch(ast.ClassDef(
            name='SomeClass',
            body=[ast.Assign],
        ))
        assert to_pattern(branch) == Branch(expand)

    def test_ast_to_pattern_7(self):
        expand = to_pattern(ast.AST(body=[Branch(ast.Name, ast.Store)]))
        expected = Branch(ast.AST(), And(Then(Branch(ast.Name, ast.Store))))
        assert expand == expected

    def test_to_pattern_8(self):
        unexpanded = Branch(
            ast.FunctionDef,
            And(
                ast.ClassDef(
                    body=[
                        Branch(ast.Assign, ast.Name(id='b', ctx=ast.Store())),
                        ast.FunctionDef
                    ]
                ),
                ast.Call
            )
        )

        expanded = Branch(
            ast.FunctionDef,
            And(
                Branch(Branch(
                    ast.ClassDef(),
                    And(Then(
                        Branch(
                            Tag('body', ast.Assign),
                            Branch(
                                ast.Name(id='b'),
                                And(Tag('ctx', ast.Store()))
                            )
                        ),
                        Tag('body', ast.FunctionDef)
                    ))
                )),
                ast.Call
            )
        )

        assert to_pattern(unexpanded).canonical_nf() == expanded.canonical_nf()

    def test_to_pattern_error_1(self):
        with pytest.raises(ValueError):
            to_pattern(Branch(ast.AST, ast.AST(ctx=ast.Store), ast.AST))
