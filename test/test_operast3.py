from operast.operast3 import *
from ast import *

# Examples

# 1.0
Seq(
    Module,
    And(
        FunctionDef,
        Assign(value=Num),
    )
)

# becomes 1.1
Seq(
    Module,
    And(
        FunctionDef,
        Seq(
            Assign,
            ('value', Num)
        )
    )
)

# becomes 1.2
p1 = Seq(Module, FunctionDef)
p2 = Seq(Module, Assign, ('value', Num))

# Each distinct combinations of branches which satisfy an 'And' should result
# in a match of the pattern. Thus we have to track which branches have
# satisfied the fsm and take action based on combinations of these. This
# tracking also has to be indexed by the location from which we started the
# 'And'. The indexing by location is handled by instantiating a new fsm for
# each new node we traverse.

# 2.0
Seq(
    Or(
        FunctionDef,
        ClassDef
    ),
    Call(func=Name)
)

# becomes 2.1
Seq(
    Or(
        FunctionDef,
        ClassDef,
    ),
    Call,
    ('func', Name)
)

# becomes 2.2
p3 = Seq(FunctionDef, Call, ('func', Name))
p4 = Seq(ClassDef, Call, ('func', Name))

# The AST lists in AST nodes should be transformed into 'Then' rather than
# 'And' structures, since these lists are ordered. In order to track 'Then'
# satisfaction we need to be able to order the nodes which satisfy a condition
# and ensure that for 'Then' conditions, later nodes satisfy later conditions.
# To do this we number each node (as previously thought) in such a way that
# later nodes are greater than earlier nodes. A simple solution is to start
# numbering peer nodes using a counter starting from 1 and then increase the
# counter for each peer, for each new node which we traverse to we reset the
# counter. This is also ensures we do not need to hold counter state across
# nodes. Then for each new layer, we do not add the new node value, but rather
# append the number, thus constructing a consecutive id. Thus for the structure:
#
# a -+- c
#    |
#    +- b
#
# we get:
#
# 1 -+- 11
#    |
#    +- 12
#
# Once we have this we extend all numbers to the length of the longest number,
# filling with zeroes. Thus we obtain:
#
# 10 -+- 11
#     |
#     +- 12
#
# We allows us to both ascertain parent nodes, and know the order of child
# nodes.
#
# NAH this doesn't work if a node has more than 9 children. So probably better
# to have a tuple of ints structure where we just add more entries for each
# layer of the tree. Then we count up as before with the children of each layer
# incrementing the counter for that layer in the tuple. Finally we implement a
# function (or class) which provides and ordering for these tuple of counters.
# Could use the collections.Counter class in python. Interestingly, this format
# is similar to a radix-invariant format for notating numbers.

# 3.0
ClassDef(
    body=[
        Assign,
        FunctionDef(
            body=[
                Assign
            ]
        )
    ]
)

# becomes 3.1
Seq(
    ClassDef,
    Then(
        ('body', Assign),
        Seq(
            ('body', FunctionDef),
            Then(
                ('body', Assign)
            )
        )
    )
)

# becomes 3.2
p5 = Seq(ClassDef, ('body', Assign))
p6 = Seq(ClassDef, FunctionDef, ('body', Assign))

# Repeat Sequence
#
# NB: implement a 'Times' operator which allows for easy specification of
# repeated AST elements.

# 4.0
p7 = Seq(FunctionDef, FunctionDef, Assign)
