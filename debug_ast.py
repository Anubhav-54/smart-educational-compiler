from compiler import Lexer, Parser, ast_to_dict, IfStatement
code = 'int a = 10; if (a > 5) { a = a - 2; } else { a = a + 2; }'
tokens = Lexer(code).tokenize()
ast = Parser(tokens).parse()
print(type(ast.statements[0]))
print(isinstance(ast.statements[0], IfStatement))
print(ast_to_dict(ast.statements[0]))
print(ast_to_dict(ast))
