from operast.constraints import *


class TestSibling:
    #   1) Sib(x, A, B) -> [Sib(x, A, B)]
    def test_sibling_constraint_1(self):
        constrained = Sib(0, 'A', 'B').constraint()
        result = [Sib(0, 'A', 'B')]
        assert constrained == result

    #   2) Sib(x, A, Sib(y, B, C)) -> [Sib(x, A, B), Sib(y, B, C)]
    def test_sibling_constraint_2(self):
        constrained = Sib(0, 'A', Sib(1, 'B', 'C')).constraint()
        result = [Sib(0, 'A', 'B'), Sib(1, 'B', 'C')]
        assert constrained == result

    def test_sibling_constraint_complex(self):
        constrained = Sib(0, Sib(1, 'A', 'D'), Sib(1, 'B', 'C')).constraint()
        result = [
            Sib(0, 'A', 'B'),
            Sib(1, 'A', 'D'),
            Sib(1, 'B', 'C')
        ]
        assert constrained == result

    def test_sib_equals(self):
        sib1 = Sib(0, 'A', 'B')
        sib2 = Sib(1, 'A', 'B')
        sib3 = Sib(0, 'X', 'Y')
        sib4 = Sib(0, 'A', 'B')

        assert sib1 == sib4
        assert sib1 != sib2 != sib3
        assert sib1 != Total('A', 'B')

    def test_sib_init_flatten(self):
        sib1 = Sib(0, 'A', Sib(0, 'B', 'C'))
        assert sib1 == Sib(0, 'A', 'B', 'C')

        sib2 = Sib(0, 'A', Sib(1, 'B', 'C'))
        assert sib2 != Sib(0, 'A', 'B', 'C')


# Cases:
#   1) Ord(A, B) => A -> B
#   2) Ord(A, Ord(B, C)) => A -> B -> C
#   3) Ord(A, [B, C]) => A -> B, A -> C
#   4) Ord([A, B], C) => A -> C, B -> C
#   5) Ord(A, [Ord(B, C), D]) => Ord(A, [B -> C, D]) => A -> B -> C, A -> D
#   6) Ord([A, Ord(B, C)], D) => Ord([A, B -> C], D) => A -> D, B -> C -> D
#   7) Ord(A, [Ord([B, C], D), E]) => Ord(A, [B -> D, C -> D, E]) =>
#       A -> B -> D, A -> C -> D, A -> E
#   8) Ord(A, [Ord([B, C], D), E], F) => Ord(A, [B -> D, C -> D, E], F) =>
#       A -> B -> D -> F, A -> C -> D -> F, A -> E -> F
#   9) Ord([A, B]) => A, B
#
class TestOrdered:
    #   1) Ord(A, B) => A -> B
    def test_ordered_dag_1(self):
        dag = Total('A', 'B').to_dag()
        result = {'A': {'B'}}
        assert dag == result

    #   2) Ord(A, Ord(B, C)) => A -> B -> C
    def test_ordered_dag_2(self):
        dag = Total('A', Total('B', 'C')).to_dag()
        result = {'A': {'B'}, 'B': {'C'}}
        assert dag == result

    #   3) Ord(A, [B, C]) => A -> B, A -> C
    def test_ordered_dag_3(self):
        dag = Total('A', Partial('B', 'C')).to_dag()
        result = {'A': {'B', 'C'}}
        assert dag == result

    #   4) Ord([A, B], C) => A -> C, B -> C
    def test_ordered_dag_4(self):
        dag = Total(Partial('A', 'B'), 'C').to_dag()
        result = {'A': {'C'}, 'B': {'C'}}
        assert dag == result

    #   5) Ord(A, [Ord(B, C), D]) => Ord(A, [B -> C, D]) => A -> B -> C, A -> D
    def test_ordered_dag_5(self):
        dag = Total('A', Partial(Total('B', 'C'), 'D')).to_dag()
        result = {'A': {'B', 'D'}, 'B': {'C'}}
        assert dag == result

    #   6) Ord([A, Ord(B, C)], D) => Ord([A, B -> C], D) => A -> D, B -> C -> D
    def test_ordered_dag_6(self):
        dag = Total(Partial('A', Total('B', 'C')), 'D').to_dag()
        result = {'A': {'D'}, 'B': {'C'}, 'C': {'D'}}
        assert dag == result

    #   7) Ord(A, [Ord([B, C], D), E]) => Ord(A, [B -> D, C -> D, E]) =>
    #       A -> B -> D, A -> C -> D, A -> E
    def test_ordered_dag_7(self):
        dag = Total('A', Partial(Total(Partial('B', 'C'), 'D'), 'E')).to_dag()
        result = {'A': {'B', 'C', 'E'}, 'B': {'D'}, 'C': {'D'}}
        assert dag == result

    #   8) Ord(A, [Ord([B, C], D), E], F) => Ord(A, [B -> D, C -> D, E], F) =>
    #       A -> B -> D -> F, A -> C -> D -> F, A -> E -> F
    def test_ordered_dag_8(self):
        dag = Total('A', Partial(Total(Partial('B', 'C'), 'D'), 'E'), 'F').to_dag()
        result = {'A': {'B', 'C', 'E'}, 'B': {'D'}, 'C': {'D'}, 'D': {'F'}, 'E': {'F'}}
        assert dag == result

    #   9) Ord([A, B]) => A, B
    def test_ordered_dag_9(self):
        dag = Partial('B', 'C').to_dag()
        result = {}
        assert dag == result

    def test_ord_dag_complex_1(self):
        dag = Total(
            'A',
            Total('N1', 'N2'),
            Partial('B1', 'C1'),
            Partial('B2', 'C2'),
            'D'
        ).to_dag()

        expected = {
            'A': {'N1'},
            'N1': {'N2'},
            'N2': {'B1', 'C1'},
            'B1': {'B2', 'C2'},
            'C1': {'B2', 'C2'},
            'B2': {'D'},
            'C2': {'D'}
        }
        assert dag == expected

    def test_ord_equals(self):
        t1 = Total('A', 'B', 'C')
        t2 = Total('A', 'B', 'C')
        t3 = Total('B', 'C')

        p1 = Partial('A', 'B', 'C')
        p2 = Partial('A', 'B', 'C')
        p3 = Partial('B', 'C')

        assert t1 == t2
        assert p1 == p2
        assert t1 != t3 != p1 != p3
