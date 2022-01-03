
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
        result = Branch('A', 'B', Branch('C', 'D')).canonical_nf()
        expected = Branch('A', 'B', 'C', 'D')
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_And_canonical_nf_2(self):
        result = Branch('A', And('B', 'C')).canonical_nf()
        expected = And(Branch('A', 'B'), Branch('A', 'C'))
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_Then_canonical_nf_2(self):
        result = Branch('A', Then('B', 'C')).canonical_nf()
        expected = Then(Branch('A', 'B'), Branch('A', 'C'))
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_Or_canonical_nf_2(self):
        result = Branch('A', Or('B', 'C')).canonical_nf()
        expected = Or(Branch('A', 'B'), Branch('A', 'C'))
        assert result == expected

    #   2) Branch(x1, ..., xn, Fa(y1, ..., yn)) => Fa(Branch(x1, ..., xn, y1), ..., Branch(x1, ..., xn, yn))
    def test_canonical_nf_2_extra(self):
        result = Branch('A', And(Branch('B', 'C'), Branch('D'))).canonical_nf()
        expected = And(Branch('A', 'B', 'C'), Branch('A', 'D'))
        assert result == expected
        assert isinstance(result, And)
        assert result.index == 1

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_Branch_canonical_nf_3(self):
        result = Branch(Branch('A', 'B')).canonical_nf()
        expected = Branch('A', 'B')
        assert result == expected

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_And_canonical_nf_3(self):
        result = And(And(Branch('A'), Branch('B'))).canonical_nf()
        expected = And(Branch('A'), Branch('B'))
        assert result == expected

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_Then_canonical_nf_3(self):
        result = Then(Then(Branch('A'), Branch('B'))).canonical_nf()
        expected = Then(Branch('A'), Branch('B'))
        assert result == expected

    #   3) Ta(Tb(x1, ..., xn)) -> Tb(x1, ..., xn)
    def test_Or_canonical_nf_3(self):
        result = Or(Or(Branch('A'), Branch('B'))).canonical_nf()
        expected = Or(Branch('A'), Branch('B'))
        assert result == expected

    #   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    def test_And_canonical_nf_4(self):
        result = And('A', 'B').canonical_nf()
        expected = And(Branch('A'), Branch('B'))
        assert result == expected

    #   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    def test_Then_canonical_nf_4(self):
        result = Then('A', 'B').canonical_nf()
        expected = Then(Branch('A'), Branch('B'))
        assert result == expected

    #   4) Fa(x1, ..., xn) => Fa(f(x1), ..., f(xn))
    def test_Or_canonical_nf_4(self):
        result = Or('A', 'B').canonical_nf()
        expected = Or(Branch('A'), Branch('B'))
        assert result == expected

    #   5) Fa(x) => Branch(x)
    def test_And_canonical_nf_5(self):
        result = And('A').canonical_nf()
        expected = Branch('A')
        assert result == expected

    #   5) Fa(x) => Branch(x)
    def test_Then_canonical_nf_5(self):
        result = Then('A').canonical_nf()
        expected = Branch('A')
        assert result == expected

    #   5) Fa(x) => Branch(x)
    def test_Or_canonical_nf_5(self):
        result = Or('A').canonical_nf()
        expected = Branch('A')
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index == Fb.index
    def test_And_canonical_nf_6_same_index(self):
        result = And(Branch('A'), And(Branch('B'), Branch('C'))).canonical_nf()
        expected = And(Branch('A'), Branch('B'), Branch('C'))
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index != Fb.index
    def test_And_canonical_nf_6_diff_index(self):
        result = And('A', Branch('B', And('C', 'D'))).canonical_nf()
        expected = And(Branch('A'), And(Branch('B', 'C'), Branch('B', 'D')))
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index == Fb.index
    def test_Then_canonical_nf_6_same_index(self):
        result = Then(Branch('A'), Then(Branch('B'), Branch('C'))).canonical_nf()
        expected = Then(Branch('A'), Branch('B'), Branch('C'))
        assert result == expected

    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa.index != Fb.index
    def test_Then_canonical_nf_6_diff_index(self):
        result = Then('A', Branch('B', Then('C', 'D'))).canonical_nf()
        expected = Then(Branch('A'), Then(Branch('B', 'C'), Branch('B', 'D')))
        assert result == expected

    # Or does not track index
    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa is Or and Fb is Or
    def test_Or_canonical_nf_6_same_index(self):
        result = Or(Branch('A'), Or(Branch('B'), Branch('C'))).canonical_nf()
        expected = Or(Branch('A'), Branch('B'), Branch('C'))
        assert result == expected

    # Or does not track index
    #   6) Fa(x1, ..., xn, Fb(y1, ..., yn)) => Fa(x1, ..., xn, y1, ..., yn)
    #       iff Fa is Or and Fb is Or
    def test_Or_canonical_nf_6_diff_index(self):
        result = Or('A', Branch('B', Or('C', 'D'))).canonical_nf()
        expected = Or(Branch('A'), Branch('B', 'C'), Branch('B', 'D'))
        assert result == expected

    #   7) And(x, Or(y1, y2)) => Or(And(x, y1), And(x, y2))
    def test_canonical_nf_7(self):
        result = And(Branch('A'), Or('B', 'C')).canonical_nf()
        expected = Or(And(Branch('A'), Branch('B')), And(Branch('A'), Branch('C')))
        assert result == expected

    #   8) Then(x, Or(y1, y2)) => Or(Then(x, y1), Then(x, y2))
    def test_canonical_nf_8(self):
        result = Then(Branch('A'), Or('B', 'C')).canonical_nf()
        expected = Or(Then(Branch('A'), Branch('B')), Then(Branch('A'), Branch('C')))
        assert result == expected

    def test_complex_canonical_nf_A(self):
        result = And(Or(Then(Or(And('A'))))).canonical_nf()
        expected = Branch('A')
        assert result == expected

    def test_complex_canonical_nf_B(self):
        pat = Branch('A', Then('A', Then('B', Or('C', 'D'))))
        result = pat.canonical_nf()
        expected = Or(
            Then(
                Branch('A', 'A'),
                Branch('A', 'B'),
                Branch('A', 'C')
            ),
            Then(
                Branch('A', 'A'),
                Branch('A', 'B'),
                Branch('A', 'D')
            )
        )
        assert result == expected

    def test_complex_canonical_nf_C(self):
        result = And('A', Or(And('B', 'C'))).canonical_nf()
        expected = And(Branch('A'), Branch('B'), Branch('C'))
        assert result == expected

    def test_complex_canonical_nf_D(self):
        result = Branch(
            'A', Branch('A', And('B', Branch('C', And('D', 'E'))))
        ).canonical_nf()
        expected = And(
            Branch('A', 'A', 'B'),
            And(
                Branch('A', 'A', 'C', 'D'),
                Branch('A', 'A', 'C', 'E')
            )
        )
        assert isinstance(result, And)
        assert result.index == 2
        assert result == expected

    def test_complex_canonical_nf_E(self):
        result = Then(
            Or(Branch('A'), Branch('B')),
            Or(Branch('C'), Branch('D'))
        ).canonical_nf()
        expected = Or(
            Then(Branch('A'), Branch('C')),
            Then(Branch('A'), Branch('D')),
            Then(Branch('B'), Branch('C')),
            Then(Branch('B'), Branch('D'))
        )
        assert result == expected

    def test_canonical_nf_invariant_only_one_Or(self):
        cnf = And(
            Or('A', Or('B')),
            Branch('C', Or('D', And('B', Then('E', Or('A', 'F')))))
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
