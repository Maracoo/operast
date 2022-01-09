#
# def test_branch_expand_ast_inst():
#     ast_inst = ast.ClassDef(
#         name='SomeClass',
#         body=[ast.Assign],
#     )
#     expanded = branch_expand(ast_inst)
#     expected = Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign))))
#     result = branch_equals(expanded, expected)
#     assert result, (expanded, expected)
#
#
# def test_branch_expand_ast_type():
#     ast_type = ast.ClassDef
#     expanded = branch_expand(ast_type)
#     expected = ast.ClassDef
#     result = branch_equals(expanded, expected)
#     assert result, (expanded, expected)
#
#
# def test_branch_expand_branch_pattern():
#     branch_pattern = And(ast.ClassDef(
#         name='SomeClass',
#         body=[ast.Assign],
#     ))
#     expanded = branch_expand(branch_pattern)
#     expected = And(Branch(ast.ClassDef(name='SomeClass'), And(Then(('body', ast.Assign)))))
#     result = branch_equals(expanded, expected)
#     assert result, (expanded, expected)
#
#
# def test_branch_expand_tuple_ast_type():
#     tuple_ast_type = ('body', ast.ClassDef)
#     expanded = branch_expand(tuple_ast_type)
#     expected = ('body', ast.ClassDef)
#     result = branch_equals(expanded, expected)
#     assert result, (expanded, expected)
#
#
# def test_branch_expand_tuple_ast_inst():
#     tuple_ast_inst = ('body', ast.Name(ctx=ast.Load()))
#     expanded = branch_expand(tuple_ast_inst)
#     expected = Branch(('body', ast.Name()), And(('ctx', ast.Load())))
#     result = branch_equals(expanded, expected)
#     assert result, (expanded, expected)
#
