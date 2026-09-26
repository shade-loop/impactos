"""
tests.test_impact
~~~~~~~~~~~~~~~~~

Unit and integration tests for the ImpactOS impact analysis engine (Task 02).

Covers:
    01. Module with no dependents → LOW risk / zero impact score
    02. Module with direct dependents only
    03. Module with both direct and indirect dependents
    04. Correct blast-radius (affected_modules) content and count
    05. Correct maximum dependency depth
    06. Deterministic impact score — two identical calls yield identical results
    07. Correct risk-level boundaries via _score_to_risk_level helper
    08. to_dict() serialization — all keys, JSON-native types
    09. to_json() produces valid JSON matching to_dict()
    10. CLI human-readable output — key fields present
    11. CLI JSON output — valid, parseable, target matches
    12. CLI error on unknown target
    13. CLI error on non-existent repo path
    14. ImpactAnalyzer.analyze raises ValueError for unknown module
    15. ImpactReport for sample_app.models (high-impact core module)
    16. Public API — ImpactAnalyzer and ImpactReport importable from analyzer
    17. impact_score bounded to [0.0, 1.0]
    18. affected_modules is a sorted, deduplicated list
    19. Reasons list is non-empty for impacted module
    20. Reasons list states "no dependents" for leaf module
"""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Ensure the analyzer package is importable
# ---------------------------------------------------------------------------
IMPACTOS_DIR = Path(__file__).parent.parent.resolve()
FIXTURE_REPO_ROOT = IMPACTOS_DIR / "tests" / "fixtures"

if str(IMPACTOS_DIR) not in sys.path:
    sys.path.insert(0, str(IMPACTOS_DIR))

from analyzer import (  # noqa: E402
    DependencyGraph,
    GraphEdge,
    GraphNode,
    ImpactAnalyzer,
    ImpactReport,
    RepoAnalyzer,
)
from analyzer.impact import (  # noqa: E402
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    _compute_impact_score,
    _compute_max_depth,
    _score_to_risk_level,
)
from analyzer.cli import main as cli_main  # noqa: E402


# ---------------------------------------------------------------------------
# Shared session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def graph() -> DependencyGraph:
    """Full dependency graph for the fixture repository (session scope)."""
    return RepoAnalyzer(FIXTURE_REPO_ROOT).analyze()


@pytest.fixture(scope="session")
def ia(graph: DependencyGraph) -> ImpactAnalyzer:
    """Shared ImpactAnalyzer instance (session scope)."""
    return ImpactAnalyzer(graph)


# ---------------------------------------------------------------------------
# Helper — tiny hand-built graph for unit tests that need precise control
# ---------------------------------------------------------------------------


def _make_linear_graph() -> DependencyGraph:
    """Return a minimal three-module linear graph: A → B → C.

    Import direction (forward): A imports B, B imports C.
    Reverse direction (dependents): C is depended on by B, B by A.
    """
    g = DependencyGraph()
    for name in ("pkg.a", "pkg.b", "pkg.c"):
        g.add_node(GraphNode(id=name, type="module", file_path="", symbol_name=name.split(".")[-1]))
    g.add_edge(GraphEdge(source="pkg.a", target="pkg.b", relationship="imports"))
    g.add_edge(GraphEdge(source="pkg.b", target="pkg.c", relationship="imports"))
    return g


def _make_star_graph() -> DependencyGraph:
    """Return a star graph where four modules all import a central module 'hub'.

    hub is the only node with no dependencies (root).
    spoke1, spoke2, spoke3, spoke4 all import hub.
    """
    g = DependencyGraph()
    names = ["pkg.hub", "pkg.spoke1", "pkg.spoke2", "pkg.spoke3", "pkg.spoke4"]
    for name in names:
        g.add_node(GraphNode(id=name, type="module", file_path="", symbol_name=name.split(".")[-1]))
    for spoke in ("pkg.spoke1", "pkg.spoke2", "pkg.spoke3", "pkg.spoke4"):
        g.add_edge(GraphEdge(source=spoke, target="pkg.hub", relationship="imports"))
    return g


# ===========================================================================
# Test 01 — Module with no dependents → LOW risk, zero impact score
# ===========================================================================


def test_no_dependents_low_risk(ia: ImpactAnalyzer) -> None:
    """sample_app.main has no dependents → affected_count=0 and LOW risk."""
    report = ia.analyze("sample_app.main")

    assert report.affected_count == 0, "main has no dependents"
    assert report.direct_dependents == [], "main has no direct dependents"
    assert report.indirect_dependents == [], "main has no indirect dependents"
    assert report.affected_modules == [], "main has no affected modules"
    assert report.risk_level == RISK_LOW, f"Expected LOW, got {report.risk_level}"
    assert report.impact_score == 0.0, f"Expected 0.0, got {report.impact_score}"


# ===========================================================================
# Test 02 — Module with only direct dependents
# ===========================================================================


def test_direct_dependents_only() -> None:
    """pkg.c in a linear graph A→B→C has only B as a direct dependent."""
    g = _make_linear_graph()
    ia = ImpactAnalyzer(g)
    report = ia.analyze("pkg.c")

    assert "pkg.b" in report.direct_dependents
    # pkg.a is indirectly affected (b→a in reverse)
    assert "pkg.a" in report.indirect_dependents
    assert report.affected_count == 2


def test_leaf_dependents_no_indirect() -> None:
    """pkg.a (the importer, with nothing importing it) has no dependents at all."""
    g = _make_linear_graph()
    ia = ImpactAnalyzer(g)
    report = ia.analyze("pkg.a")

    assert report.direct_dependents == []
    assert report.indirect_dependents == []
    assert report.affected_count == 0
    assert report.risk_level == RISK_LOW


# ===========================================================================
# Test 03 — Module with both direct and indirect dependents
# ===========================================================================


def test_utils_has_direct_and_indirect_dependents(ia: ImpactAnalyzer) -> None:
    """sample_app.utils: service is direct, main is indirect."""
    report = ia.analyze("sample_app.utils")

    assert "sample_app.service" in report.direct_dependents, (
        "service must be a direct dependent of utils"
    )
    assert "sample_app.main" in report.indirect_dependents, (
        "main must be an indirect dependent of utils (via service)"
    )
    assert "sample_app.service" not in report.indirect_dependents, (
        "service must NOT appear in indirect_dependents"
    )
    assert "sample_app.main" not in report.direct_dependents, (
        "main must NOT appear in direct_dependents"
    )


# ===========================================================================
# Test 04 — Correct blast-radius count and content
# ===========================================================================


def test_blast_radius_count_utils(ia: ImpactAnalyzer) -> None:
    """Blast radius of utils = 2 (service + main)."""
    report = ia.analyze("sample_app.utils")
    assert report.affected_count == 2
    assert set(report.affected_modules) == {"sample_app.service", "sample_app.main"}


def test_blast_radius_count_models(ia: ImpactAnalyzer) -> None:
    """Blast radius of models = 3 (utils + service + main)."""
    report = ia.analyze("sample_app.models")
    assert report.affected_count == 3
    assert set(report.affected_modules) == {
        "sample_app.utils",
        "sample_app.service",
        "sample_app.main",
    }


def test_blast_radius_no_duplicates(ia: ImpactAnalyzer) -> None:
    """affected_modules must not contain duplicates."""
    report = ia.analyze("sample_app.models")
    assert len(report.affected_modules) == len(set(report.affected_modules))


# ===========================================================================
# Test 05 — Correct maximum dependency depth
# ===========================================================================


def test_max_depth_utils(ia: ImpactAnalyzer) -> None:
    """utils blast radius spans 2 hops: utils→service(1)→main(2)."""
    report = ia.analyze("sample_app.utils")
    assert report.max_depth == 2, f"Expected depth 2, got {report.max_depth}"


def test_max_depth_models(ia: ImpactAnalyzer) -> None:
    """models direct-imports span 1 hop (all direct); max_depth == 1."""
    report = ia.analyze("sample_app.models")
    assert report.max_depth == 1, f"Expected depth 1, got {report.max_depth}"


def test_max_depth_no_dependents(ia: ImpactAnalyzer) -> None:
    """A module with no dependents must have max_depth == 0."""
    report = ia.analyze("sample_app.main")
    assert report.max_depth == 0


def test_max_depth_linear_graph() -> None:
    """In A→B→C, C has max_depth 2 (B at 1, A at 2)."""
    g = _make_linear_graph()
    assert _compute_max_depth("pkg.c", g) == 2


# ===========================================================================
# Test 06 — Deterministic impact score
# ===========================================================================


def test_impact_score_is_deterministic(ia: ImpactAnalyzer) -> None:
    """Calling analyze() twice on the same target must yield the same score."""
    r1 = ia.analyze("sample_app.utils")
    r2 = ia.analyze("sample_app.utils")
    assert r1.impact_score == r2.impact_score
    assert r1.risk_level == r2.risk_level


def test_impact_score_formula() -> None:
    """_compute_impact_score must return the expected value for known inputs."""
    # affected=2, direct=1, max_depth=2, total=5
    # coverage=0.4, directness=0.2, depth_ratio=0.2
    # score = 0.4*0.5 + 0.2*0.3 + 0.2*0.2 = 0.20 + 0.06 + 0.04 = 0.30
    score = _compute_impact_score(
        affected_count=2,
        direct_count=1,
        max_depth=2,
        total_modules=5,
    )
    assert abs(score - 0.30) < 1e-9, f"Expected 0.30, got {score}"


def test_impact_score_bounded() -> None:
    """_compute_impact_score must always return a value in [0.0, 1.0]."""
    for affected, direct, depth, total in [
        (0, 0, 0, 1),
        (1, 1, 1, 1),
        (100, 100, 100, 1),
        (5, 5, 10, 5),
    ]:
        score = _compute_impact_score(affected, direct, depth, total)
        assert 0.0 <= score <= 1.0, f"Score {score} out of bounds"


def test_impact_score_zero_modules() -> None:
    """_compute_impact_score must return 0.0 when total_modules is 0."""
    score = _compute_impact_score(0, 0, 0, 0)
    assert score == 0.0


# ===========================================================================
# Test 07 — Risk level boundaries
# ===========================================================================


def test_risk_level_boundaries() -> None:
    """_score_to_risk_level must map scores to the correct risk buckets."""
    assert _score_to_risk_level(0.0) == RISK_LOW
    assert _score_to_risk_level(0.24) == RISK_LOW
    assert _score_to_risk_level(0.25) == RISK_MEDIUM
    assert _score_to_risk_level(0.49) == RISK_MEDIUM
    assert _score_to_risk_level(0.50) == RISK_HIGH
    assert _score_to_risk_level(0.74) == RISK_HIGH
    assert _score_to_risk_level(0.75) == RISK_CRITICAL
    assert _score_to_risk_level(1.0) == RISK_CRITICAL


def test_utils_risk_level_is_medium(ia: ImpactAnalyzer) -> None:
    """sample_app.utils must be MEDIUM risk in the sample_app fixture."""
    report = ia.analyze("sample_app.utils")
    assert report.risk_level == RISK_MEDIUM, (
        f"Expected MEDIUM for utils, got {report.risk_level}"
    )


def test_models_risk_level_is_high_or_critical(ia: ImpactAnalyzer) -> None:
    """sample_app.models (depended on by 3 modules) must be HIGH or CRITICAL risk."""
    report = ia.analyze("sample_app.models")
    assert report.risk_level in (RISK_HIGH, RISK_CRITICAL), (
        f"Expected HIGH or CRITICAL for models, got {report.risk_level}"
    )


# ===========================================================================
# Test 08 — to_dict() serialization
# ===========================================================================


def test_to_dict_keys(ia: ImpactAnalyzer) -> None:
    """to_dict() must contain all expected top-level keys."""
    report = ia.analyze("sample_app.utils")
    d = report.to_dict()
    expected_keys = {
        "target",
        "direct_dependents",
        "indirect_dependents",
        "affected_modules",
        "affected_count",
        "max_depth",
        "impact_score",
        "risk_level",
        "reasons",
    }
    assert expected_keys == set(d.keys()), f"Keys mismatch: {set(d.keys())}"


def test_to_dict_types(ia: ImpactAnalyzer) -> None:
    """to_dict() must return only JSON-native types."""
    report = ia.analyze("sample_app.utils")
    d = report.to_dict()
    assert isinstance(d["target"], str)
    assert isinstance(d["direct_dependents"], list)
    assert isinstance(d["indirect_dependents"], list)
    assert isinstance(d["affected_modules"], list)
    assert isinstance(d["affected_count"], int)
    assert isinstance(d["max_depth"], int)
    assert isinstance(d["impact_score"], float)
    assert isinstance(d["risk_level"], str)
    assert isinstance(d["reasons"], list)


def test_to_dict_values_match_report(ia: ImpactAnalyzer) -> None:
    """to_dict() values must be consistent with the ImpactReport attributes."""
    report = ia.analyze("sample_app.utils")
    d = report.to_dict()
    assert d["target"] == report.target
    assert d["direct_dependents"] == report.direct_dependents
    assert d["indirect_dependents"] == report.indirect_dependents
    assert d["affected_modules"] == report.affected_modules
    assert d["affected_count"] == report.affected_count
    assert d["max_depth"] == report.max_depth
    assert d["risk_level"] == report.risk_level


# ===========================================================================
# Test 09 — to_json() produces valid JSON matching to_dict()
# ===========================================================================


def test_to_json_valid(ia: ImpactAnalyzer) -> None:
    """to_json() must return a valid, parseable JSON string."""
    report = ia.analyze("sample_app.utils")
    json_str = report.to_json()
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


def test_to_json_matches_to_dict(ia: ImpactAnalyzer) -> None:
    """Parsed to_json() must equal to_dict()."""
    report = ia.analyze("sample_app.utils")
    assert json.loads(report.to_json()) == report.to_dict()


# ===========================================================================
# Test 10 — CLI human-readable output
# ===========================================================================


def test_cli_human_output_contains_key_fields(capsys: pytest.CaptureFixture) -> None:
    """CLI human output must include target, risk level, score, and dependents."""
    exit_code = cli_main([str(FIXTURE_REPO_ROOT), "sample_app.utils"])
    captured = capsys.readouterr()
    out = captured.out

    assert exit_code == 0, f"CLI exited with code {exit_code}"
    assert "sample_app.utils" in out
    assert "MEDIUM" in out or "HIGH" in out or "LOW" in out or "CRITICAL" in out
    assert "sample_app.service" in out
    assert "sample_app.main" in out
    assert "Impact Score" in out
    assert "Risk Level" in out


def test_cli_human_output_zero_impact(capsys: pytest.CaptureFixture) -> None:
    """CLI human output for main (no dependents) must show zero impact."""
    exit_code = cli_main([str(FIXTURE_REPO_ROOT), "sample_app.main"])
    captured = capsys.readouterr()
    out = captured.out

    assert exit_code == 0
    assert "sample_app.main" in out
    assert "LOW" in out


# ===========================================================================
# Test 11 — CLI JSON output
# ===========================================================================


def test_cli_json_output_valid(capsys: pytest.CaptureFixture) -> None:
    """CLI --json output must be valid, parseable JSON."""
    exit_code = cli_main([str(FIXTURE_REPO_ROOT), "sample_app.utils", "--json"])
    captured = capsys.readouterr()
    out = captured.out

    assert exit_code == 0, f"CLI exited with {exit_code}"
    parsed = json.loads(out)
    assert isinstance(parsed, dict)


def test_cli_json_output_target_matches(capsys: pytest.CaptureFixture) -> None:
    """CLI --json output must contain the correct target field."""
    cli_main([str(FIXTURE_REPO_ROOT), "sample_app.utils", "--json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["target"] == "sample_app.utils"


def test_cli_json_output_all_keys(capsys: pytest.CaptureFixture) -> None:
    """CLI --json output must contain all ImpactReport keys."""
    cli_main([str(FIXTURE_REPO_ROOT), "sample_app.models", "--json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    for key in (
        "target", "direct_dependents", "indirect_dependents",
        "affected_modules", "affected_count", "max_depth",
        "impact_score", "risk_level", "reasons",
    ):
        assert key in parsed, f"Missing key: {key}"


# ===========================================================================
# Test 12 — CLI error on unknown target
# ===========================================================================


def test_cli_error_unknown_target(capsys: pytest.CaptureFixture) -> None:
    """CLI must exit with code 1 for an unknown target module."""
    exit_code = cli_main([str(FIXTURE_REPO_ROOT), "sample_app.nonexistent"])
    captured = capsys.readouterr()

    assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
    assert "ERROR" in captured.err or "not found" in captured.err.lower()


# ===========================================================================
# Test 13 — CLI error on non-existent repo path
# ===========================================================================


def test_cli_error_nonexistent_repo(capsys: pytest.CaptureFixture) -> None:
    """CLI must exit with code 1 when the repo path does not exist."""
    exit_code = cli_main(["/this/path/does/not/exist", "sample_app.utils"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "ERROR" in captured.err


# ===========================================================================
# Test 14 — ImpactAnalyzer.analyze raises ValueError for unknown module
# ===========================================================================


def test_analyze_raises_for_unknown_module(ia: ImpactAnalyzer) -> None:
    """analyze() must raise ValueError when target is not in the graph."""
    with pytest.raises(ValueError, match="not found"):
        ia.analyze("this.does.not.exist")


# ===========================================================================
# Test 15 — sample_app.models is correctly identified as a core module
# ===========================================================================


def test_models_is_core_module(ia: ImpactAnalyzer) -> None:
    """models is a high-impact core: 3 modules depend on it directly."""
    report = ia.analyze("sample_app.models")

    # All three non-root modules depend on models
    assert "sample_app.utils" in report.affected_modules
    assert "sample_app.service" in report.affected_modules
    assert "sample_app.main" in report.affected_modules
    assert report.affected_count == 3
    assert report.impact_score >= 0.5, (
        f"models should have score >= 0.5, got {report.impact_score}"
    )


def test_models_direct_dependents_all_three(ia: ImpactAnalyzer) -> None:
    """models is directly imported by utils, service, and main."""
    report = ia.analyze("sample_app.models")
    # All three directly import models
    for mod in ("sample_app.utils", "sample_app.service", "sample_app.main"):
        assert mod in report.direct_dependents, (
            f"{mod} must be a direct dependent of models"
        )


# ===========================================================================
# Test 16 — Public API: ImpactAnalyzer and ImpactReport importable from analyzer
# ===========================================================================


def test_public_api_imports() -> None:
    """ImpactAnalyzer and ImpactReport must be importable from the top-level analyzer package."""
    import analyzer  # noqa: PLC0415
    assert hasattr(analyzer, "ImpactAnalyzer")
    assert hasattr(analyzer, "ImpactReport")


# ===========================================================================
# Test 17 — impact_score is always bounded to [0.0, 1.0]
# ===========================================================================


def test_impact_score_always_bounded(graph: DependencyGraph) -> None:
    """impact_score for every module node must be in [0.0, 1.0]."""
    ia = ImpactAnalyzer(graph)
    for node in graph.get_nodes():
        if node.type == "module":
            report = ia.analyze(node.id)
            assert 0.0 <= report.impact_score <= 1.0, (
                f"Score out of bounds for {node.id}: {report.impact_score}"
            )


# ===========================================================================
# Test 18 — affected_modules is sorted and deduplicated
# ===========================================================================


def test_affected_modules_sorted(ia: ImpactAnalyzer) -> None:
    """affected_modules must be in sorted (alphabetical) order."""
    report = ia.analyze("sample_app.models")
    assert report.affected_modules == sorted(report.affected_modules)


def test_direct_dependents_sorted(ia: ImpactAnalyzer) -> None:
    """direct_dependents must be in sorted order."""
    report = ia.analyze("sample_app.models")
    assert report.direct_dependents == sorted(report.direct_dependents)


def test_indirect_dependents_sorted(ia: ImpactAnalyzer) -> None:
    """indirect_dependents must be in sorted order."""
    report = ia.analyze("sample_app.utils")
    assert report.indirect_dependents == sorted(report.indirect_dependents)


# ===========================================================================
# Test 19 — Reasons are non-empty for an impacted module
# ===========================================================================


def test_reasons_non_empty_for_impacted_module(ia: ImpactAnalyzer) -> None:
    """An impacted module must have at least one reason."""
    report = ia.analyze("sample_app.utils")
    assert len(report.reasons) > 0, "Expected at least one reason for utils"


def test_reasons_contain_affected_count(ia: ImpactAnalyzer) -> None:
    """Reasons must mention the number of affected modules."""
    report = ia.analyze("sample_app.utils")
    combined = " ".join(report.reasons)
    assert "2" in combined, "Reasons should mention '2' affected modules"


# ===========================================================================
# Test 20 — Reasons for a leaf module state no dependents
# ===========================================================================


def test_reasons_no_dependents_message(ia: ImpactAnalyzer) -> None:
    """Reasons for sample_app.main must state that no modules depend on it."""
    report = ia.analyze("sample_app.main")
    combined = " ".join(report.reasons).lower()
    assert "no" in combined and "depend" in combined, (
        f"Expected 'no ... depend ...' in reasons, got: {report.reasons}"
    )
