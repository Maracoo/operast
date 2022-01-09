
import ast
from operast.ast_pattern import *
from operast.pattern import *


class TestTag:

    def test_expand_1(self):
        expand = Tag('body', ast.AST).te_expand()
        assert expand == Tag('body', ast.AST)

    def test_expand_2(self):
        expand = Tag('body', ast.AST(id='a')).te_expand()
        assert expand == Tag('body', ast.AST(id='a'))

    def test_expand_3(self):
        expand = Tag('body', ast.AST(ctx=ast.Store)).te_expand()
        expected = Branch(Tag('body', ast.AST()), And(Tag('ctx', ast.Store)))
        assert expand == expected


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


class TestASTExpand:

    def test_expand_ast_1(self):
        assert ast_equals(ast_expand(ast.AST), ast.AST)

    def test_expand_ast_2(self):
        assert ast_equals(ast_expand(ast.Name()), ast.Name())

    def test_expand_ast_3(self):
        expand = ast_expand(ast.AST(ctx=ast.Store))
        assert expand == Branch(ast.AST(), And(Tag('ctx', ast.Store)))

    def test_expand_ast_4(self):
        expand = ast_expand(ast.AST(body=[ast.Assign]))
        assert expand == Branch(ast.AST(), And(Then(Tag('body', ast.Assign))))

    def test_expand_ast_5(self):
        expand = ast_expand(
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

    def test_expand_ast_6(self):
        ast_inst = ast.ClassDef(
            name='SomeClass',
            body=[ast.Assign],
        )
        expand = ast_expand(ast_inst)
        expected = Branch(ast.ClassDef(name='SomeClass'), And(Then(Tag('body', ast.Assign))))
        assert expand == expected

        branch = Branch(ast.ClassDef(
            name='SomeClass',
            body=[ast.Assign],
        ))
        assert branch.expand() == Branch(expand)

    def test_expand_ast_7(self):
        expand = ast_expand(ast.AST(body=[Branch(ast.Name, ast.Store)]))
        expected = Branch(ast.AST(), And(Then(Branch(ast.Name, ast.Store))))
        assert expand == expected
