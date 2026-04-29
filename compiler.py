import re
from enum import Enum
from collections import defaultdict, deque
from typing import List, Tuple, Dict, Optional
import json

# ==================== TOKEN DEFINITIONS ====================
class TokenType(Enum):
    # Keywords
    INT = "INT"
    FLOAT = "FLOAT"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    RETURN = "RETURN"
    VOID = "VOID"
    
    # Operators
    INC = "INC"
    DEC = "DEC"
    ASSIGN = "ASSIGN"
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULT = "MULT"
    DIV = "DIV"
    MOD = "MOD"
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LE = "LE"
    GT = "GT"
    GE = "GE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    # Delimiters
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    SEMICOLON = "SEMICOLON"
    COMMA = "COMMA"
    
    # Literals
    ID = "ID"
    NUMBER = "NUMBER"
    FLOATNUM = "FLOATNUM"
    STRING = "STRING"
    AMPERSAND = "AMPERSAND"
    
    # Special
    EOF = "EOF"
    ERROR = "ERROR"

class Token:
    def __init__(self, type_: TokenType, value: str, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', {self.line}:{self.column})"

# ==================== LEXICAL ANALYZER ====================
class Lexer:
    KEYWORDS = {
        'int': TokenType.INT,
        'float': TokenType.FLOAT,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'return': TokenType.RETURN,
        'void': TokenType.VOID,
    }
    
    TOKEN_SPEC = [
        ('COMMENT',      r'//.*'),
        ('PREPROCESSOR', r'#.*'),
        ('STRING',       r'"([^"\\]|\\.)*"'),
        ('FLOATNUM',     r'\d+\.\d+'),
        ('NUMBER',       r'\d+'),
        ('ID',           r'[A-Za-z_][A-Za-z0-9_]*'),
        ('EQ',           r'=='),
        ('NE',           r'!='),
        ('LE',           r'<='),
        ('GE',           r'>='),
        ('AND',          r'&&'),
        ('OR',           r'\|\|'),
        ('INC',          r'\+\+'),
        ('DEC',          r'--'),
        ('AMPERSAND',    r'&'),
        ('ASSIGN',       r'='),
        ('LT',        r'<'),
        ('GT',        r'>'),
        ('PLUS',      r'\+'),
        ('MINUS',     r'-'),
        ('MULT',      r'\*'),
        ('DIV',       r'/'),
        ('MOD',       r'%'),
        ('NOT',       r'!'),
        ('LPAREN',    r'\('),
        ('RPAREN',    r'\)'),
        ('LBRACE',    r'\{'),
        ('RBRACE',    r'\}'),
        ('SEMICOLON', r';'),
        ('COMMA',     r','),
        ('NEWLINE',   r'\n'),
        ('SKIP',      r'[ \t]+'),
        ('MISMATCH',  r'.'),
    ]
    
    def __init__(self, code: str):
        self.code = code
        self.tokens = []
        self.errors = []
        self.line = 1
        self.column = 1
        self.pos = 0
    
    def tokenize(self) -> List[Token]:
        token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.TOKEN_SPEC)
        line_num = 1
        line_start = 0
        
        for mo in re.finditer(token_regex, self.code):
            kind = mo.lastgroup
            value = mo.group()
            column = mo.start() - line_start + 1
            
            if kind == 'NEWLINE':
                line_num += 1
                line_start = mo.end()
            elif kind in ['SKIP', 'COMMENT', 'PREPROCESSOR']:
                continue
            elif kind == 'MISMATCH':
                self.errors.append({
                    'type': 'LEXICAL_ERROR',
                    'line': line_num,
                    'column': column,
                    'message': f"Invalid character: '{value}'",
                    'phase': 'Lexical Analysis'
                })
            elif kind == 'ID':
                token_type = self.KEYWORDS.get(value, TokenType.ID)
                self.tokens.append(Token(token_type, value, line_num, column))
            else:
                token_type = TokenType[kind]
                self.tokens.append(Token(token_type, value, line_num, column))
        
        self.tokens.append(Token(TokenType.EOF, '', line_num, 0))
        return self.tokens

# ==================== ERROR HANDLER & AUTO-CORRECTOR ====================
class ErrorHandler:
    def __init__(self):
        self.errors = []
    
    def add_error(self, error_type: str, line: int, column: int, message: str, phase: str):
        error = {
            'type': error_type,
            'line': line,
            'column': column,
            'message': message,
            'phase': phase,
            'suggestion': self._get_suggestion(error_type, message)
        }
        self.errors.append(error)
    
    def _get_suggestion(self, error_type: str, message: str) -> Optional[str]:
        suggestions = {
            'SYNTAX_ERROR': {
                'Missing semicolon': 'Add semicolon (;) at the end of statement',
                'Expected RPAREN': 'Add closing parenthesis )',
                'Expected RBRACE': 'Add closing brace }',
            },
            'SEMANTIC_ERROR': {
                'Undeclared variable': 'Declare the variable with its type (int/float)',
                'Type mismatch': 'Ensure both operands have compatible types',
            }
        }
        return suggestions.get(error_type, {}).get(message)
    
    def get_corrections(self, code: str, errors: Optional[List[Dict]] = None) -> List[Tuple[str, str]]:
        """Suggest auto-corrections for common errors"""
        corrections = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if stripped and not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}'):
                if any(keyword in stripped for keyword in ['=', 'return']):
                    corrections.append((i, f"Missing semicolon at end of line {i}"))

        # Check for truly unclosed brackets across the full program.
        open_paren_lines = []
        open_brace_lines = []
        for i, line in enumerate(lines, 1):
            for ch in line:
                if ch == '(':
                    open_paren_lines.append(i)
                elif ch == ')':
                    if open_paren_lines:
                        open_paren_lines.pop()
                elif ch == '{':
                    open_brace_lines.append(i)
                elif ch == '}':
                    if open_brace_lines:
                        open_brace_lines.pop()

        for line_no in open_paren_lines:
            corrections.append((line_no, f"Unclosed parenthesis '(' at line {line_no}"))
        for line_no in open_brace_lines:
            corrections.append((line_no, f"Unclosed brace '{{' at line {line_no}"))
        
        # Add correction hints based on actual semantic/syntax errors
        for error in errors or []:
            if error.get('type') == 'SEMANTIC_ERROR' and "Undeclared variable" in error.get('message', ''):
                line_num = error.get('line', 1)
                var_name_match = re.search(r"'([^']+)'", error.get('message', ''))
                if var_name_match:
                    var_name = var_name_match.group(1)
                    corrections.append((line_num, f"Declare variable: int {var_name};"))
            elif error.get('type') == 'SYNTAX_ERROR' and error.get('message') == 'Missing semicolon':
                line_num = error.get('line', 1)
                corrections.append((line_num, f"Missing semicolon at end of line {line_num}"))
        
        # Remove duplicates while preserving order
        deduped = []
        seen = set()
        for item in corrections:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        
        return deduped

# ==================== SYMBOL TABLE ====================
class SymbolTable:
    def __init__(self):
        self.symbols = {}
        self.scopes = [{}]  # Stack of symbol tables for nested scopes
    
    def enter_scope(self):
        self.scopes.append({})
    
    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def declare(self, name: str, type_: str, line: int):
        if name in self.scopes[-1]:
            return False, f"Variable '{name}' already declared"
        self.scopes[-1][name] = {'type': type_, 'line': line}
        return True, None
    
    def lookup(self, name: str) -> Optional[str]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]['type']
        return None
    
    def get_all_symbols(self) -> Dict:
        result = {}
        for scope_idx, scope in enumerate(self.scopes):
            result[f"Scope {scope_idx}"] = scope
        return result

# ==================== AST NODES ====================
class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, declarations, statements):
        self.declarations = declarations
        self.statements = statements

class Declaration(ASTNode):
    def __init__(self, type_, name, initializer=None):
        self.type = type_
        self.name = name
        self.initializer = initializer

class Assignment(ASTNode):
    def __init__(self, name, expression):
        self.name = name
        self.expression = expression

class BinaryOp(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class Number(ASTNode):
    def __init__(self, value):
        self.value = value

class Identifier(ASTNode):
    def __init__(self, name):
        self.name = name

class StringLiteral(ASTNode):
    def __init__(self, value):
        self.value = value

class AddressOf(ASTNode):
    def __init__(self, target):
        self.target = target

class FunctionCall(ASTNode):
    def __init__(self, name, args=None):
        self.name = name
        self.args = args or []

class FunctionDefinition(ASTNode):
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body

class IfStatement(ASTNode):
    def __init__(self, condition, then_stmt, else_stmt=None):
        self.condition = condition
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

class WhileStatement(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ForStatement(ASTNode):
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

class ReturnStatement(ASTNode):
    def __init__(self, expression=None):
        self.expression = expression

# ==================== PARSER (SYNTAX ANALYZER) ====================
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.symbol_table = SymbolTable()
        self.max_errors = 120
    
    def report_error(self, error: Dict):
        if len(self.errors) >= self.max_errors:
            return
        # Avoid repeated duplicate errors from parser recovery loops
        for existing in reversed(self.errors[-10:]):
            if (
                existing.get('type') == error.get('type')
                and existing.get('line') == error.get('line')
                and existing.get('column') == error.get('column')
                and existing.get('message') == error.get('message')
            ):
                return
        self.errors.append(error)
    
    def synchronize(self):
        """Panic-mode recovery to limit cascading errors."""
        while self.current_token().type not in [TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF]:
            self.advance()
        if self.current_token().type == TokenType.SEMICOLON:
            self.advance()
    
    def current_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]
    
    def peek_token(self, offset: int = 1) -> Token:
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]
    
    def advance(self):
        self.pos += 1
    
    def expect(self, token_type: TokenType) -> bool:
        if self.current_token().type == token_type:
            self.advance()
            return True
        token = self.current_token()
        self.report_error({
            'type': 'SYNTAX_ERROR',
            'line': token.line,
            'column': token.column,
            'message': f"Expected {token_type.name}, got {token.type.name}",
            'phase': 'Syntax Analysis'
        })
        return False
    
    def parse(self) -> Program:
        declarations = []
        statements = []
        
        while self.current_token().type != TokenType.EOF:
            if len(self.errors) >= self.max_errors:
                break
            before_pos = self.pos
            if self.current_token().type in [TokenType.INT, TokenType.FLOAT, TokenType.VOID]:
                if self.peek_token().type == TokenType.ID and self.peek_token(2).type == TokenType.LPAREN:
                    func = self.parse_function_definition()
                    if func:
                        statements.append(func)
                else:
                    decls = self.parse_declaration()
                    if decls:
                        declarations.extend(decls)
            else:
                stmt = self.parse_statement()
                if stmt:
                    statements.append(stmt)
            if self.pos == before_pos:
                self.advance()
        
        return Program(declarations, statements)
    
    def parse_declaration(self) -> Optional[List[Declaration]]:
        type_token = self.current_token()
        type_name = type_token.value
        self.advance()
        
        declarations = []
        while True:
            if self.current_token().type != TokenType.ID:
                self.report_error({
                    'type': 'SYNTAX_ERROR',
                    'line': type_token.line,
                    'message': 'Expected identifier after type',
                    'phase': 'Syntax Analysis'
                })
                self.synchronize()
                return None
            
            name = self.current_token().value
            name_line = self.current_token().line
            self.advance()

            initializer = None
            if self.current_token().type == TokenType.ASSIGN:
                self.advance()
                initializer = self.parse_expression()

            declarations.append(Declaration(type_name, name, initializer))

            if self.current_token().type == TokenType.COMMA:
                self.advance()
                continue
            break
        
        if self.current_token().type == TokenType.SEMICOLON:
            self.advance()
        else:
            self.report_error({
                'type': 'SYNTAX_ERROR',
                'line': name_line,
                'column': self.current_token().column,
                'message': 'Missing semicolon',
                'phase': 'Syntax Analysis'
            })

        for declaration in declarations:
            success, error = self.symbol_table.declare(declaration.name, declaration.type, declaration.initializer.line if hasattr(declaration.initializer, 'line') else name_line)
            if not success:
                self.report_error({
                    'type': 'SEMANTIC_ERROR',
                    'line': name_line,
                    'message': error,
                    'phase': 'Semantic Analysis'
                })
        
        return declarations
    
    def parse_statement(self):
        token = self.current_token()
        
        if token.type in [TokenType.INT, TokenType.FLOAT, TokenType.VOID]:
            if self.peek_token().type == TokenType.ID:
                if self.peek_token(2).type == TokenType.LPAREN:
                    return self.parse_function_definition()
                else:
                    decls = self.parse_declaration()
                    if decls:
                        return decls
                    else:
                        self.synchronize()
                        return None
            else:
                self.report_error({
                    'type': 'SYNTAX_ERROR',
                    'line': token.line,
                    'message': 'Expected identifier after type',
                    'phase': 'Syntax Analysis'
                })
                self.synchronize()
                return None
        elif token.type == TokenType.ID:
            if self.peek_token().type == TokenType.LPAREN:
                return self.parse_function_call()
            return self.parse_assignment()
        elif token.type == TokenType.IF:
            return self.parse_if_statement()
        elif token.type == TokenType.WHILE:
            return self.parse_while_statement()
        elif token.type == TokenType.FOR:
            return self.parse_for_statement()
        elif token.type == TokenType.RETURN:
            return self.parse_return_statement()
        elif token.type == TokenType.SEMICOLON:
            self.advance()
            return None
        elif token.type == TokenType.LBRACE:
            return self.parse_block()
        else:
            self.report_error({
                'type': 'SYNTAX_ERROR',
                'line': token.line,
                'message': f"Unexpected token: {token.type.name}",
                'phase': 'Syntax Analysis'
            })
            self.synchronize()
            return None
    
    def parse_assignment_expr(self):
        name_token = self.current_token()
        name = name_token.value
        self.advance()
        
        if self.current_token().type == TokenType.INC:
            self.advance()
            return Assignment(name, BinaryOp(Identifier(name), '+', Number(1)))
        elif self.current_token().type == TokenType.DEC:
            self.advance()
            return Assignment(name, BinaryOp(Identifier(name), '-', Number(1)))
        elif self.current_token().type == TokenType.ASSIGN:
            self.advance()
            val = self.parse_expression()
            return Assignment(name, val)
        elif self.current_token().type in [TokenType.PLUS, TokenType.MINUS, TokenType.MULT, TokenType.DIV, TokenType.MOD]:
            op = self.current_token().value
            self.advance()
            if self.current_token().type == TokenType.ASSIGN:
                self.advance()
                val = self.parse_expression()
                return Assignment(name, BinaryOp(Identifier(name), op, val))
                
        self.report_error({
            'type': 'SYNTAX_ERROR',
            'line': name_token.line,
            'message': 'Expected =, ++, -- or compound assignment',
            'phase': 'Syntax Analysis'
        })
        return None

    def parse_assignment(self) -> Optional[Assignment]:
        expr = self.parse_assignment_expr()
        if not expr: return None
        
        if self.current_token().type == TokenType.SEMICOLON:
            self.advance()
        else:
            self.report_error({
                'type': 'SYNTAX_ERROR',
                'line': self.current_token().line,
                'column': self.current_token().column,
                'message': 'Missing semicolon',
                'phase': 'Syntax Analysis'
            })
        
        var_type = self.symbol_table.lookup(expr.name)
        if var_type is None:
            self.report_error({
                'type': 'SEMANTIC_ERROR',
                'line': self.current_token().line,
                'message': f"Undeclared variable '{expr.name}'",
                'phase': 'Semantic Analysis',
                'suggestion': f"Declare variable: int {expr.name};"
            })
        
        return expr
    
    def parse_function_call(self) -> Optional[FunctionCall]:
        name_token = self.current_token()
        name = name_token.value
        self.advance()
        self.expect(TokenType.LPAREN)

        args = []
        if self.current_token().type != TokenType.RPAREN:
            args.append(self.parse_expression())
            while self.current_token().type == TokenType.COMMA:
                self.advance()
                args.append(self.parse_expression())

        self.expect(TokenType.RPAREN)
        if self.current_token().type == TokenType.SEMICOLON:
            self.advance()
        else:
            self.report_error({
                'type': 'SYNTAX_ERROR',
                'line': self.current_token().line,
                'column': self.current_token().column,
                'message': 'Missing semicolon',
                'phase': 'Syntax Analysis'
            })
        
        return FunctionCall(name, args)
    
    def parse_function_definition(self) -> Optional[FunctionDefinition]:
        type_token = self.current_token()
        return_type = type_token.value
        self.advance()

        if self.current_token().type != TokenType.ID:
            self.report_error({
                'type': 'SYNTAX_ERROR',
                'line': type_token.line,
                'message': 'Expected function name after return type',
                'phase': 'Syntax Analysis'
            })
            self.synchronize()
            return None

        name = self.current_token().value
        self.advance()
        self.expect(TokenType.LPAREN)

        params = []
        if self.current_token().type != TokenType.RPAREN:
            while True:
                if self.current_token().type in [TokenType.INT, TokenType.FLOAT, TokenType.VOID] and self.peek_token().type == TokenType.ID:
                    param_type = self.current_token().value
                    self.advance()
                    param_name = self.current_token().value
                    self.advance()
                    params.append((param_type, param_name))
                else:
                    self.report_error({
                        'type': 'SYNTAX_ERROR',
                        'line': self.current_token().line,
                        'message': 'Invalid function parameter',
                        'phase': 'Syntax Analysis'
                    })
                    break

                if self.current_token().type == TokenType.COMMA:
                    self.advance()
                    continue
                break

        self.expect(TokenType.RPAREN)
        body = self.parse_block()
        return FunctionDefinition(return_type, name, params, body)
    
    def parse_expression(self):
        return self.parse_or_expression()
    
    def parse_or_expression(self):
        left = self.parse_and_expression()
        
        while self.current_token().type == TokenType.OR:
            op_token = self.current_token()
            self.advance()
            right = self.parse_and_expression()
            left = BinaryOp(left, op_token.value, right)
        
        return left
    
    def parse_and_expression(self):
        left = self.parse_comparison_expression()
        
        while self.current_token().type == TokenType.AND:
            op_token = self.current_token()
            self.advance()
            right = self.parse_comparison_expression()
            left = BinaryOp(left, op_token.value, right)
        
        return left
    
    def parse_comparison_expression(self):
        left = self.parse_additive_expression()
        
        while self.current_token().type in [TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE]:
            op_token = self.current_token()
            self.advance()
            right = self.parse_additive_expression()
            left = BinaryOp(left, op_token.value, right)
        
        return left
    
    def parse_additive_expression(self):
        left = self.parse_multiplicative_expression()
        
        while self.current_token().type in [TokenType.PLUS, TokenType.MINUS]:
            op_token = self.current_token()
            self.advance()
            right = self.parse_multiplicative_expression()
            left = BinaryOp(left, op_token.value, right)
        
        return left
    
    def parse_multiplicative_expression(self):
        left = self.parse_unary_expression()
        
        while self.current_token().type in [TokenType.MULT, TokenType.DIV, TokenType.MOD]:
            op_token = self.current_token()
            self.advance()
            right = self.parse_unary_expression()
            left = BinaryOp(left, op_token.value, right)
        
        return left
    
    def parse_unary_expression(self):
        if self.current_token().type in [TokenType.MINUS, TokenType.NOT]:
            op_token = self.current_token()
            self.advance()
            expr = self.parse_unary_expression()
            return UnaryOp(op_token.value, expr)
        elif self.current_token().type == TokenType.AMPERSAND:
            self.advance()
            target = self.parse_primary_expression()
            return AddressOf(target)
        
        return self.parse_primary_expression()
    
    def parse_primary_expression(self):
        token = self.current_token()
        
        if token.type == TokenType.NUMBER:
            self.advance()
            return Number(int(token.value))
        elif token.type == TokenType.FLOATNUM:
            self.advance()
            return Number(float(token.value))
        elif token.type == TokenType.STRING:
            self.advance()
            return StringLiteral(token.value[1:-1])
        elif token.type == TokenType.ID:
            name = token.value
            self.advance()
            if self.current_token().type == TokenType.LPAREN:
                self.advance()
                args = []
                if self.current_token().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token().type == TokenType.COMMA:
                        self.advance()
                        args.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                return FunctionCall(name, args)
            return Identifier(name)
        elif token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        else:
            self.report_error({
                'type': 'SYNTAX_ERROR',
                'line': token.line,
                'message': f"Unexpected token: {token.type.name}",
                'phase': 'Syntax Analysis'
            })
            self.synchronize()
            return None
    
    def parse_if_statement(self) -> Optional[IfStatement]:
        self.advance()  # skip 'if'
        self.expect(TokenType.LPAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN)
        
        then_stmt = self.parse_statement()
        else_stmt = None
        
        if self.current_token().type == TokenType.ELSE:
            self.advance()
            else_stmt = self.parse_statement()
        
        return IfStatement(condition, then_stmt, else_stmt)
    
    def parse_while_statement(self) -> Optional[WhileStatement]:
        self.advance()  # skip 'while'
        self.expect(TokenType.LPAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN)
        
        body = self.parse_statement()
        return WhileStatement(condition, body)

    def parse_for_statement(self) -> Optional[ForStatement]:
        self.advance()  # skip 'for'
        self.expect(TokenType.LPAREN)
        
        init = None
        if self.current_token().type != TokenType.SEMICOLON:
            init = self.parse_assignment()
        else:
            self.advance()
            
        condition = None
        if self.current_token().type != TokenType.SEMICOLON:
            condition = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        
        update = None
        if self.current_token().type != TokenType.RPAREN:
            update = self.parse_assignment_expr()
            
        self.expect(TokenType.RPAREN)
        body = self.parse_statement()
        
        return ForStatement(init, condition, update, body)
    
    def parse_return_statement(self) -> Optional[ReturnStatement]:
        self.advance()  # skip 'return'
        expr = None
        if self.current_token().type != TokenType.SEMICOLON:
            expr = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        return ReturnStatement(expr)
    
    def parse_block(self):
        self.advance()  # skip '{'
        self.symbol_table.enter_scope()
        statements = []
        
        while self.current_token().type != TokenType.RBRACE and self.current_token().type != TokenType.EOF:
            stmt = self.parse_statement()
            if stmt:
                if isinstance(stmt, list):
                    statements.extend(stmt)
                else:
                    statements.append(stmt)
        
        self.symbol_table.exit_scope()
        self.expect(TokenType.RBRACE)
        return statements

# ==================== INTERMEDIATE CODE GENERATOR (TAC) ====================
class IntermediateCodeGenerator:
    def __init__(self):
        self.tac = []
        self.temp_counter = 0
        self.label_counter = 0
    
    def new_temp(self) -> str:
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
    
    def new_label(self) -> str:
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label
    
    def emit(self, op: str, arg1: str = "", arg2: str = "", result: str = ""):
        """Emit a Three Address Code instruction"""
        self.tac.append({
            'op': op,
            'arg1': arg1,
            'arg2': arg2,
            'result': result
        })
    
    def generate(self, ast: ASTNode) -> List[Dict] | str:
        """Generate TAC from AST"""
        if isinstance(ast, Program):
            for stmt in ast.statements:
                self.generate(stmt)
        elif isinstance(ast, Declaration):
            if ast.initializer:
                self.generate_assignment(Assignment(ast.name, ast.initializer))
        elif isinstance(ast, Assignment):
            self.generate_assignment(ast)
        elif isinstance(ast, FunctionDefinition):
            self.emit("LABEL", "", "", ast.name)
            for stmt in ast.body:
                self.generate(stmt)
        elif isinstance(ast, FunctionCall):
            args = [str(self.generate(arg)) for arg in ast.args]
            result = self.new_temp()
            self.emit("CALL", ast.name, ", ".join(args), result)
            return result
        elif isinstance(ast, IfStatement):
            else_label = self.new_label()
            end_label = self.new_label()
            cond = self.generate(ast.condition)
            self.emit("JZ", cond, "", else_label)
            self.generate(ast.then_stmt)
            self.emit("JMP", "", "", end_label)
            self.emit("LABEL", "", "", else_label)
            if ast.else_stmt:
                self.generate(ast.else_stmt)
            self.emit("LABEL", "", "", end_label)
        elif isinstance(ast, WhileStatement):
            start_label = self.new_label()
            end_label = self.new_label()
            self.emit("LABEL", "", "", start_label)
            cond = self.generate(ast.condition)
            self.emit("JZ", cond, "", end_label)
            self.generate(ast.body)
            self.emit("JMP", "", "", start_label)
            self.emit("LABEL", "", "", end_label)
        elif isinstance(ast, ForStatement):
            if ast.init:
                self.generate(ast.init)
            start_label = self.new_label()
            end_label = self.new_label()
            self.emit("LABEL", "", "", start_label)
            if ast.condition:
                cond = self.generate(ast.condition)
                self.emit("JZ", cond, "", end_label)
            self.generate(ast.body)
            if ast.update:
                self.generate(ast.update)
            self.emit("JMP", "", "", start_label)
            self.emit("LABEL", "", "", end_label)
        elif isinstance(ast, ReturnStatement):
            value = self.generate(ast.expression) if ast.expression else "0"
            self.emit("RETURN", value, "", "")
        elif isinstance(ast, BinaryOp):
            return self.generate_binary_op(ast)
        elif isinstance(ast, StringLiteral):
            return ast.value
        elif isinstance(ast, AddressOf):
            return ast.target.name if isinstance(ast.target, Identifier) else str(ast.target)
        elif isinstance(ast, Number):
            return str(ast.value)
        elif isinstance(ast, Identifier):
            return ast.name
        elif isinstance(ast, list):
            for stmt in ast:
                self.generate(stmt)
        
        return self.tac
    
    def generate_assignment(self, ast: Assignment):
        val = self.generate(ast.expression) if ast.expression else "0"
        self.emit("ASSIGN", val, "", ast.name)
    
    def generate_binary_op(self, ast: BinaryOp) -> str:
        left = self.generate(ast.left) if hasattr(ast.left, '__dict__') else str(ast.left)
        right = self.generate(ast.right) if hasattr(ast.right, '__dict__') else str(ast.right)
        result = self.new_temp()
        
        self.emit(ast.op, str(left), str(right), result)
        return result

# ==================== AST VISUALIZER ====================
def ast_to_dict(node) -> Dict:
    """Convert AST to dictionary for JSON serialization"""
    if node is None:
        return None
    
    if isinstance(node, Program):
        return {
            'type': 'Program',
            'declarations': [ast_to_dict(d) for d in node.declarations],
            'statements': [ast_to_dict(s) for s in node.statements]
        }
    elif isinstance(node, Declaration):
        return {
            'type': 'Declaration',
            'varType': node.type,
            'name': node.name
        }
    elif isinstance(node, Assignment):
        return {
            'type': 'Assignment',
            'name': node.name,
            'expression': ast_to_dict(node.expression)
        }
    elif isinstance(node, BinaryOp):
        return {
            'type': 'BinaryOp',
            'operator': node.op,
            'left': ast_to_dict(node.left),
            'right': ast_to_dict(node.right)
        }
    elif isinstance(node, UnaryOp):
        return {
            'type': 'UnaryOp',
            'operator': node.op,
            'operand': ast_to_dict(node.operand)
        }
    elif isinstance(node, Number):
        return {
            'type': 'Number',
            'value': node.value
        }
    elif isinstance(node, Identifier):
        return {
            'type': 'Identifier',
            'name': node.name
        }
    elif isinstance(node, StringLiteral):
        return {
            'type': 'StringLiteral',
            'value': node.value
        }
    elif isinstance(node, AddressOf):
        return {
            'type': 'AddressOf',
            'target': ast_to_dict(node.target)
        }
    elif isinstance(node, FunctionCall):
        return {
            'type': 'FunctionCall',
            'name': node.name,
            'args': [ast_to_dict(arg) for arg in node.args]
        }
    elif isinstance(node, FunctionDefinition):
        return {
            'type': 'FunctionDefinition',
            'returnType': node.return_type,
            'name': node.name,
            'params': [{'type': p[0], 'name': p[1]} for p in node.params],
            'body': [ast_to_dict(stmt) for stmt in node.body]
        }
    elif isinstance(node, IfStatement):
        return {
            'type': 'IfStatement',
            'condition': ast_to_dict(node.condition),
            'then': ast_to_dict(node.then_stmt),
            'else': ast_to_dict(node.else_stmt) if node.else_stmt else None
        }
    elif isinstance(node, WhileStatement):
        return {
            'type': 'WhileStatement',
            'condition': ast_to_dict(node.condition),
            'body': ast_to_dict(node.body)
        }
    elif isinstance(node, ForStatement):
        return {
            'type': 'ForStatement',
            'init': ast_to_dict(node.init),
            'condition': ast_to_dict(node.condition),
            'update': ast_to_dict(node.update),
            'body': ast_to_dict(node.body)
        }
    elif isinstance(node, ReturnStatement):
        return {
            'type': 'ReturnStatement',
            'expression': ast_to_dict(node.expression)
        }
    elif isinstance(node, list):
        return [ast_to_dict(item) for item in node]

    return str(node)

# ==================== INTERPRETER ====================
class Interpreter:
    def __init__(self, input_values=None):
        self.env_stack = [{}]
        self.output = []
        self.inputs = deque(input_values or [])
        self.functions = {}
    
    def current_env(self):
        return self.env_stack[-1]
    
    def lookup(self, name: str):
        for env in reversed(self.env_stack):
            if name in env:
                return env[name]
        return 0
    
    def assign(self, name: str, value):
        for env in reversed(self.env_stack):
            if name in env:
                env[name] = value
                return
        self.current_env()[name] = value
    
    def push_env(self):
        self.env_stack.append({})
    
    def pop_env(self):
        if len(self.env_stack) > 1:
            self.env_stack.pop()
    
    def extract_input_values(self, code: str):
        import re
        match = re.search(r'//\s*input\s*:\s*([0-9\s]+)', code)
        if match:
            values = [int(x) for x in match.group(1).split() if x.isdigit()]
            self.inputs = deque(values)
        elif not self.inputs:
            self.inputs = deque([0, 0])
    
    def run(self, ast: Program, code: str = "") -> List[str]:
        if code:
            self.extract_input_values(code)

        main_func = None
        for stmt in ast.statements:
            if isinstance(stmt, FunctionDefinition):
                self.functions[stmt.name] = stmt
                if stmt.name == 'main':
                    main_func = stmt
            elif isinstance(stmt, Declaration):
                self.execute(stmt)

        if main_func:
            self.execute_function(main_func)
        else:
            for stmt in ast.statements:
                if not isinstance(stmt, FunctionDefinition):
                    self.execute(stmt)

        return self.output
    
    def execute_function(self, func: FunctionDefinition, args=None):
        self.push_env()
        for (param_type, param_name), arg in zip(func.params, args or []):
            self.current_env()[param_name] = self.evaluate(arg)
        result = self.execute_block(func.body)
        self.pop_env()
        if isinstance(result, dict) and result.get('return'):
            return result['value']
        return 0
    
    def execute_block(self, statements):
        for stmt in statements:
            result = self.execute(stmt)
            if isinstance(result, dict) and result.get('return'):
                return result
        return None
    
    def execute(self, node):
        if node is None:
            return None
        if isinstance(node, Declaration):
            self.current_env()[node.name] = self.evaluate(node.initializer) if node.initializer else 0
            return None
        if isinstance(node, Assignment):
            value = self.evaluate(node.expression)
            self.assign(node.name, value)
            return None
        if isinstance(node, FunctionCall):
            return self.execute_function_call(node)
        if isinstance(node, IfStatement):
            condition = self.evaluate(node.condition)
            if condition:
                return self.execute(node.then_stmt)
            elif node.else_stmt:
                return self.execute(node.else_stmt)
            return None
        if isinstance(node, WhileStatement):
            while self.evaluate(node.condition):
                result = self.execute(node.body)
                if isinstance(result, dict) and result.get('return'):
                    return result
            return None
        if isinstance(node, ForStatement):
            if node.init:
                self.execute(node.init)
            while node.condition is None or self.evaluate(node.condition):
                result = self.execute(node.body)
                if isinstance(result, dict) and result.get('return'):
                    return result
                if node.update:
                    self.execute(node.update)
            return None
        if isinstance(node, ReturnStatement):
            value = self.evaluate(node.expression) if node.expression else 0
            return {'return': True, 'value': value}
        if isinstance(node, list):
            return self.execute_block(node)
        return None
    
    def execute_function_call(self, node: FunctionCall):
        name = node.name
        if name == 'printf':
            formatted = self.format_printf(node.args)
            self.output.append(formatted)
            return None
        if name == 'scanf':
            self.handle_scanf(node.args)
            return None
        func = self.functions.get(name)
        if func:
            return self.execute_function(func, node.args)
        return 0
    
    def format_printf(self, args):
        if not args:
            return ''
        fmt = self.evaluate(args[0])
        values = [self.evaluate(arg) for arg in args[1:]]
        try:
            if isinstance(fmt, str):
                return fmt.replace('%d', '{}').replace('%f', '{}').format(*values)
        except Exception:
            pass
        return f"{fmt} {' '.join(str(v) for v in values)}"
    
    def handle_scanf(self, args):
        if not args:
            return
        format_str = self.evaluate(args[0])
        values = []
        if isinstance(format_str, str):
            specifiers = format_str.count('%d') + format_str.count('%f')
            for _ in range(specifiers):
                values.append(self.inputs.popleft() if self.inputs else 0)
        for target, value in zip(args[1:], values):
            if isinstance(target, AddressOf) and isinstance(target.target, Identifier):
                self.assign(target.target.name, value)
    
    def evaluate(self, node):
        if node is None:
            return 0
        if isinstance(node, Number):
            return node.value
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, Identifier):
            return self.lookup(node.name)
        if isinstance(node, AddressOf):
            return node.target.name if isinstance(node.target, Identifier) else None
        if isinstance(node, FunctionCall):
            return self.execute_function_call(node)
        if isinstance(node, BinaryOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if node.op == '+':
                return left + right
            if node.op == '-':
                return left - right
            if node.op == '*':
                return left * right
            if node.op == '/':
                return left // right if isinstance(left, int) and isinstance(right, int) and right != 0 else left / right
            if node.op == '%':
                return left % right if isinstance(right, int) and right != 0 else 0
            if node.op == '==':
                return left == right
            if node.op == '!=':
                return left != right
            if node.op == '<':
                return left < right
            if node.op == '<=':
                return left <= right
            if node.op == '>':
                return left > right
            if node.op == '>=':
                return left >= right
            if node.op == '&&':
                return bool(left) and bool(right)
            if node.op == '||':
                return bool(left) or bool(right)
        if isinstance(node, UnaryOp):
            value = self.evaluate(node.operand)
            if node.op == '-':
                return -value
            if node.op == '!':
                return not bool(value)
        return 0
    
    def format_printf(self, args):
        if not args:
            return ''
        fmt = self.evaluate(args[0])
        values = [self.evaluate(arg) for arg in args[1:]]
        try:
            if isinstance(fmt, str):
                return fmt.replace('%d', '{}').replace('%f', '{}').format(*values)
        except Exception:
            pass
        return f"{fmt} {' '.join(str(v) for v in values)}"
    
    def handle_scanf(self, args):
        if not args:
            return
        format_str = self.evaluate(args[0])
        values = []
        if isinstance(format_str, str):
            specifiers = format_str.count('%d') + format_str.count('%f')
            for _ in range(specifiers):
                values.append(self.inputs.popleft() if self.inputs else 0)
        for target, value in zip(args[1:], values):
            if isinstance(target, AddressOf) and isinstance(target.target, Identifier):
                self.assign(target.target.name, value)
    
    def evaluate(self, node):
        if node is None:
            return 0
        if isinstance(node, Number):
            return node.value
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, Identifier):
            return self.lookup(node.name)
        if isinstance(node, AddressOf):
            return node.target.name if isinstance(node.target, Identifier) else None
        if isinstance(node, BinaryOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if node.op == '+':
                return left + right
            if node.op == '-':
                return left - right
            if node.op == '*':
                return left * right
            if node.op == '/':
                return left // right if isinstance(left, int) and isinstance(right, int) and right != 0 else left / right
            if node.op == '%':
                return left % right if isinstance(right, int) and right != 0 else 0
            if node.op == '==':
                return left == right
            if node.op == '!=':
                return left != right
            if node.op == '<':
                return left < right
            if node.op == '<=':
                return left <= right
            if node.op == '>':
                return left > right
            if node.op == '>=':
                return left >= right
            if node.op == '&&':
                return bool(left) and bool(right)
            if node.op == '||':
                return bool(left) or bool(right)
        if isinstance(node, UnaryOp):
            value = self.evaluate(node.operand)
            if node.op == '-':
                return -value
            if node.op == '!':
                return not bool(value)
        return 0

# ==================== MAIN COMPILER ====================
class SmartCompiler:
    def __init__(self):
        self.lexer = None
        self.parser = None
        self.error_handler = ErrorHandler()
    
    def compile(self, code: str) -> Dict:
        """Main compilation process"""
        result = {
            'source_code': code,
            'phases': {}
        }
        
        # Phase 1: Lexical Analysis
        print("\n" + "="*60)
        print("PHASE 1: LEXICAL ANALYSIS")
        print("="*60)
        self.lexer = Lexer(code)
        tokens = self.lexer.tokenize()
        result['phases']['lexical'] = {
            'tokens': [(t.type.name, t.value, t.line, t.column) for t in tokens if t.type != TokenType.EOF],
            'errors': self.lexer.errors
        }
        
        print(f"\nTokens found: {len(tokens)-1}")
        for token in tokens[:-1]:
            print(f"  {token}")
        
        if self.lexer.errors:
            print("\nLexical Errors:")
            for error in self.lexer.errors:
                print(f"  Line {error['line']}: {error['message']}")
        
        # Phase 2: Syntax Analysis
        print("\n" + "="*60)
        print("PHASE 2: SYNTAX ANALYSIS")
        print("="*60)
        self.parser = Parser(tokens)
        ast = self.parser.parse()
        result['phases']['syntax'] = {
            'errors': self.parser.errors
        }
        
        if not self.parser.errors:
            print("[OK] Syntax is valid")
        else:
            print("Syntax Errors:")
            for error in self.parser.errors:
                print(f"  Line {error['line']}: {error['message']}")
        
        # Phase 3: Semantic Analysis
        print("\n" + "="*60)
        print("PHASE 3: SEMANTIC ANALYSIS")
        print("="*60)
        result['phases']['semantic'] = {
            'symbol_table': self.parser.symbol_table.get_all_symbols(),
            'errors': [e for e in self.parser.errors if e.get('phase') == 'Semantic Analysis']
        }
        
        semantic_errors = result['phases']['semantic']['errors']
        if not semantic_errors:
            print("[OK] Semantic validation passed")
        else:
            print("Semantic Errors:")
            for error in semantic_errors:
                print(f"  Line {error['line']}: {error['message']}")
                if error.get('suggestion'):
                    print(f"    Suggestion: {error['suggestion']}")
        
        lexical_errors = self.lexer.errors
        syntax_errors = [e for e in self.parser.errors if e.get('phase') == 'Syntax Analysis']
        semantic_errors = result['phases']['semantic']['errors']
        total_errors = len(lexical_errors) + len(syntax_errors) + len(semantic_errors)
        
        # Phase 4 + 5 should run only when previous phases have no errors
        if total_errors == 0:
            print("\n" + "="*60)
            print("PHASE 4: AST GENERATION")
            print("="*60)
            ast_dict = ast_to_dict(ast)
            result['phases']['ast'] = ast_dict
            print("[OK] AST generated successfully")
            
            print("\n" + "="*60)
            print("PHASE 5: INTERMEDIATE CODE (THREE ADDRESS CODE)")
            print("="*60)
            ic_generator = IntermediateCodeGenerator()
            tac = ic_generator.generate(ast)
            result['phases']['intermediate_code'] = tac
            
            if tac:
                print("\nThree Address Code:")
                for i, instruction in enumerate(tac, 1):
                    print(f"  {i}: {instruction['op']} {instruction['arg1']} {instruction['arg2']} -> {instruction['result']}")
            else:
                print("No intermediate code generated")
            interpreter = Interpreter()
            result['compiler_output'] = interpreter.run(ast, code)
        else:
            result['phases']['ast'] = {}
            result['phases']['intermediate_code'] = []
            result['compiler_output'] = []
            print("\nSkipping AST and intermediate code generation due to earlier errors")
        
        # Auto-correction suggestions
        print("\n" + "="*60)
        print("AUTO-CORRECTION SUGGESTIONS")
        print("="*60)
        all_errors = lexical_errors + syntax_errors + semantic_errors
        corrections = self.error_handler.get_corrections(code, all_errors)
        if corrections:
            for line_num, suggestion in corrections:
                print(f"  Line {line_num}: {suggestion}")
        else:
            print("[OK] No common errors detected")
        
        # Normalize errors into report-friendly structure
        normalized_errors = []
        for err in all_errors:
            normalized_errors.append({
                'type': err.get('type', 'UNKNOWN_ERROR'),
                'line': err.get('line', 0),
                'column': err.get('column', 0),
                'message': err.get('message', 'Unknown error'),
                'phase': err.get('phase', 'Unknown Phase'),
                'suggestion': err.get('suggestion')
            })
        
        result['auto_corrections'] = corrections
        result['all_errors'] = normalized_errors
        result['error_report'] = {
            'total_errors': len(normalized_errors),
            'by_phase': {
                'Lexical Analysis': len(lexical_errors),
                'Syntax Analysis': len(syntax_errors),
                'Semantic Analysis': len(semantic_errors),
            },
            'errors': normalized_errors
        }
        result['success'] = total_errors == 0
        
        return result

# ==================== MAIN ENTRY POINT ====================
if __name__ == "__main__":
    print("=" * 70)
    print("Web-Based Smart Educational Compiler".center(70))
    print("Simplified C-Like Language".center(70))
    print("=" * 70)
    
    print("\nEnter your source code (Type END on a new line to finish):")
    print("-" * 60)
    
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    
    code = "\n".join(lines)
    
    if code.strip():
        compiler = SmartCompiler()
        result = compiler.compile(code)
        
        print("\n" + "="*60)
        print("COMPILATION SUMMARY")
        print("="*60)
        print(f"Total Errors: {len(result['all_errors'])}")
        print(f"Lexical Errors: {len(result['phases']['lexical']['errors'])}")
        print(f"Syntax Errors: {len([e for e in result['phases']['syntax']['errors']])}")
        print(f"Semantic Errors: {len(result['phases']['semantic']['errors'])}")
    else:
        print("No code provided.")
