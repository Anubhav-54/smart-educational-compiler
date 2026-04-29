from flask import Flask, request, jsonify
from flask_cors import CORS
from compiler import SmartCompiler, Lexer, TokenType
import tempfile
import subprocess
import os
import re

app = Flask(__name__)
CORS(app)  # Allow requests from index.html (different port)

compiler = SmartCompiler()


def _looks_like_full_c_code(code: str) -> bool:
    """Detect common C constructs unsupported by educational subset."""
    patterns = [
        r'^\s*#\s*include\s*<[^>]+>',
        r'\bfor\s*\(',
        r'\bprintf\s*\(',
        r'\bscanf\s*\(',
        r'\bmain\s*\(',
        r'"[^"\n]*"',  # string literal
        r'\b(int|float|char|double)\s+[A-Za-z_]\w*\s*,\s*[A-Za-z_]\w*',  # int a, b;
    ]
    return any(re.search(pattern, code, re.MULTILINE) for pattern in patterns)


def _parse_gcc_diagnostics(stderr_text):
    """Parse gcc diagnostics into normalized error entries."""
    pattern = re.compile(r"^(.+?):(\d+):(\d+):\s+(warning|error):\s+(.+)$")
    lexical = []
    syntax = []
    semantic = []
    warnings = []
    output = []

    for raw in stderr_text.splitlines():
        output.append(raw)
        match = pattern.match(raw.strip())
        if not match:
            continue

        _, line, column, level, message = match.groups()
        entry = {
            'type': 'SYNTAX_ERROR' if level == 'error' else 'WARNING',
            'line': int(line),
            'column': int(column),
            'message': message,
            'phase': 'Syntax Analysis' if level == 'error' else 'Compiler Warning'
        }
        if level == 'error':
            syntax.append(entry)
        else:
            warnings.append(entry)

    return {
        'lexical': lexical,
        'syntax': syntax,
        'semantic': semantic,
        'warnings': warnings,
        'output': output
    }


def _build_safe_c_corrections(code, diagnostics):
    """Generate only high-confidence, rule-based fixes for GCC mode."""
    include_map = {
        'printf': '#include <stdio.h>',
        'scanf': '#include <stdio.h>',
        'fgets': '#include <stdio.h>',
        'strcmp': '#include <string.h>',
        'strlen': '#include <string.h>',
        'isspace': '#include <ctype.h>',
        'isalpha': '#include <ctype.h>',
        'isalnum': '#include <ctype.h>',
        'isdigit': '#include <ctype.h>',
    }
    corrections = []
    seen = set()
    lines = code.splitlines()

    def _nearest_semicolon_candidate(start_line):
        idx = max(1, min(start_line, len(lines)))
        while idx > 0:
            text = lines[idx - 1].strip()
            if text and not text.endswith(('{', '}', ';')):
                return idx
            idx -= 1
        return max(1, min(start_line, len(lines) if lines else 1))

    for entry in diagnostics:
        message = entry.get('message', '')
        line = entry.get('line', 1)

        # Missing semicolon family
        if "expected ';'" in message:
            # GCC usually reports this at the following token line.
            suggested_line = line - 1 if "before" in message and line > 1 else line
            suggested_line = _nearest_semicolon_candidate(suggested_line)
            suggestion = f"Missing semicolon at end of line {suggested_line}"
            item = (suggested_line, suggestion)
            if item not in seen:
                seen.add(item)
                corrections.append(item)

        # Undeclared variable
        undeclared = re.search(r"'([^']+)' undeclared", message)
        if undeclared:
            var_name = undeclared.group(1)
            suggestion = f"Declare variable: int {var_name};"
            item = (line, suggestion)
            if item not in seen:
                seen.add(item)
                corrections.append(item)

        # Missing include from implicit declaration
        implicit = re.search(r"implicit declaration of function '([^']+)'", message)
        if implicit:
            fn = implicit.group(1)
            if fn in include_map:
                suggestion = f"Add include: {include_map[fn]}"
                item = (1, suggestion)
                if item not in seen:
                    seen.add(item)
                    corrections.append(item)

    # Simple structural checks as fallback
    open_paren = sum(line.count('(') for line in lines)
    close_paren = sum(line.count(')') for line in lines)
    if open_paren > close_paren:
        item = (len(lines) if lines else 1, "Unclosed parenthesis '('")
        if item not in seen:
            corrections.append(item)

    open_brace = sum(line.count('{') for line in lines)
    close_brace = sum(line.count('}') for line in lines)
    if open_brace > close_brace:
        item = (len(lines) if lines else 1, "Unclosed brace '{'")
        if item not in seen:
            corrections.append(item)

    return corrections


def _requires_runtime_input(code: str) -> bool:
    """Detect whether the C code needs runtime input via scanf or similar calls."""
    patterns = [
        r'\bscanf\s*\(',
        r'\bfgets\s*\(',
        r'\bgets\s*\(',
        r'\bgetchar\s*\(',
        r'\bgetc\s*\(',
    ]
    return any(re.search(pattern, code) for pattern in patterns)


def _run_gcc_compile_and_execute(code: str, input_values: list = None):
    """Compile C code with GCC and execute it, capturing output."""
    c_file_path = None
    exe_file_path = None
    try:
        # Create temp C file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as c_file:
            c_file.write(code)
            c_file_path = c_file.name

        # Create temp executable path
        exe_file_path = c_file_path.replace('.c', '.exe')

        # Step 1: Compile with GCC
        compile_result = subprocess.run(
            ['gcc', c_file_path, '-o', exe_file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        parsed = _parse_gcc_diagnostics(compile_result.stderr or "")
        lexical_errors = parsed['lexical']
        syntax_errors = parsed['syntax']
        semantic_errors = parsed['semantic']
        warnings = parsed['warnings']

        lexer = Lexer(code)
        lexer_tokens = lexer.tokenize()
        lexer_errors = lexer.errors
        tokens = [
            [token.type.name, token.value, token.line, token.column]
            for token in lexer_tokens
            if token.type != TokenType.EOF
        ]

        # Merge any lexer errors into lexical phase errors
        if lexer_errors:
            lexical_errors.extend(lexer_errors)

        total_errors = len(lexical_errors) + len(syntax_errors) + len(semantic_errors)

        compiler_output = []
        requires_input = _requires_runtime_input(code)
        runtime_input_needed = requires_input and not input_values
        
        # If compilation succeeded and runtime input is not required, run the executable
        if compile_result.returncode == 0 and os.path.exists(exe_file_path) and not runtime_input_needed:
            try:
                # Prepare stdin for scanf calls
                stdin_input = None
                if input_values:
                    stdin_input = '\n'.join(str(v) for v in input_values) + '\n'
                
                # Run the executable
                run_result = subprocess.run(
                    [exe_file_path],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    input=stdin_input
                )
                
                # Combine stdout and stderr
                if run_result.stdout:
                    compiler_output.extend(run_result.stdout.split('\n'))
                if run_result.stderr:
                    compiler_output.extend(run_result.stderr.split('\n'))
                    
                # Remove empty trailing lines
                while compiler_output and compiler_output[-1] == '':
                    compiler_output.pop()
                    
            except subprocess.TimeoutExpired:
                compiler_output = ['[Program timed out after 5 seconds]']
            except Exception as e:
                compiler_output = [f'[Execution error: {str(e)}]']
        elif runtime_input_needed:
            compiler_output = ['[Compiled successfully. Program requires runtime input to execute.]']
        
        auto_corrections = _build_safe_c_corrections(
            code,
            syntax_errors + warnings
        )

        response = {
            'success': total_errors == 0 and compile_result.returncode == 0,
            'total_errors': total_errors,
            'tokens': tokens,
            'errors': {
                'lexical': lexical_errors,
                'syntax': syntax_errors,
                'semantic': semantic_errors,
            },
            'symbol_table': {},
            'ast': {},
            'intermediate_code': [],
            'auto_corrections': auto_corrections,
            'warnings': warnings,
            'warning_count': len(warnings),
            'runtime_input_needed': runtime_input_needed,
            'compiler_output': compiler_output if compiler_output else (parsed['output'] if not total_errors else []),
            'error_report': {
                'total_errors': total_errors,
                'by_phase': {
                    'Lexical Analysis': len(lexical_errors),
                    'Syntax Analysis': len(syntax_errors),
                    'Semantic Analysis': len(semantic_errors),
                },
                'errors': syntax_errors,
            },
            'mode': 'c-compiler',
            'source_code': code,
        }
        return jsonify(response)
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'GCC not found. Please install MinGW GCC and add it to PATH.',
            'total_errors': 1,
            'compiler_output': [],
            'mode': 'c-compiler'
        }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Compilation timed out.',
            'total_errors': 1,
            'compiler_output': [],
            'mode': 'c-compiler'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'total_errors': 1,
            'compiler_output': [],
            'mode': 'c-compiler'
        }), 500
    finally:
        # Cleanup temporary files
        if c_file_path and os.path.exists(c_file_path):
            try:
                os.remove(c_file_path)
            except:
                pass
        if exe_file_path and os.path.exists(exe_file_path):
            try:
                os.remove(exe_file_path)
            except:
                pass


def _run_gcc_syntax_check(code: str):
    """Run GCC syntax-only validation and normalize API response."""
    c_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as c_file:
            c_file.write(code)
            c_file_path = c_file.name

        result = subprocess.run(
            ['gcc', '-fsyntax-only', c_file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        parsed = _parse_gcc_diagnostics(result.stderr or "")
        lexical_errors = parsed['lexical']
        syntax_errors = parsed['syntax']
        semantic_errors = parsed['semantic']
        warnings = parsed['warnings']
        auto_corrections = _build_safe_c_corrections(
            code,
            syntax_errors + warnings
        )
        total_errors = len(lexical_errors) + len(syntax_errors) + len(semantic_errors)

        response = {
            'success': total_errors == 0 and result.returncode == 0,
            'total_errors': total_errors,
            'tokens': [],
            'errors': {
                'lexical': lexical_errors,
                'syntax': syntax_errors,
                'semantic': semantic_errors,
            },
            'symbol_table': {},
            'ast': {},
            'intermediate_code': [],
            'auto_corrections': auto_corrections,
            'warnings': warnings,
            'warning_count': len(warnings),
            'error_report': {
                'total_errors': total_errors,
                'by_phase': {
                    'Lexical Analysis': len(lexical_errors),
                    'Syntax Analysis': len(syntax_errors),
                    'Semantic Analysis': len(semantic_errors),
                },
                'errors': syntax_errors,
            },
            'compiler_output': parsed['output'],
            'mode': 'c-compiler'
        }
        return jsonify(response)
    finally:
        if c_file_path and os.path.exists(c_file_path):
            os.remove(c_file_path)

@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400

    code = data['code']

    try:
        result = compiler.compile(code)

        # Flatten the response into the shape index.html expects
        phases = result.get('phases', {})
        all_errors = result.get('all_errors', [])

        tokens = phases.get('lexical', {}).get('tokens', [])
        lexical_errors  = phases.get('lexical', {}).get('errors', [])
        syntax_errors   = [e for e in phases.get('syntax', {}).get('errors', [])
                           if e.get('phase') == 'Syntax Analysis']
        semantic_errors = phases.get('semantic', {}).get('errors', [])
        symbol_table    = phases.get('semantic', {}).get('symbol_table', {})
        ast             = phases.get('ast', {})
        intermediate    = phases.get('intermediate_code', [])

        total_errors = len(lexical_errors) + len(syntax_errors) + len(semantic_errors)

        response = {
            'success': total_errors == 0,
            'total_errors': total_errors,
            'tokens': tokens,
            'errors': {
                'lexical':  lexical_errors,
                'syntax':   syntax_errors,
                'semantic': semantic_errors,
            },
            'symbol_table': symbol_table,
            'ast': ast,
            'intermediate_code': intermediate,
            'compiler_output': result.get('compiler_output', []),
            'auto_corrections': result.get('auto_corrections', []),
            'error_report': result.get('error_report', {}),
            'source_code': code,
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/compile-c', methods=['POST'])
def compile_c_code():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400

    code = data['code']
    input_values = data.get('input_values', [])

    try:
        return _run_gcc_compile_and_execute(code, input_values)
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': "gcc not found. Install MinGW GCC and add it to PATH.",
            'mode': 'c-compiler'
        }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Compilation timed out.',
            'mode': 'c-compiler'
        }), 500
    except Exception as e:
        return jsonify({'error': str(e), 'success': False, 'mode': 'c-compiler'}), 500


@app.route('/api/execute-with-input', methods=['POST'])
def execute_with_input():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400

    code = data['code']
    input_values = data.get('input_values', [])

    try:
        # Re-compile the code to get the AST
        result = compiler.compile(code)
        
        # If compilation succeeded, run interpreter with provided inputs
        if result.get('compiler_output') is not None:
            # The AST was already run with default inputs, now run with user inputs
            # We need to re-run the interpreter with the new inputs
            phases = result.get('phases', {})
            
            # Check if we have a valid AST for execution
            if phases.get('ast'):
                # Re-parse to get the actual AST object (not dict)
                from compiler import Lexer, Parser, Interpreter
                lexer = Lexer(code)
                tokens = lexer.tokenize()
                parser = Parser(tokens)
                ast = parser.parse()
                
                # Run interpreter with user-provided inputs
                interpreter = Interpreter(input_values=input_values)
                output = interpreter.run(ast, code)
                result['compiler_output'] = output
        
        # Flatten the response
        phases = result.get('phases', {})
        all_errors = result.get('all_errors', [])
        
        tokens = phases.get('lexical', {}).get('tokens', [])
        lexical_errors = phases.get('lexical', {}).get('errors', [])
        syntax_errors = [e for e in phases.get('syntax', {}).get('errors', [])
                        if e.get('phase') == 'Syntax Analysis']
        semantic_errors = phases.get('semantic', {}).get('errors', [])
        symbol_table = phases.get('semantic', {}).get('symbol_table', {})
        ast = phases.get('ast', {})
        intermediate = phases.get('intermediate_code', [])
        
        total_errors = len(lexical_errors) + len(syntax_errors) + len(semantic_errors)
        
        response = {
            'success': total_errors == 0,
            'total_errors': total_errors,
            'tokens': tokens,
            'errors': {
                'lexical': lexical_errors,
                'syntax': syntax_errors,
                'semantic': semantic_errors,
            },
            'symbol_table': symbol_table,
            'ast': ast,
            'intermediate_code': intermediate,
            'compiler_output': result.get('compiler_output', []),
            'auto_corrections': result.get('auto_corrections', []),
            'error_report': result.get('error_report', {}),
            'source_code': code,
        }
        
        return jsonify(response)
    
    except Exception as e:
        import traceback
        print(f"Error in execute_with_input: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/execute-c-with-input', methods=['POST'])
def execute_c_with_input():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400

    code = data['code']
    input_values = data.get('input_values', [])

    try:
        return _run_gcc_compile_and_execute(code, input_values)
    except Exception as e:
        return jsonify({'error': str(e), 'success': False, 'mode': 'c-compiler'}), 500


if __name__ == '__main__':
    print("Starting Smart Compiler API on http://localhost:5000")
    app.run(debug=True, port=5000)
