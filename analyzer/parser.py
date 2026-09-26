import ast
import os


def resolve_module_path(file_path: str, repo_path: str) -> str:
    """Convert a file path like sample_app/utils.py to sample_app.utils."""
    rel = os.path.relpath(file_path, repo_path)
    # Normalise separators
    rel = rel.replace(os.sep, "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith("/__init__"):
        rel = rel[: -len("/__init__")]
    return rel.replace("/", ".")


def parse_modules(repo_path: str) -> dict[str, set[str]]:
    """Walk all .py files in repo_path, extract import relationships.

    Returns a dict mapping module_name -> set of module names it imports.
    """
    imports: dict[str, set[str]] = {}

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Skip irrelevant directories in-place so os.walk doesn't descend
        dirnames[:] = [
            d for d in dirnames if d not in ("__pycache__", ".git")
        ]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            file_path = os.path.join(dirpath, filename)
            module_name = resolve_module_path(file_path, repo_path)

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=file_path)
            except SyntaxError:
                continue

            module_imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_imports.add(node.module)

            imports[module_name] = module_imports

    return imports
