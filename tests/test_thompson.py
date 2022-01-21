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
