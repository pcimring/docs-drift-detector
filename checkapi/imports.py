import ast
import sys

PACKAGE_OVERRIDES = {
    "langchain_openai": "langchain-openai",
    "langchain_core": "langchain-core",
    "langchain_community": "langchain-community",
    "langchain_anthropic": "langchain-anthropic",
    "langgraph": "langgraph",
    "yaml": "pyyaml",
}

STDLIB_MODULES = set(sys.stdlib_module_names)


def resolve_packages(code: str) -> list[str]:
    tree = ast.parse(code)
    top_level_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top_level_modules.add(node.module.split(".")[0])

    packages = set()
    for module_name in top_level_modules:
        if module_name in STDLIB_MODULES:
            continue
        packages.add(PACKAGE_OVERRIDES.get(module_name, module_name.replace("_", "-")))

    return sorted(packages)
