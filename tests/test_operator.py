
from operast.operator import *
from operast.pattern import And
from operast.thompson import *


class TestOp:

    def test_equals(self):
        s1 = Plus('A')
        s2 = Plus('A')
        s3 = Plus('B')
        pat = And('A', 'B')

        assert s1 == s2
        assert s1 != s3 != pat


class TestCompile:

    # ab?c
    def test_compile_1(self):
        result = compile_regex(['a', QMark('b'), 'c'])
        expected = [Unit('a'), Split(2, 3), Unit('b'), Unit('c'), Match()]
        assert result == expected

    # ab??c
    def test_compile_2(self):
        result = compile_regex(['a', QMark('b', greedy=False), 'c'])
        expected = [Unit('a'), Split(3, 2), Unit('b'), Unit('c'), Match()]
        assert result == expected

    # ab*c
    def test_compile_3(self):
        result = compile_regex(['a', Star('b'), 'c'])
        expected = [Unit('a'), Split(2, 4), Unit('b'), Jump(1), Unit('c'), Match()]
        assert result == expected

    # ab*?c
    def test_compile_4(self):
        result = compile_regex(['a', Star('b', greedy=False), 'c'])
        expected = [Unit('a'), Split(4, 2), Unit('b'), Jump(1), Unit('c'), Match()]
        assert result == expected

    # ab+c
    def test_compile_5(self):
        result = compile_regex(['a', Plus('b'), 'c'])
        expected = [Unit('a'), Unit('b'), Split(1, 3), Unit('c'), Match()]
        assert result == expected

    # ab+?c
    def test_compile_6(self):
        result = compile_regex(['a', Plus('b', greedy=False), 'c'])
        expected = [Unit('a'), Unit('b'), Split(3, 1), Unit('c'), Match()]
        assert result == expected

    # a+b+
    def test_compile_7(self):
        result = compile_regex([Plus('a'), Plus('b')])
        expected = [Unit('a'), Split(0, 2), Unit('b'), Split(2, 4), Match()]
        assert result == expected

    # a(b|c)d
    def test_compile_8(self):
        result = compile_regex(['a', Alt(['b'], ['c']), 'd'])
        expected = [Unit('a'), Split(2, 4), Unit('b'), Jump(5), Unit('c'), Unit('d'), Match()]
        assert result == expected

    # a[bc]d
    def test_compile_9(self):
        result = compile_regex(['a', Lst('b', 'c'), 'd'])
        expected = [Unit('a'), UnitList(['b', 'c']), Unit('d'), Match()]
        assert result == expected

    # a.b
    def test_compile_10(self):
        result = compile_regex(['a', Dot(), 'b'])
        expected = [Unit('a'), AnyUnit(), Unit('b'), Match()]
        assert result == expected

    # ab{3}c
    def test_compile_11(self):
        result = compile_regex(['a', Repeat('b', count=3), 'c'])
        expected = [Unit('a'), Unit('b'), Unit('b'), Unit('b'), Unit('c'), Match()]
        assert result == expected

    # a(b|c)*d
    def test_compile_complex_1(self):
        result = compile_regex(['a', Star(Alt(['b'], ['c'])), 'd'])
        expected = [Unit('a'), Split(2, 7), Split(3, 5), Unit('b'),
                    Jump(6), Unit('c'), Jump(1), Unit('d'), Match()]
        assert result == expected

    # a(b|c*)d
    def test_compile_complex_2(self):
        result = compile_regex(['a', Alt(['b'], [Star('c')]), 'd'])
        expected = [Unit('a'), Split(2, 4), Unit('b'), Jump(7),
                    Split(5, 7), Unit('c'), Jump(4), Unit('d'), Match()]
        assert result == expected

    # .+P
    def test_compile_complex_13(self):
        result = compile_regex([Plus(Dot()), 'P'])
        expected = [AnyUnit(), Split(0, 2), Unit('P'), Match()]
        assert result == expected
