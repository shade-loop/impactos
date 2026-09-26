"""
tests.test_change
~~~~~~~~~~~~~~~~~

Comprehensive tests for the ImpactOS Change Analysis Engine (Task 03).

Covers:
    01. Single changed module — direct dependents identified
    02. Single changed module — indirect dependents identified
    03. Multiple changed modules — union of affected modules
    04. Duplicate affected modules are not double-counted
    05. Correct direct vs indirect classification
    06. Correct blast-radius count (affected_count)
    07. Correct maximum depth
    08. Deterministic output — identical calls produce identical results
    09. Explanations are non-empty and grounded in graph evidence
    10. JSON serialisation — to_dict() and to_json()
    11. CLI 'change' human-readable output
    12. CLI 'change' JSON output
    13. Unknown file/module handling
    14. Empty change set handling
    15. File path resolution (relative path to module)
    16. ChangeType enum values
    17. Public API importable from analyzer
    18. Risk level reflects total blast radius
    19. changed_modules excludes unknown inputs
    20. Changed modules not in all_affected_modules
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure the analyzer package is importable
# ---------------------------------------------------------------------------
IMPACTOS_DIR = Path(__file__).parent.parent.resolve()
FIXTURE_REPO_ROOT = IMPACTOS_DIR / "tests" / "fixtures"
FIXTURE_SAMPLE_APP = FIXTURE_REPO_ROOT / "sample_app"

if str(IMPACTOS_DIR) not in sys.path:
    sys.path.insert(0, str(IMPACTOS_DIR))

from analyzer import (  # noqa: E402
    ChangeAnalyzer,
    ChangeImpactReport,
    ChangeType,
    DependencyGraph,
    GraphEdge,
    GraphNode,
    ImpactAnalyzer,
    RepoAnalyzer,
)
from analyzer.cli import main as cli_main  # noqa: E402


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def graph() -> DependencyGraph:
    """Full dependency graph for the fixture repository (session scope)."""
    return RepoAnalyzer(FIXTURE_REPO_ROOT).analyze()


@pytest.fixture(scope="session")
def ca(graph: DependencyGraph) -> ChangeAnalyzer:
    """Shared ChangeAnalyzer with repo_root set (session scope)."""
    return ChangeAnalyzer(graph, repo_root=FIXTURE_REPO_ROOT)


# ---------------------------------------------------------------------------
# Helper — hand-built minimal graph for unit-level tests
# ---------------------------------------------------------------------------
#
# Graph layout (import direction):
#
#   main → service → utils → models
#          service → models
#   main  → models
#
# Reverse (dependents):
#   models  ← utils, service, main
#   utils   ← service
#   service ← main


def _make_fixture_graph() -> DependencyGraph:
    """Return a hand-built graph mirroring the sample_app fixture."""
    g = DependencyGraph()
    for mod in ("sample_app.models", "sample_app.utils",
                "sample_app.service", "sample_app.main"):
        g.add_node(GraphNode(id=mod, type="module", file_path="", symbol_name=mod.split(".")[-1]))
    edges = [
        ("sample_app.utils", "sample_app.models", "imports"),
        ("sample_app.service", "sample_app.utils", "imports"),
        ("sample_app.service", "sample_app.models", "imports"),
        ("sample_app.main", "sample_app.service", "imports"),
        ("sample_app.main", "sample_app.models", "imports"),
    ]
    for src, tgt, rel in edges:
        g.add_edge(GraphEdge(source=src, target=tgt, relationship=rel))
    return g


# ===========================================================================
# Test 01 — Single changed module: direct dependents identified
# ===========================================================================


def test_single_change_direct_dependents(ca: ChangeAnalyzer) -> None:
    """Changing utils must surface service as a direct dependent."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert "sample_app.service" in report.direct_affected_modules, (
        "sample_app.service must be a direct dependent of sample_app.utils"
    )


# ===========================================================================
# Test 02 — Single changed module: indirect dependents identified
# ===========================================================================


def test_single_change_indirect_dependents(ca: ChangeAnalyzer) -> None:
    """Changing utils must surface main as an indirect dependent."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert "sample_app.main" in report.indirect_affected_modules, (
        "sample_app.main must be an indirect dependent of sample_app.utils"
    )
    # main is not a DIRECT dependent of utils
    assert "sample_app.main" not in report.direct_affected_modules


# ===========================================================================
# Test 03 — Multiple changed modules: union of affected modules
# ===========================================================================


def test_multiple_changed_modules_union(ca: ChangeAnalyzer) -> None:
    """Changing utils + models must include all non-changed dependent modules."""
    report = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    # utils affects service (direct), main (indirect)
    # models affects utils, service, main — but utils is a changed module itself
    # so it's excluded from all_affected_modules.
    # Final affected (excluding changed modules): service, main
    affected = set(report.all_affected_modules)
    assert "sample_app.service" in affected
    assert "sample_app.main" in affected
    # utils is changed, so it must NOT appear in the affected set
    assert "sample_app.utils" not in affected
    assert "sample_app.models" not in affected


# ===========================================================================
# Test 04 — No double-counting of affected modules
# ===========================================================================


def test_no_double_counting(ca: ChangeAnalyzer) -> None:
    """The same module must not appear twice in all_affected_modules."""
    report = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    assert len(report.all_affected_modules) == len(set(report.all_affected_modules))


# ===========================================================================
# Test 05 — Correct direct vs indirect classification
# ===========================================================================


def test_direct_indirect_classification(ca: ChangeAnalyzer) -> None:
    """Modules directly importing the changed file must not appear as indirect."""
    report = ca.analyze_changes(["sample_app.utils"])
    # service directly imports utils → direct
    assert "sample_app.service" in report.direct_affected_modules
    assert "sample_app.service" not in report.indirect_affected_modules
    # main only imports service (not utils) → indirect
    assert "sample_app.main" in report.indirect_affected_modules
    assert "sample_app.main" not in report.direct_affected_modules


# ===========================================================================
# Test 06 — Correct blast-radius count
# ===========================================================================


def test_blast_radius_count_single_module(ca: ChangeAnalyzer) -> None:
    """affected_count must equal len(all_affected_modules)."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert report.affected_count == len(report.all_affected_modules)


def test_blast_radius_count_multiple_modules(ca: ChangeAnalyzer) -> None:
    """affected_count stays consistent for a multi-module change."""
    report = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    assert report.affected_count == len(report.all_affected_modules)


def test_blast_radius_utils_is_two(ca: ChangeAnalyzer) -> None:
    """Changing utils should affect exactly 2 modules: service and main."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert report.affected_count == 2, (
        f"Expected 2 affected modules for utils, got {report.affected_count}"
    )


# ===========================================================================
# Test 07 — Correct maximum depth
# ===========================================================================


def test_max_depth_single_module(ca: ChangeAnalyzer) -> None:
    """Changing utils must have max_depth == 2 (service=1, main=2)."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert report.max_depth == 2, (
        f"Expected max_depth 2 for utils, got {report.max_depth}"
    )


def test_max_depth_leaf_module(ca: ChangeAnalyzer) -> None:
    """Changing main (no dependents) must have max_depth == 0."""
    report = ca.analyze_changes(["sample_app.main"])
    assert report.max_depth == 0


def test_max_depth_consistent(ca: ChangeAnalyzer) -> None:
    """max_depth must be the maximum across all changed modules."""
    report_utils = ca.analyze_changes(["sample_app.utils"])
    report_multi = ca.analyze_changes(["sample_app.utils", "sample_app.main"])
    # Adding main (depth 0) should not decrease max_depth below utils's depth
    assert report_multi.max_depth >= report_utils.max_depth


# ===========================================================================
# Test 08 — Deterministic output
# ===========================================================================


def test_deterministic_output(ca: ChangeAnalyzer) -> None:
    """Two identical calls must return identical reports."""
    r1 = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    r2 = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    assert r1.to_dict() == r2.to_dict()


def test_lists_are_sorted(ca: ChangeAnalyzer) -> None:
    """All list fields in the report must be sorted."""
    report = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    assert report.changed_modules == sorted(report.changed_modules)
    assert report.direct_affected_modules == sorted(report.direct_affected_modules)
    assert report.indirect_affected_modules == sorted(report.indirect_affected_modules)
    assert report.all_affected_modules == sorted(report.all_affected_modules)


# ===========================================================================
# Test 09 — Explanations are non-empty and evidence-based
# ===========================================================================


def test_explanations_non_empty_for_impacted_module(ca: ChangeAnalyzer) -> None:
    """Explanations must be non-empty when there are affected modules."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert len(report.explanations) > 0


def test_explanations_mention_direct_dependent(ca: ChangeAnalyzer) -> None:
    """At least one explanation must mention the direct dependent."""
    report = ca.analyze_changes(["sample_app.utils"])
    combined = " ".join(report.explanations)
    assert "sample_app.service" in combined


def test_explanations_mention_indirect_chain(ca: ChangeAnalyzer) -> None:
    """At least one explanation must mention the indirect module."""
    report = ca.analyze_changes(["sample_app.utils"])
    combined = " ".join(report.explanations)
    assert "sample_app.main" in combined


def test_explanations_no_dependents_message(ca: ChangeAnalyzer) -> None:
    """Changing a leaf module must produce a 'no dependents' explanation."""
    report = ca.analyze_changes(["sample_app.main"])
    assert len(report.explanations) == 1
    assert "No other modules" in report.explanations[0] or "no" in report.explanations[0].lower()


def test_explanations_contain_count_summary(ca: ChangeAnalyzer) -> None:
    """Explanations must include a summary mentioning the affected count."""
    report = ca.analyze_changes(["sample_app.utils"])
    combined = " ".join(report.explanations)
    # "2 unique modules may be affected across 2 dependency levels."
    assert "2" in combined


# ===========================================================================
# Test 10 — JSON serialisation
# ===========================================================================


def test_to_dict_has_all_keys(ca: ChangeAnalyzer) -> None:
    """to_dict() must contain all documented keys."""
    report = ca.analyze_changes(["sample_app.utils"])
    d = report.to_dict()
    expected_keys = {
        "changed_files",
        "changed_modules",
        "change_type",
        "direct_affected_modules",
        "indirect_affected_modules",
        "all_affected_modules",
        "affected_count",
        "max_depth",
        "impact_score",
        "risk_level",
        "explanations",
        "unknown_modules",
    }
    assert expected_keys == set(d.keys())


def test_to_dict_types(ca: ChangeAnalyzer) -> None:
    """to_dict() must contain JSON-native types only."""
    report = ca.analyze_changes(["sample_app.utils"])
    d = report.to_dict()
    assert isinstance(d["changed_files"], list)
    assert isinstance(d["changed_modules"], list)
    assert isinstance(d["change_type"], str)
    assert isinstance(d["direct_affected_modules"], list)
    assert isinstance(d["indirect_affected_modules"], list)
    assert isinstance(d["all_affected_modules"], list)
    assert isinstance(d["affected_count"], int)
    assert isinstance(d["max_depth"], int)
    assert isinstance(d["impact_score"], float)
    assert isinstance(d["risk_level"], str)
    assert isinstance(d["explanations"], list)
    assert isinstance(d["unknown_modules"], list)


def test_to_json_valid(ca: ChangeAnalyzer) -> None:
    """to_json() must produce valid, parseable JSON."""
    report = ca.analyze_changes(["sample_app.utils"])
    parsed = json.loads(report.to_json())
    assert isinstance(parsed, dict)


def test_to_json_matches_to_dict(ca: ChangeAnalyzer) -> None:
    """to_json() must round-trip to the same data as to_dict()."""
    report = ca.analyze_changes(["sample_app.models"])
    assert json.loads(report.to_json()) == report.to_dict()


def test_impact_score_bounded(ca: ChangeAnalyzer) -> None:
    """impact_score must always be in [0.0, 1.0]."""
    for mod in ("sample_app.utils", "sample_app.models",
                "sample_app.service", "sample_app.main"):
        report = ca.analyze_changes([mod])
        assert 0.0 <= report.impact_score <= 1.0, (
            f"impact_score out of range for {mod}: {report.impact_score}"
        )


# ===========================================================================
# Test 11 — CLI 'change' human-readable output
# ===========================================================================


def test_cli_change_human_output_contains_key_fields(
    capsys: pytest.CaptureFixture,
) -> None:
    """CLI 'change' must show changed module, risk, score, and affected modules."""
    exit_code = cli_main(
        ["change", str(FIXTURE_REPO_ROOT), "sample_app.utils"]
    )
    captured = capsys.readouterr()
    out = captured.out

    assert exit_code == 0, f"CLI exited with code {exit_code}"
    assert "sample_app.utils" in out
    assert "Risk Level" in out
    assert "Impact Score" in out
    assert "sample_app.service" in out
    assert "sample_app.main" in out
    assert "Blast Radius" in out


def test_cli_change_human_multiple_modules(
    capsys: pytest.CaptureFixture,
) -> None:
    """CLI 'change' must handle multiple changed modules."""
    exit_code = cli_main(
        ["change", str(FIXTURE_REPO_ROOT), "sample_app.utils", "sample_app.models"]
    )
    captured = capsys.readouterr()
    out = captured.out

    assert exit_code == 0, f"CLI exited with code {exit_code}"
    assert "sample_app.utils" in out
    assert "sample_app.models" in out


def test_cli_change_human_why_section(
    capsys: pytest.CaptureFixture,
) -> None:
    """CLI 'change' human output must include a 'Why?' section."""
    cli_main(["change", str(FIXTURE_REPO_ROOT), "sample_app.utils"])
    captured = capsys.readouterr()
    assert "Why?" in captured.out


def test_cli_change_with_type_flag(
    capsys: pytest.CaptureFixture,
) -> None:
    """CLI 'change --type DELETED' must show the correct change type."""
    exit_code = cli_main(
        ["change", str(FIXTURE_REPO_ROOT), "sample_app.utils", "--type", "DELETED"]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "DELETED" in captured.out


def test_cli_change_nonexistent_repo(
    capsys: pytest.CaptureFixture,
) -> None:
    """CLI 'change' must exit with code 1 for a non-existent repo path."""
    exit_code = cli_main(
        ["change", "/this/path/does/not/exist", "sample_app.utils"]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR" in captured.err


# ===========================================================================
# Test 12 — CLI 'change' JSON output
# ===========================================================================


def test_cli_change_json_valid(capsys: pytest.CaptureFixture) -> None:
    """CLI 'change --json' must produce valid, parseable JSON."""
    exit_code = cli_main(
        ["change", str(FIXTURE_REPO_ROOT), "sample_app.utils", "--json"]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    parsed = json.loads(captured.out)
    assert isinstance(parsed, dict)


def test_cli_change_json_all_keys(capsys: pytest.CaptureFixture) -> None:
    """CLI 'change --json' output must contain all ChangeImpactReport keys."""
    cli_main(["change", str(FIXTURE_REPO_ROOT), "sample_app.utils", "--json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    for key in (
        "changed_files", "changed_modules", "change_type",
        "direct_affected_modules", "indirect_affected_modules",
        "all_affected_modules", "affected_count", "max_depth",
        "impact_score", "risk_level", "explanations", "unknown_modules",
    ):
        assert key in parsed, f"Missing key: {key}"


def test_cli_change_json_changed_modules(capsys: pytest.CaptureFixture) -> None:
    """CLI 'change --json' must include the changed module in changed_modules."""
    cli_main(["change", str(FIXTURE_REPO_ROOT), "sample_app.utils", "--json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "sample_app.utils" in parsed["changed_modules"]


def test_cli_change_json_multiple_modules(capsys: pytest.CaptureFixture) -> None:
    """CLI 'change --json' with multiple inputs reports both in changed_modules."""
    cli_main(
        [
            "change", str(FIXTURE_REPO_ROOT),
            "sample_app.utils", "sample_app.models", "--json",
        ]
    )
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "sample_app.utils" in parsed["changed_modules"]
    assert "sample_app.models" in parsed["changed_modules"]


# ===========================================================================
# Test 13 — Unknown file/module handling
# ===========================================================================


def test_unknown_module_does_not_crash(ca: ChangeAnalyzer) -> None:
    """An unknown module name must not raise — it goes to unknown_modules."""
    report = ca.analyze_changes(["sample_app.this_does_not_exist"])
    assert "sample_app.this_does_not_exist" in report.unknown_modules
    assert report.affected_count == 0


def test_unknown_module_mixed_with_known(ca: ChangeAnalyzer) -> None:
    """A mix of known and unknown inputs should analyse the known ones correctly."""
    report = ca.analyze_changes(
        ["sample_app.utils", "sample_app.nonexistent"]
    )
    assert "sample_app.nonexistent" in report.unknown_modules
    assert "sample_app.utils" in report.changed_modules
    assert report.affected_count > 0


def test_unknown_module_not_in_changed_modules(ca: ChangeAnalyzer) -> None:
    """unknown_modules must not appear in changed_modules."""
    report = ca.analyze_changes(
        ["sample_app.utils", "sample_app.ghost"]
    )
    for u in report.unknown_modules:
        assert u not in report.changed_modules


def test_file_path_resolution(graph: DependencyGraph) -> None:
    """A file path relative to repo_root must resolve to the correct module."""
    ca = ChangeAnalyzer(graph, repo_root=FIXTURE_REPO_ROOT)
    # Relative path: sample_app/utils.py
    report = ca.analyze_changes(["sample_app/utils.py"])
    assert "sample_app.utils" in report.changed_modules, (
        f"Expected sample_app.utils in changed_modules, got {report.changed_modules}"
    )
    assert report.affected_count > 0


# ===========================================================================
# Test 14 — Empty change set handling
# ===========================================================================


def test_empty_change_set(ca: ChangeAnalyzer) -> None:
    """An empty change set must produce a zero-impact report without error."""
    report = ca.analyze_changes([])
    assert report.changed_modules == []
    assert report.all_affected_modules == []
    assert report.affected_count == 0
    assert report.impact_score == 0.0
    assert report.max_depth == 0


# ===========================================================================
# Test 15 — ChangeType enum
# ===========================================================================


def test_change_type_values() -> None:
    """ChangeType must have MODIFIED, ADDED, DELETED."""
    assert ChangeType.MODIFIED.value == "MODIFIED"
    assert ChangeType.ADDED.value == "ADDED"
    assert ChangeType.DELETED.value == "DELETED"


def test_change_type_in_report(ca: ChangeAnalyzer) -> None:
    """change_type in the report must reflect the input ChangeType."""
    report = ca.analyze_changes(["sample_app.utils"], change_type=ChangeType.DELETED)
    assert report.change_type == "DELETED"


def test_change_type_string_accepted(ca: ChangeAnalyzer) -> None:
    """analyze_changes must accept a plain string change_type."""
    report = ca.analyze_changes(["sample_app.utils"], change_type="ADDED")
    assert report.change_type == "ADDED"


# ===========================================================================
# Test 16 — changed_modules excluded from affected
# ===========================================================================


def test_changed_modules_not_in_affected(ca: ChangeAnalyzer) -> None:
    """Changed modules themselves must not appear in all_affected_modules."""
    report = ca.analyze_changes(["sample_app.utils"])
    assert "sample_app.utils" not in report.all_affected_modules
    assert "sample_app.utils" not in report.direct_affected_modules
    assert "sample_app.utils" not in report.indirect_affected_modules


def test_multiple_changed_not_in_affected(ca: ChangeAnalyzer) -> None:
    """Multiple changed modules must not appear in affected lists."""
    changed = ["sample_app.utils", "sample_app.models"]
    report = ca.analyze_changes(changed)
    for mod in changed:
        assert mod not in report.all_affected_modules


# ===========================================================================
# Test 17 — Public API importable from analyzer
# ===========================================================================


def test_public_api_imports() -> None:
    """ChangeAnalyzer, ChangeImpactReport, ChangeType must be importable."""
    from analyzer import ChangeAnalyzer, ChangeImpactReport, ChangeType  # noqa: F401
    assert callable(ChangeAnalyzer)
    assert callable(ChangeImpactReport)
    assert hasattr(ChangeType, "MODIFIED")


# ===========================================================================
# Test 18 — Risk level reflects blast radius
# ===========================================================================


def test_risk_level_low_for_leaf(ca: ChangeAnalyzer) -> None:
    """A leaf module with no dependents must have LOW risk."""
    report = ca.analyze_changes(["sample_app.main"])
    assert report.risk_level == "LOW"


def test_risk_level_non_trivial_for_core(ca: ChangeAnalyzer) -> None:
    """A core module (models) with many dependents must have higher risk."""
    report = ca.analyze_changes(["sample_app.models"])
    assert report.risk_level in ("MEDIUM", "HIGH", "CRITICAL"), (
        f"Expected MEDIUM/HIGH/CRITICAL for models, got {report.risk_level}"
    )


# ===========================================================================
# Test 19 — Deduplication of changed_files input
# ===========================================================================


def test_duplicate_inputs_deduped(ca: ChangeAnalyzer) -> None:
    """Passing the same module twice must not inflate changed_modules."""
    report = ca.analyze_changes(["sample_app.utils", "sample_app.utils"])
    assert report.changed_modules.count("sample_app.utils") == 1


# ===========================================================================
# Test 20 — Hand-built graph unit tests (isolated from fixture repo)
# ===========================================================================


def test_unit_direct_dependents_handbuilt() -> None:
    """Unit test on hand-built graph: direct dependents of models."""
    g = _make_fixture_graph()
    ca = ChangeAnalyzer(g)
    report = ca.analyze_changes(["sample_app.models"])
    # utils, service, main all depend on models
    assert "sample_app.utils" in report.all_affected_modules
    assert "sample_app.service" in report.all_affected_modules
    assert "sample_app.main" in report.all_affected_modules


def test_unit_no_dependents_handbuilt() -> None:
    """Unit test: main has no dependents in the hand-built graph."""
    g = _make_fixture_graph()
    ca = ChangeAnalyzer(g)
    report = ca.analyze_changes(["sample_app.main"])
    assert report.affected_count == 0
    assert report.risk_level == "LOW"
