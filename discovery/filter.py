import ast
import builtins

BUILTIN_NAMES = set(dir(builtins))


def is_runnable_candidate(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    has_import = False
    defined_names: set[str] = set()
    used_names: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node):
            nonlocal has_import
            has_import = True
            for alias in node.names:
                defined_names.add((alias.asname or alias.name).split(".")[0])
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            nonlocal has_import
            has_import = True
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
            self.generic_visit(node)

        def visit_Assign(self, node):
            for target in node.targets:
                for name_node in ast.walk(target):
                    if isinstance(name_node, ast.Name):
                        defined_names.add(name_node.id)
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            defined_names.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            defined_names.add(node.name)
            self.generic_visit(node)

        def visit_For(self, node):
            for name_node in ast.walk(node.target):
                if isinstance(name_node, ast.Name):
                    defined_names.add(name_node.id)
            self.generic_visit(node)

        def visit_With(self, node):
            for item in node.items:
                if item.optional_vars:
                    for name_node in ast.walk(item.optional_vars):
                        if isinstance(name_node, ast.Name):
                            defined_names.add(name_node.id)
            self.generic_visit(node)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            self.generic_visit(node)

    Visitor().visit(tree)

    if not has_import:
        return False

    unresolved = used_names - defined_names - BUILTIN_NAMES
    return len(unresolved) == 0
