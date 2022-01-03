import ast
import operast.pattern
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
# Let x, y ∈ TreeElem, and let n ∈ ℕ.
# Let Ta, Tb, ... ∈ TreePattern, and let Fa, Fb, ... ∈ ForkPattern.
# Then, given concrete TreePattern classes Branch, And, Then and Or, we
# have rewrite rules:
#
#   1) Branch(x1, ..., xn, Branch(y1, ..., yn)) => Branch(x1, ..., xn, y1, ..., yn)
#   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
#   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
#   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
#   5) Fa(x) => Branch(x)
#   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
#       iff Fa.index == Fb.index V Fa is Or and Fb is Or
#   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
#   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
#
# noinspection PyPep8Naming
class TestCanonicalNormalForm:

    #   1) Branch(x1, ..., xn, Branch(y1, ..., yn)) => Branch(x1, ..., xn, y1, ..., yn)
    def test_canonical_nf_1(self):
        result = Branch(ast.AST, ast.Name, Branch(ast.AST, ast.Load)).canonical_nf()
        expected = Branch(ast.AST, ast.Name, ast.AST, ast.Load)
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_And_canonical_nf_2(self):
        result = Branch(ast.AST, And(ast.AST, ast.Load)).canonical_nf()
        expected = And(Branch(ast.AST, ast.AST), Branch(ast.AST, ast.Load))
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_Then_canonical_nf_2(self):
        result = Branch(ast.AST, Then(ast.AST, ast.Load)).canonical_nf()
        expected = Then(Branch(ast.AST, ast.AST), Branch(ast.AST, ast.Load))
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_Or_canonical_nf_2(self):
        result = Branch(ast.AST, Or(ast.AST, ast.Load)).canonical_nf()
        expected = Or(Branch(ast.AST, ast.AST), Branch(ast.AST, ast.Load))
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_canonical_nf_2_extra(self):
        result = Branch(ast.AST, And(Branch(ast.Name, ast.Store), Branch(ast.Load))).canonical_nf()
        expected = And(Branch(ast.AST, ast.Name, ast.Store), Branch(ast.AST, ast.Load))
        assert result == expected
        assert isinstance(result, And)
        assert result.index == 1

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_Branch_canonical_nf_3(self):
        result = Branch(Branch(ast.AST, ast.Load)).canonical_nf()
        expected = Branch(ast.AST, ast.Load)
        assert result == expected

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_And_canonical_nf_3(self):
        result = And(And(Branch(ast.AST), Branch(ast.Load))).canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.Load))
        assert result == expected

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_Then_canonical_nf_3(self):
        result = Then(Then(Branch(ast.AST), Branch(ast.Load))).canonical_nf()
        expected = Then(Branch(ast.AST), Branch(ast.Load))
        assert result == expected

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_Or_canonical_nf_3(self):
        result = Or(Or(Branch(ast.AST), Branch(ast.Load))).canonical_nf()
        expected = Or(Branch(ast.AST), Branch(ast.Load))
        assert result == expected

    #   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    def test_And_canonical_nf_4(self):
        result = And(ast.AST, ast.Load).canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.Load))
        assert result == expected

    #   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    def test_Then_canonical_nf_4(self):
        result = Then(ast.AST, ast.Load).canonical_nf()
        expected = Then(Branch(ast.AST), Branch(ast.Load))
        assert result == expected

    #   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    def test_Or_canonical_nf_4(self):
        result = Or(ast.AST, ast.Load).canonical_nf()
        expected = Or(Branch(ast.AST), Branch(ast.Load))
        assert result == expected

    #   5) Fa(x) => Branch(x)
    def test_And_canonical_nf_5(self):
        result = And(ast.AST).canonical_nf()
        expected = Branch(ast.AST)
        assert result == expected

    #   5) Fa(x) => Branch(x)
    def test_Then_canonical_nf_5(self):
        result = Then(ast.AST).canonical_nf()
        expected = Branch(ast.AST)
        assert result == expected

    #   5) Fa(x) => Branch(x)
    def test_Or_canonical_nf_5(self):
        result = Or(ast.AST).canonical_nf()
        expected = Branch(ast.AST)
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index == Fb.index
    def test_And_canonical_nf_6_same_index(self):
        result = And(Branch(ast.AST), And(Branch(ast.Load), Branch(ast.Store))).canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.Load), Branch(ast.Store))
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index != Fb.index
    def test_And_canonical_nf_6_diff_index(self):
        result = And(ast.AST, Branch(ast.Name, And(ast.Load, ast.Store))).canonical_nf()
        expected = And(Branch(ast.AST), And(Branch(ast.Name, ast.Load), Branch(ast.Name, ast.Store)))
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index == Fb.index
    def test_Then_canonical_nf_6_same_index(self):
        result = Then(Branch(ast.AST), Then(Branch(ast.Load), Branch(ast.Store))).canonical_nf()
        expected = Then(Branch(ast.AST), Branch(ast.Load), Branch(ast.Store))
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index != Fb.index
    def test_Then_canonical_nf_6_diff_index(self):
        result = Then(ast.AST, Branch(ast.Name, Then(ast.Load, ast.Store))).canonical_nf()
        expected = Then(Branch(ast.AST), Then(Branch(ast.Name, ast.Load), Branch(ast.Name, ast.Store)))
        assert result == expected

    # Or does not track index
    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa is Or and Fb is Or
    def test_Or_canonical_nf_6_same_index(self):
        result = Or(Branch(ast.AST), Or(Branch(ast.Load), Branch(ast.Store))).canonical_nf()
        expected = Or(Branch(ast.AST), Branch(ast.Load), Branch(ast.Store))
        assert result == expected

    # Or does not track index
    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa is Or and Fb is Or
    def test_Or_canonical_nf_6_diff_index(self):
        result = Or(ast.AST, Branch(ast.Name, Or(ast.Load, ast.Store))).canonical_nf()
        expected = Or(Branch(ast.AST), Branch(ast.Name, ast.Load), Branch(ast.Name, ast.Store))
        assert result == expected

    #   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
    def test_canonical_nf_7(self):
        result = And(Branch(ast.AST), Or(ast.Load, ast.Store)).canonical_nf()
        expected = Or(And(Branch(ast.AST), Branch(ast.Load)), And(Branch(ast.AST), Branch(ast.Store)))
        assert result == expected

    #   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
    def test_canonical_nf_8(self):
        result = Then(Branch(ast.AST), Or(ast.Load, ast.Store)).canonical_nf()
        expected = Or(Then(Branch(ast.AST), Branch(ast.Load)), Then(Branch(ast.AST), Branch(ast.Store)))
        assert result == expected

    def test_complex_canonical_nf_A(self):
        result = And(Or(Then(Or(And(ast.AST))))).canonical_nf()
        expected = Branch(ast.AST)
        assert result == expected

    def test_complex_canonical_nf_B(self):
        pat = Branch(ast.AST, Then(ast.AST, Then(ast.Name, Or(ast.Load, ast.Store))))
        result = pat.canonical_nf()
        expected = Or(
            Then(
                Branch(ast.AST, ast.AST),
                Branch(ast.AST, ast.Name),
                Branch(ast.AST, ast.Load)
            ),
            Then(
                Branch(ast.AST, ast.AST),
                Branch(ast.AST, ast.Name),
                Branch(ast.AST, ast.Store)
            )
        )
        assert result == expected

    def test_complex_canonical_nf_C(self):
        result = And(ast.AST, Or(And(ast.Name, ast.expr))).canonical_nf()
        expected = And(Branch(ast.AST), Branch(ast.Name), Branch(ast.expr))
        assert result == expected

    def test_complex_canonical_nf_D(self):
        result = Branch(
            ast.AST,
            Branch(
                ast.AST,
                And(
                    ast.Name,
                    Branch(ast.expr, And(ast.Load, ast.Store))
                )
            )
        ).canonical_nf()
        expected = And(
            Branch(ast.AST, ast.AST, ast.Name),
            And(
                Branch(ast.AST, ast.AST, ast.expr, ast.Load),
                Branch(ast.AST, ast.AST, ast.expr, ast.Store)
            )
        )
        assert isinstance(result, And)
        assert result.index == 2
        assert result == expected

    def test_complex_canonical_nf_E(self):
        result = Then(
            Or(Branch(ast.AST), Branch(ast.Name)),
            Or(Branch(ast.List), Branch(ast.Tuple))
        ).canonical_nf()
        expected = Or(
            Then(Branch(ast.AST), Branch(ast.List)),
            Then(Branch(ast.AST), Branch(ast.Tuple)),
            Then(Branch(ast.Name), Branch(ast.List)),
            Then(Branch(ast.Name), Branch(ast.Tuple))
        )
        assert result == expected

    def test_canonical_nf_invariant_only_one_Or(self):
        cnf = And(
            Or(ast.AST, Or(ast.Name)),
            Branch(
                ast.Load,
                Or(ast.Tuple, And(ast.Name, Then(ast.And, Or(ast.AST, ast.Or))))
            )
        ).canonical_nf()

        or_count = 0
        to_check = [cnf]
        while to_check:
            elem = to_check.pop()
            if isinstance(elem, operast.pattern.TreePattern):
                to_check.extend(elem.elems)
                if isinstance(elem, Or):
                    or_count += 1

        assert or_count == 1
