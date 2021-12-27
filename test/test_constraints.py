from operast.constraints import *


class TestSibling:
    #   1) Sib(x, A, B) -> [Sib(x, A, B)]
    def test_sibling_flatten_1(self):
        flattened = Sibling(0, Term('A'), Term('B')).flatten()
        result = [Sibling(0, Term('A'), Term('B'))]
        assert flattened == result

    #   2) Sib(x, A, Sib(y, B, C)) -> [Sib(x, A, B), Sib(y, B, C)]
    def test_sibling_flatten_2(self):
        flattened = Sibling(0, Term('A'), Sibling(1, Term('B'), Term('C'))).flatten()
        result = [Sibling(0, Term('A'), Term('B')), Sibling(1, Term('A'), Term('B'))]
        assert flattened == result


class TestOrdered:
    #   1) Ord(A, B) => A -> B
    def test_ordered_dag_1(self):
        dag = Ord(Term('A'), Term('B')).to_dag()
        result = {'A': {'B'}}
        assert dag == result

#   2) Ord(A, [B, C]) => A -> B, A -> C
    def test_ordered_dag_2(self):
        dag = Ord(Term('A'), [Term('B'), Term('C')]).to_dag()
        result = {'A': {'B', 'C'}}
        assert dag == result

#   3) Ord([A, B], C) => A -> C, B -> C
    def test_ordered_dag_3(self):
        dag = Ord([Term('A'), Term('B')], Term('C')).to_dag()
        result = {'A': {'C'}, 'B': {'C'}}
        assert dag == result

#   4) Ord(A, [Ord(B, C), D]) => Ord(A, [B -> C, D]) => A -> B -> C, A -> D
    def test_ordered_dag_4(self):
        dag = Ord(Term('A'), [Ord(Term('B'), Term('C')), Term('D')]).to_dag()
        result = {'A': {'B', 'D'}, 'B': {'C'}}
        assert dag == result

#   5) Ord([A, Ord(B, C)], D) => Ord([A, B -> C], D) => A -> D, B -> C -> D
    def test_ordered_dag_5(self):
        dag = Ord([Term('A'), Ord(Term('B'), Term('C'))], Term('D')).to_dag()
        result = {'A': {'D'}, 'B': {'C'}, 'C': {'D'}}
        assert dag == result

#   6) Ord(A, [Ord([B, C], D), E]) => Ord(A, [B -> D, C -> D, E]) => A -> B -> D, A -> C -> D, A -> E
    def test_ordered_dag_6(self):
        dag = Ord(Term('A'), [Ord([Term('B'), Term('C')], Term('D')), Term('E')]).to_dag()
        result = {'A': {'B', 'C', 'E'}, 'B': {'D'}, 'C': {'D'}}
        assert dag == result

#   7) Ord(A, [Ord([B, C], D), E], F) => Ord(A, [B -> D, C -> D, E], F) =>
    #       A -> B -> D -> F, A -> C -> D -> F, A -> E -> F
    def test_ordered_dag_7(self):
        dag = Ord(Term('A'), [Ord([Term('B'), Term('C')], Term('D')), Term('E')], Term('F')).to_dag()
        result = {'A': {'B', 'C', 'E'}, 'B': {'D'}, 'C': {'D'}, 'D': {'F'}, 'E': {'F'}}
        assert dag == result
