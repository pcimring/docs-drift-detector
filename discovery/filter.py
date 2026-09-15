import ast
import builtins

BUILTIN_NAMES = set(dir(builtins))


def is_runnable_candidate(code: str) -> bool:
    """Heuristic: does this snippet import something and resolve every name it uses?

    Names are classified by `ctx` in a single walk. One rule therefore covers
    every binding form that produces a `Name` with `ctx=Store`/`Del`: plain
    assignment, annotated and augmented assignment, `for` targets,
    `with`/`async with` `as` targets, comprehension targets and walrus. Only
    binders that produce no such `Name` node need explicit handling below.

    Reading `ctx` also fixes a false positive: in `obj.field = x` the store
    target is an `Attribute`, and `obj` inside it is a `Load`, so `obj` counts
    as used rather than defined.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    has_import = False
    defined_names: set[str] = set()
    used_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                defined_names.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
        elif isinstance(node, ast.Import):
            has_import = True
            for alias in node.names:
                defined_names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            has_import = True
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # A def/class statement binds its own name in the enclosing scope.
            defined_names.add(node.name)
        elif isinstance(node, ast.arg):
            # Covers positional, keyword-only, *args, **kwargs and lambda args.
            defined_names.add(node.arg)
        elif isinstance(node, ast.ExceptHandler):
            if node.name is not None:
                defined_names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            defined_names.update(node.names)

    if not has_import:
        return False

    unresolved = used_names - defined_names - BUILTIN_NAMES
    return len(unresolved) == 0
