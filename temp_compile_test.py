from compiler import SmartCompiler
import json
compiler = SmartCompiler()
tests = {
    'declaration_assignment': 'int x = 5; int y = x + 2;',
    'if_else': 'int a = 10; if (a > 5) { a = a - 2; } else { a = a + 2; }',
    'while_loop': 'int i = 0; while (i < 3) { i = i + 1; }',
    'function_main': 'int add(int a, int b) { return a + b; } int main() { int result = add(2, 3); }',
    'printf_scanf': 'int main() { int x; scanf("%d", &x); printf("%d", x); } // input: 7',
}
for name, code in tests.items():
    print('=== TEST:', name, '===')
    result = compiler.compile(code)
    print('success:', result['success'])
    print('tokens:', result['phases']['lexical']['tokens'])
    print('syntax_errors:', result['phases']['syntax']['errors'])
    print('semantic_errors:', result['phases']['semantic']['errors'])
    print('symbol_table:', result['phases']['semantic']['symbol_table'])
    print('ast:', json.dumps(result['phases'].get('ast', {}), indent=2))
    print('tac:', json.dumps(result['phases'].get('intermediate_code', []), indent=2))
    print('output:', result.get('compiler_output'))
    print('auto_corrections:', result['auto_corrections'])
    print()
