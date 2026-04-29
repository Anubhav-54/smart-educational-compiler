import json
from compiler import SmartCompiler

compiler = SmartCompiler()

snippets = {
    "1_hello_world": """#include <stdio.h>
int main() {
    printf("Hello, World!");
    return 0;
}""",
    "2_input_output": """#include <stdio.h>
int main() {
    int a, b;
    printf("Enter two numbers: ");
    scanf("%d %d", &a, &b);
    printf("Sum = %d", a + b);
    return 0;
}""",
    "3_if_else": """#include <stdio.h>
int main() {
    int num;
    scanf("%d", &num);
    if (num % 2 == 0)
        printf("Even");
    else
        printf("Odd");
    return 0;
}""",
    "4_loop": """#include <stdio.h>
int main() {
    int n, i;
    int fact = 1;
    scanf("%d", &n);
    for (i = 1; i <= n; i++) {
        fact *= i;
    }
    printf("Factorial = %d", fact);
    return 0;
}""",
    "5_functions": """#include <stdio.h>
int add(int a, int b) {
    return a + b;
}
int main() {
    int x = 5, y = 7;
    printf("Sum = %d", add(x, y));
    return 0;
}"""
}

results = {}
for name, code in snippets.items():
    res = compiler.compile(code)
    results[name] = {
        "success": res.get("success"),
        "syntax_errors": res.get("phases", {}).get("syntax", {}).get("errors", []),
        "semantic_errors": res.get("phases", {}).get("semantic", {}).get("errors", [])
    }

with open("test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Done compiling snippets. Results saved to test_results.json")
