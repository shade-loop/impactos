import os

from analyzer.parser import parse_modules, resolve_module_path
from analyzer.graph import DependencyGraph


def compute_impact(repo_path: str, changed_files: list[str]) -> dict:
    """Compute the blast-radius impact for a list of changed file paths."""
    imports = parse_modules(repo_path)
    known_modules = set(imports.keys())

    changed_modules: list[str] = []
    unknown_files: list[str] = []

    for file_path in changed_files:
        if not file_path.endswith(".py"):
            continue
        # Resolve to module name; handle both absolute and relative paths
        if os.path.isabs(file_path):
            mod = resolve_module_path(file_path, repo_path)
        else:
            abs_path = os.path.join(repo_path, file_path)
            mod = resolve_module_path(abs_path, repo_path)

        if mod in known_modules:
            changed_modules.append(mod)
        else:
            unknown_files.append(file_path)

    graph = DependencyGraph(imports)
    direct_affected, indirect_affected, max_depth = graph.get_all_affected(
        changed_modules
    )

    all_affected = direct_affected + indirect_affected
    affected_count = len(all_affected)

    return {
        "changed_files": changed_files,
        "changed_modules": changed_modules,
        "direct_affected": direct_affected,
        "indirect_affected": indirect_affected,
        "all_affected": all_affected,
        "affected_count": affected_count,
        "direct_count": len(direct_affected),
        "indirect_count": len(indirect_affected),
        "max_depth": max_depth,
        "unknown_files": unknown_files,
    }


def compute_git_impact(repo_path: str) -> dict:
    """Compute impact based on current git changes in the repository."""
    try:
        import git  # gitpython
    except ImportError as exc:
        raise ValueError("gitpython is not installed") from exc

    try:
        repo = git.Repo(repo_path)
    except git.InvalidGitRepositoryError:
        raise ValueError(f"No git repository found at: {repo_path}")
    except git.NoSuchPathError:
        raise ValueError(f"Path does not exist: {repo_path}")

    changed_paths: set[str] = set()

    # Staged changes (index vs HEAD)
    try:
        for diff in repo.index.diff("HEAD"):
            if diff.a_path:
                changed_paths.add(diff.a_path)
            if diff.b_path:
                changed_paths.add(diff.b_path)
    except Exception:
        pass

    # Unstaged changes (working tree vs index)
    try:
        for diff in repo.index.diff(None):
            if diff.a_path:
                changed_paths.add(diff.a_path)
            if diff.b_path:
                changed_paths.add(diff.b_path)
    except Exception:
        pass

    # Untracked files
    for path in repo.untracked_files:
        changed_paths.add(path)

    py_files = [p for p in changed_paths if p.endswith(".py")]

    result = compute_impact(repo_path, py_files)
    result["git_changes"] = py_files
    result["source"] = "git"

    return result
