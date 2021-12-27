import ast
from operast.pattern import *


class TestExpand:
    pass


class TestPushdownFieldname:
    pass


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
# noinspection PyPep8Naming
class TestCanonicalNormalForm:

    #   1) T(x1, ..., xn, T(y1, ..., yn)) => T(x1, ..., xn, y1, ..., yn)
    def test_Branch_canonical_normal_form_1(self):
        result = Branch(ast.AST, Branch(ast.AST)).canonical_nf()
        expected = Branch(ast.AST, ast.AST)
        assert result == expected

    #   1) T(x1, ..., xn, T(y1, ..., yn)) => T(x1, ..., xn, y1, ..., yn)
    def test_Fork_canonical_normal_form_1(self):
        fork = And(Branch(ast.AST), Branch(ast.AST), And(Branch(ast.AST), Branch(ast.AST)))
        result = fork.canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.AST), Branch(ast.AST), Branch(ast.AST))
        assert result == expected

    #   2) F(x1, ..., xn) => F(f(x1), ..., f(xn))
    def test_Fork_canonical_normal_form_2(self):
        result = And(ast.AST, Branch(ast.Name)).canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.Name))
        assert result == expected

    #   3) F(x) => Branch(x)
    def test_Fork_canonical_normal_form_3(self):
        result = And(ast.AST).canonical_nf()
        expected = Branch(ast.AST)
        assert result == expected

    #   4) Fa(Fb(x1, ..., xn)) => Fb(x1, ..., xn)
    def test_Fork_canonical_normal_form_4(self):
        result = And(Or(ast.AST, ast.expr)).canonical_nf()
        expected = Or(Branch(ast.AST), Branch(ast.expr))
        assert result == expected

    #   5) Branch(x1, ..., xn, F(y1, ..., yn)) =>> F(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_Branch_canonical_normal_form_5(self):
        result = Branch(ast.AST, And(Branch(ast.Name), Branch(ast.Load))).canonical_nf()
        expected = And(Branch(ast.AST, ast.Name), Branch(ast.AST, ast.Load))
        assert result == expected
        assert isinstance(result, And)
        assert result.index == 1

    def test_complex_canonical_normal_form_1(self):
        result = And(Or(Then(Or(And(ast.AST))))).canonical_nf()
        expected = Branch(ast.AST)
        assert result == expected

    def test_complex_canonical_normal_form_2(self):
        pat = Branch(ast.AST, Then(ast.AST, Then(ast.Name, Or(ast.Load, ast.Store))))
        result = pat.canonical_nf()
        expected = Then(
            Branch(ast.AST, ast.AST),
            Branch(ast.AST, ast.Name),
            Or(Branch(ast.AST, ast.Load), Branch(ast.AST, ast.Store))
        )
        assert result == expected

    def test_complex_canonical_normal_form_3(self):
        result = And(ast.AST, Or(And(ast.Name, ast.expr))).canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.Name), Branch(ast.expr))
        assert result == expected


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
class TestDisjunctiveNormalForm:
    pass
