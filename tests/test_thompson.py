
from operast.thompson import *
from typing import List


def thompson_str(program: List[Inst[str]], in_: str) -> bool:
    return thompson_vm(program, list(in_), str.__eq__)


class TestThompsonVM:

    # ab?c
    def test_zero_or_one_1(self):
        program = [Unit('a'), Split(2, 3), Unit('b'), Unit('c'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'abc')
        assert not thompson_str(program, 'abbc')
        assert thompson_str(program, 'ac')

    # ab*c
    def test_zero_or_more_1(self):
        program = [Unit('a'), Split(2, 4), Unit('b'), Jump(1), Unit('c'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'abc')
        assert thompson_str(program, 'abbc')
        assert thompson_str(program, 'ac')

    # ab+c
    def test_one_or_more_1(self):
        program = [Unit('a'), Unit('b'), Split(1, 3), Unit('c'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'abc')
        assert thompson_str(program, 'abbc')
        assert not thompson_str(program, 'ac')

    # a+b+
    def test_one_or_more_2(self):
        program = [Unit('a'), Split(0, 2), Unit('b'), Split(2, 4), Match()]
        assert thompson_str(program, 'aaaabbb')
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'b')

    # a(b|c)d
    def test_alternate_1(self):
        program = [Unit('a'), Split(2, 4), Unit('b'), Jump(5), Unit('c'), Unit('d'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'abd')
        assert not thompson_str(program, 'ac')
        assert thompson_str(program, 'acd')
        assert not thompson_str(program, 'abcd')
        assert not thompson_str(program, 'ad')

    # a[bc]d
    def test_unit_class_1(self):
        program = [Unit('a'), UnitList(['b', 'c']), Unit('d'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert not thompson_str(program, 'ac')
        assert thompson_str(program, 'abd')
        assert thompson_str(program, 'acd')
        assert not thompson_str(program, 'abcd')
        assert not thompson_str(program, 'ad')

    # a.b
    def test_any_unit_1(self):
        program = [Unit('a'), AnyUnit(), Unit('b'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'b')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'aab')
        assert thompson_str(program, 'abb')
        assert thompson_str(program, 'acb')
        assert thompson_str(program, 'azb')
        assert not thompson_str(program, 'axyzb')

    # a(b|c)*d
    def test_complex_1(self):
        program = [Unit('a'), Split(2, 7), Split(3, 5), Unit('b'),
                   Jump(6), Unit('c'), Jump(1), Unit('d'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'abd')
        assert thompson_str(program, 'abbbd')
        assert not thompson_str(program, 'ac')
        assert thompson_str(program, 'acd')
        assert thompson_str(program, 'acccd')
        assert thompson_str(program, 'abcd')
        assert thompson_str(program, 'abcbd')
        assert thompson_str(program, 'acbcd')
        assert thompson_str(program, 'ad')

    # a(b|c*)d
    def test_complex_2(self):
        program = [Unit('a'), Split(2, 4), Unit('b'), Jump(7),
                   Split(5, 7), Unit('c'), Jump(4), Unit('d'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'ab')
        assert thompson_str(program, 'abd')
        assert not thompson_str(program, 'abbbd')
        assert not thompson_str(program, 'ac')
        assert thompson_str(program, 'acd')
        assert thompson_str(program, 'acccd')
        assert not thompson_str(program, 'abcd')
        assert not thompson_str(program, 'abcbd')
        assert not thompson_str(program, 'acbcd')
        assert thompson_str(program, 'ad')

    # .+P
    def test_complex_3(self):
        program = [AnyUnit(), Split(0, 2), Unit('P'), Match()]
        assert not thompson_str(program, 'a')
        assert not thompson_str(program, 'P')
        assert thompson_str(program, 'aP')
        assert not thompson_str(program, 'abcdef')
        assert thompson_str(program, 'abcdefP')
