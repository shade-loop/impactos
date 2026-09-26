"""
analyzer.repo_analyzer
~~~~~~~~~~~~~~~~~~~~~~

Orchestrates the full analysis pipeline for a Python repository.

Given a root directory, :class:`RepoAnalyzer` walks all ``.py`` files,
parses each one with :func:`analyzer.parser.parse_file`, and translates the
extracted symbols into a populated :class:`~analyzer.graph.DependencyGraph`.

Only modules that belong to the target repository are represented as graph
nodes.  External / stdlib imports that cannot be resolved to a file within the
repo are recorded as ``"imports"`` edges to a target node whose ID matches the
imported name — but only if that name corresponds to another module already
present in the graph.  This keeps the graph focused on resolvable project code.
"""

from __future__ import annotations

import logging
from pathlib import Path

from analyzer.graph import DependencyGraph, GraphEdge, GraphNode
from analyzer.parser import ParsedModule, parse_file

logger = logging.getLogger(__name__)


class RepoAnalyzer:
    """Analyse a local Python repository and build a dependency graph.

    Usage::

        analyzer = RepoAnalyzer("/path/to/my_project")
        graph = analyzer.analyze()
        deps = graph.find_indirect_dependents("my_project.utils")

    Args:
        repo_path: Root directory of the repository to analyse.  May be a
                   :class:`str` or :class:`~pathlib.Path`.
    """

    def __init__(self, repo_path: str | Path) -> None:
        self._root = Path(repo_path).resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> DependencyGraph:
        """Walk the repository, parse every Python file, and build the graph.

        Pipeline
        --------
        1. Walk all ``.py`` files under :attr:`_root`.
        2. Parse each file with :func:`parse_file`.
        3. Create a ``"module"`` node per file.
        4. Create ``"class"`` and ``"function"`` nodes for every definition,
           connected to the owning module node via ``"defines_class"`` /
           ``"defines_function"`` edges.
        5. Add ``"imports"`` edges to other modules that are resolvable
           within the project (stdlib/external imports are skipped — they are
           not present as nodes so the edge would be dangling noise).
        6. Add ``"calls"`` edges for function calls whose targets can be
           resolved to a known function node within the project.

        Returns:
            A populated :class:`~analyzer.graph.DependencyGraph`.
        """
        graph = DependencyGraph()
        python_files = _walk_python_files(self._root)

        # First pass — parse every file and register module nodes so that the
        # second pass can resolve cross-file references.
        parsed: list[ParsedModule] = []
        for path in python_files:
            module_name = _module_name_from_path(self._root, path)
            pm = parse_file(path)
            pm.module_name = module_name  # override the stem-only default
            parsed.append(pm)

            module_node = GraphNode(
                id=module_name,
                type="module",
                file_path=str(path),
                symbol_name=module_name.split(".")[-1],
            )
            graph.add_node(module_node)

        # Build a set of known module IDs for fast lookup.
        known_module_ids: set[str] = {
            n.id for n in graph.get_nodes() if n.type == "module"
        }

        # Build a set of known function node IDs (populated below during the
        # definition pass) for resolving call edges.
        known_function_ids: set[str] = set()

        # Second pass — emit definition nodes and definition edges.
        for pm in parsed:
            for class_name in pm.classes:
                node_id = f"{pm.module_name}.{class_name}"
                graph.add_node(
                    GraphNode(
                        id=node_id,
                        type="class",
                        file_path=pm.file_path,
                        symbol_name=class_name,
                    )
                )
                graph.add_edge(
                    GraphEdge(
                        source=pm.module_name,
                        target=node_id,
                        relationship="defines_class",
                    )
                )

            for func_name in pm.functions:
                node_id = f"{pm.module_name}.{func_name}"
                graph.add_node(
                    GraphNode(
                        id=node_id,
                        type="function",
                        file_path=pm.file_path,
                        symbol_name=func_name,
                    )
                )
                known_function_ids.add(node_id)
                graph.add_edge(
                    GraphEdge(
                        source=pm.module_name,
                        target=node_id,
                        relationship="defines_function",
                    )
                )

        # Third pass — emit import edges (project modules only) and call edges.
        for pm in parsed:
            for imported_name in pm.imports:
                # Resolve relative-style imports and dotted submodule imports.
                # Try the full dotted name first, then parent packages.
                resolved = _resolve_import(imported_name, known_module_ids)
                if resolved is None:
                    logger.debug(
                        "Skipping unresolvable import %r in %s",
                        imported_name,
                        pm.module_name,
                    )
                    continue
                graph.add_edge(
                    GraphEdge(
                        source=pm.module_name,
                        target=resolved,
                        relationship="imports",
                    )
                )

            for call_name in pm.calls:
                # Try to match simple names to functions in the same module,
                # then to fully-qualified names known in the graph.
                resolved_call = _resolve_call(
                    call_name, pm.module_name, known_function_ids
                )
                if resolved_call is None:
                    continue
                graph.add_edge(
                    GraphEdge(
                        source=pm.module_name,
                        target=resolved_call,
                        relationship="calls",
                    )
                )

        return graph


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


def _walk_python_files(root: Path) -> list[Path]:
    """Return all ``.py`` files under *root*, excluding ``__pycache__``.

    Args:
        root: Root directory to walk.

    Returns:
        Sorted list of absolute :class:`~pathlib.Path` objects pointing to
        ``.py`` files.
    """
    return sorted(
        p
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _module_name_from_path(root: Path, file_path: Path) -> str:
    """Convert an absolute file path to a dotted Python module name.

    Examples::

        _module_name_from_path(
            Path("/repo"),
            Path("/repo/sample_app/utils.py"),
        )
        # → "sample_app.utils"

        _module_name_from_path(
            Path("/repo"),
            Path("/repo/sample_app/__init__.py"),
        )
        # → "sample_app"

    Args:
        root:      Repository root directory.
        file_path: Absolute path to a ``.py`` file inside *root*.

    Returns:
        Dotted module name string.
    """
    relative = file_path.relative_to(root)
    parts = list(relative.with_suffix("").parts)
    # Treat __init__ as the package itself (drop the trailing component).
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else root.name


def _resolve_import(
    imported_name: str, known_module_ids: set[str]
) -> str | None:
    """Attempt to resolve an imported name to a known project module ID.

    Tries the full dotted name, then successively shorter prefixes, to
    handle ``from sample_app.utils import format_user`` → ``sample_app.utils``.

    Args:
        imported_name:    The raw imported module name (e.g. ``"sample_app.utils"``).
        known_module_ids: Set of module IDs that exist in the project.

    Returns:
        The matching module ID, or ``None`` if the import cannot be resolved
        to a project module.
    """
    # Exact match (most common).
    if imported_name in known_module_ids:
        return imported_name

    # Try progressively shorter dotted prefixes so that
    # "sample_app.utils.format_user" resolves to "sample_app.utils".
    parts = imported_name.split(".")
    for length in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:length])
        if candidate in known_module_ids:
            return candidate

    return None


def _resolve_call(
    call_name: str,
    module_name: str,
    known_function_ids: set[str],
) -> str | None:
    """Attempt to resolve a call expression name to a known function node ID.

    Strategy:
    1. ``"<module_name>.<call_name>"`` — unqualified local call.
    2. The raw ``call_name`` itself — fully-qualified call (already dotted).

    Args:
        call_name:          The call expression as extracted by the AST visitor.
        module_name:        Dotted name of the module that contains the call.
        known_function_ids: Set of all function node IDs in the graph.

    Returns:
        The matching function node ID, or ``None`` if unresolvable.
    """
    local_id = f"{module_name}.{call_name}"
    if local_id in known_function_ids:
        return local_id
    if call_name in known_function_ids:
        return call_name
    return None
