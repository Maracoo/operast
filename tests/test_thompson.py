from operast.thompson import *


class TestThompsonVM:

    # ab?c
    def test_zero_or_one_1(self):
        program = [Unit('a'), Split(2, 3), Unit('b'), Unit('c'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('abc'), str.__eq__)
        assert not thompson_vm(program, list('abbc'), str.__eq__)
        assert thompson_vm(program, list('ac'), str.__eq__)

    # ab*c
    def test_zero_or_more_1(self):
        program = [Unit('a'), Split(2, 4), Unit('b'), Jump(1), Unit('c'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('abc'), str.__eq__)
        assert thompson_vm(program, list('abbc'), str.__eq__)
        assert thompson_vm(program, list('ac'), str.__eq__)

    # ab+c
    def test_one_or_more_1(self):
        program = [Unit('a'), Unit('b'), Split(1, 3), Unit('c'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('abc'), str.__eq__)
        assert thompson_vm(program, list('abbc'), str.__eq__)
        assert not thompson_vm(program, list('ac'), str.__eq__)

    # a+b+
    def test_one_or_more_2(self):
        program = [Unit('a'), Split(0, 2), Unit('b'), Split(2, 4), Match()]
        assert thompson_vm(program, list('aaaabbb'), str.__eq__)
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('b'), str.__eq__)

    # a(b|c)d
    def test_alternate_1(self):
        program = [Unit('a'), Split(2, 4), Unit('b'), Jump(5), Unit('c'), Unit('d'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('abd'), str.__eq__)
        assert not thompson_vm(program, list('ac'), str.__eq__)
        assert thompson_vm(program, list('acd'), str.__eq__)
        assert not thompson_vm(program, list('abcd'), str.__eq__)
        assert not thompson_vm(program, list('ad'), str.__eq__)

    # a[bc]d
    def test_unit_class_1(self):
        program = [Unit('a'), UnitClass(['b', 'c']), Unit('d'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert not thompson_vm(program, list('ac'), str.__eq__)
        assert thompson_vm(program, list('abd'), str.__eq__)
        assert thompson_vm(program, list('acd'), str.__eq__)
        assert not thompson_vm(program, list('abcd'), str.__eq__)
        assert not thompson_vm(program, list('ad'), str.__eq__)

    # a.b
    def test_any_unit_1(self):
        program = [Unit('a'), AnyUnit(), Unit('b'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('b'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('aab'), str.__eq__)
        assert thompson_vm(program, list('abb'), str.__eq__)
        assert thompson_vm(program, list('acb'), str.__eq__)
        assert thompson_vm(program, list('azb'), str.__eq__)
        assert not thompson_vm(program, list('axyzb'), str.__eq__)

    # a(b|c)*d
    def test_complex_1(self):
        program = [Unit('a'), Split(2, 7), Split(3, 5), Unit('b'),
                   Jump(6), Unit('c'), Jump(1), Unit('d'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('abd'), str.__eq__)
        assert thompson_vm(program, list('abbbd'), str.__eq__)
        assert not thompson_vm(program, list('ac'), str.__eq__)
        assert thompson_vm(program, list('acd'), str.__eq__)
        assert thompson_vm(program, list('acccd'), str.__eq__)
        assert thompson_vm(program, list('abcd'), str.__eq__)
        assert thompson_vm(program, list('abcbd'), str.__eq__)
        assert thompson_vm(program, list('acbcd'), str.__eq__)
        assert thompson_vm(program, list('ad'), str.__eq__)

    # a(b|c*)d
    def test_complex_2(self):
        program = [Unit('a'), Split(2, 4), Unit('b'), Jump(7),
                   Split(5, 7), Unit('c'), Jump(4), Unit('d'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('ab'), str.__eq__)
        assert thompson_vm(program, list('abd'), str.__eq__)
        assert not thompson_vm(program, list('abbbd'), str.__eq__)
        assert not thompson_vm(program, list('ac'), str.__eq__)
        assert thompson_vm(program, list('acd'), str.__eq__)
        assert thompson_vm(program, list('acccd'), str.__eq__)
        assert not thompson_vm(program, list('abcd'), str.__eq__)
        assert not thompson_vm(program, list('abcbd'), str.__eq__)
        assert not thompson_vm(program, list('acbcd'), str.__eq__)
        assert thompson_vm(program, list('ad'), str.__eq__)

    # .+P
    def test_complex_3(self):
        program = [AnyUnit(), Split(0, 2), Unit('P'), Match()]
        assert not thompson_vm(program, list('a'), str.__eq__)
        assert not thompson_vm(program, list('P'), str.__eq__)
        assert thompson_vm(program, list('aP'), str.__eq__)
        assert not thompson_vm(program, list('abcdef'), str.__eq__)
        assert thompson_vm(program, list('abcdefP'), str.__eq__)
