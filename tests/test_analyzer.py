"""
tests.test_analyzer
~~~~~~~~~~~~~~~~~~~

Unit tests for the ImpactOS repository analysis engine (Task 01).

Covers:
    1. Repository discovery
    2. AST parsing — class extraction
    3. AST parsing — import and function extraction
    4. Import extraction from a multi-import module
    5. Graph construction — nodes and edges
    6. Direct dependency lookup  (forward traversal)
    7. Indirect dependency lookup (forward BFS transitive closure)
    8. Direct dependent lookup   (reverse traversal)
    9. Indirect dependent lookup — blast-radius (reverse BFS)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure the analyzer package and the fixture repo are importable when tests
# are run from the impactos/ directory.
# ---------------------------------------------------------------------------
IMPACTOS_DIR = Path(__file__).parent.parent.resolve()
# The analyzer root must be the directory that *contains* sample_app/ so that
# module names are computed as "sample_app.models", not bare "models".
FIXTURE_REPO_ROOT = IMPACTOS_DIR / "tests" / "fixtures"
FIXTURE_ROOT = FIXTURE_REPO_ROOT / "sample_app"

if str(IMPACTOS_DIR) not in sys.path:
    sys.path.insert(0, str(IMPACTOS_DIR))

from analyzer import (  # noqa: E402
    DependencyGraph,
    GraphEdge,
    GraphNode,
    ParsedModule,
    RepoAnalyzer,
    parse_file,
)


# ---------------------------------------------------------------------------
# Shared session-scoped fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def graph() -> DependencyGraph:
    """Run RepoAnalyzer once over the fixture repository for the whole session."""
    return RepoAnalyzer(FIXTURE_REPO_ROOT).analyze()


# ---------------------------------------------------------------------------
# Test 1 — Repository discovery
# ---------------------------------------------------------------------------


def test_repository_discovery() -> None:
    """RepoAnalyzer must discover every .py file in the fixture repository."""
    from analyzer.repo_analyzer import _walk_python_files

    found = _walk_python_files(FIXTURE_ROOT)
    found_names = {p.name for p in found}

    expected = {"__init__.py", "models.py", "utils.py", "service.py", "main.py"}
    assert expected == found_names, (
        f"Expected files {expected}, got {found_names}"
    )


# ---------------------------------------------------------------------------
# Test 2 — AST parsing: class extraction
# ---------------------------------------------------------------------------


def test_ast_parsing_classes() -> None:
    """parse_file on models.py must return both defined class names."""
    pm = parse_file(FIXTURE_ROOT / "models.py")

    assert "User" in pm.classes, "Expected class 'User' in models.py"
    assert "Product" in pm.classes, "Expected class 'Product' in models.py"


# ---------------------------------------------------------------------------
# Test 3 — AST parsing: imports and functions
# ---------------------------------------------------------------------------


def test_ast_parsing_imports_and_functions() -> None:
    """parse_file on utils.py must return correct imports and function names."""
    pm = parse_file(FIXTURE_ROOT / "utils.py")

    assert "sample_app.models" in pm.imports, (
        "utils.py must import 'sample_app.models'"
    )
    assert "format_user" in pm.functions, (
        "utils.py must define 'format_user'"
    )
    assert "format_product" in pm.functions, (
        "utils.py must define 'format_product'"
    )


# ---------------------------------------------------------------------------
# Test 4 — Import extraction: multi-import module
# ---------------------------------------------------------------------------


def test_import_extraction_service() -> None:
    """parse_file on service.py must record imports of both utils and models."""
    pm = parse_file(FIXTURE_ROOT / "service.py")

    assert "sample_app.utils" in pm.imports, (
        "service.py must import 'sample_app.utils'"
    )
    assert "sample_app.models" in pm.imports, (
        "service.py must import 'sample_app.models'"
    )


# ---------------------------------------------------------------------------
# Test 5 — Graph construction
# ---------------------------------------------------------------------------


def test_graph_contains_module_nodes(graph: DependencyGraph) -> None:
    """The graph must contain a 'module' node for every fixture file."""
    node_ids = {n.id for n in graph.get_nodes()}

    for expected_id in (
        "sample_app",
        "sample_app.models",
        "sample_app.utils",
        "sample_app.service",
        "sample_app.main",
    ):
        assert expected_id in node_ids, (
            f"Expected module node '{expected_id}' in graph"
        )


def test_graph_contains_class_nodes(graph: DependencyGraph) -> None:
    """The graph must contain 'class' nodes for User and Product."""
    node_ids = {n.id for n in graph.get_nodes()}

    assert "sample_app.models.User" in node_ids
    assert "sample_app.models.Product" in node_ids


def test_graph_contains_function_nodes(graph: DependencyGraph) -> None:
    """The graph must contain 'function' nodes for utility functions."""
    node_ids = {n.id for n in graph.get_nodes()}

    assert "sample_app.utils.format_user" in node_ids
    assert "sample_app.utils.format_product" in node_ids


def test_graph_contains_import_edges(graph: DependencyGraph) -> None:
    """The graph must have 'imports' edges for project-internal imports."""
    import_edges = {
        (e.source, e.target)
        for e in graph.get_edges()
        if e.relationship == "imports"
    }

    # utils → models
    assert ("sample_app.utils", "sample_app.models") in import_edges
    # service → utils
    assert ("sample_app.service", "sample_app.utils") in import_edges
    # service → models
    assert ("sample_app.service", "sample_app.models") in import_edges
    # main → service
    assert ("sample_app.main", "sample_app.service") in import_edges


def test_graph_contains_defines_edges(graph: DependencyGraph) -> None:
    """The graph must have 'defines_class' and 'defines_function' edges."""
    edge_tuples = {
        (e.source, e.target, e.relationship) for e in graph.get_edges()
    }

    assert ("sample_app.models", "sample_app.models.User", "defines_class") in edge_tuples
    assert ("sample_app.models", "sample_app.models.Product", "defines_class") in edge_tuples
    assert (
        "sample_app.utils",
        "sample_app.utils.format_user",
        "defines_function",
    ) in edge_tuples


# ---------------------------------------------------------------------------
# Test 6 — Direct dependency lookup (forward)
# ---------------------------------------------------------------------------


def test_direct_dependencies_of_main(graph: DependencyGraph) -> None:
    """main's direct dependencies must include service and models."""
    dep_ids = {n.id for n in graph.find_direct_dependencies("sample_app.main")}

    assert "sample_app.service" in dep_ids, (
        "sample_app.main must directly depend on sample_app.service"
    )
    assert "sample_app.models" in dep_ids, (
        "sample_app.main must directly depend on sample_app.models"
    )


# ---------------------------------------------------------------------------
# Test 7 — Indirect dependency lookup (forward BFS)
# ---------------------------------------------------------------------------


def test_indirect_dependencies_of_main(graph: DependencyGraph) -> None:
    """main's transitive dependencies must include service, utils, and models."""
    dep_ids = {n.id for n in graph.find_indirect_dependencies("sample_app.main")}

    for expected in ("sample_app.service", "sample_app.utils", "sample_app.models"):
        assert expected in dep_ids, (
            f"sample_app.main must transitively depend on {expected}"
        )


def test_indirect_dependencies_excludes_self(graph: DependencyGraph) -> None:
    """The result of find_indirect_dependencies must not include the start node."""
    dep_ids = {n.id for n in graph.find_indirect_dependencies("sample_app.main")}
    assert "sample_app.main" not in dep_ids


# ---------------------------------------------------------------------------
# Test 8 — Direct dependent lookup (reverse)
# ---------------------------------------------------------------------------


def test_direct_dependents_of_utils(graph: DependencyGraph) -> None:
    """utils must be directly depended on by service (and only project modules)."""
    dependent_ids = {
        n.id for n in graph.find_direct_dependents("sample_app.utils")
    }

    assert "sample_app.service" in dependent_ids, (
        "sample_app.service must be a direct dependent of sample_app.utils"
    )
    # main does NOT directly import utils — it imports service.
    assert "sample_app.main" not in dependent_ids, (
        "sample_app.main must NOT be a direct dependent of sample_app.utils"
    )


# ---------------------------------------------------------------------------
# Test 9 — Indirect dependent lookup — blast radius (reverse BFS)
# ---------------------------------------------------------------------------


def test_indirect_dependents_of_utils(graph: DependencyGraph) -> None:
    """Blast-radius of utils must include both service and main."""
    dependent_ids = {
        n.id for n in graph.find_indirect_dependents("sample_app.utils")
    }

    assert "sample_app.service" in dependent_ids, (
        "sample_app.service must be an indirect dependent of sample_app.utils"
    )
    assert "sample_app.main" in dependent_ids, (
        "sample_app.main must be an indirect dependent of sample_app.utils"
    )


def test_indirect_dependents_excludes_self(graph: DependencyGraph) -> None:
    """The result of find_indirect_dependents must not include the start node."""
    dependent_ids = {
        n.id for n in graph.find_indirect_dependents("sample_app.utils")
    }
    assert "sample_app.utils" not in dependent_ids


def test_indirect_dependents_of_models(graph: DependencyGraph) -> None:
    """models has no dependencies of its own but everything depends on it."""
    dependent_ids = {
        n.id for n in graph.find_indirect_dependents("sample_app.models")
    }

    # utils, service, and main all depend on models (directly or transitively).
    for expected in (
        "sample_app.utils",
        "sample_app.service",
        "sample_app.main",
    ):
        assert expected in dependent_ids, (
            f"{expected} must be an indirect dependent of sample_app.models"
        )
