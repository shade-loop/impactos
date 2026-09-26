"""
tests.test_risk
~~~~~~~~~~~~~~~

Comprehensive tests for the ImpactOS Risk & Action Recommendation Engine
(Task 04).

Covers:
    01. LOW risk assessment (isolated module)
    02. MEDIUM risk assessment (sample_app.utils — 2 affected)
    03. HIGH risk assessment (sample_app.models — more affected)
    04. Existing impact score is preserved from ChangeImpactReport
    05. Evidence is generated correctly
    06. Direct dependent gets HIGH test priority
    07. Indirect dependent gets MEDIUM test priority
    08. Direct dependent gets HIGH review priority
    09. Indirect dependent gets MEDIUM review priority
    10. Recommendations are deduplicated (module affected by 2 changed modules)
    11. Multiple changed modules
    12. Deterministic recommendation ordering
    13. to_dict() structure and types
    14. to_json() is valid JSON matching to_dict()
    15. CLI human-readable output (review command)
    16. CLI JSON output (review command --json)
    17. Unknown target handling (empty change set)
    18. Empty change handling (no affected modules → LOW, no recommendations)
    19. Public API importable from analyzer
    20. RiskAssessment preserves risk_level from report
    21. Evidence empty-impact case
    22. Recommendation.to_dict() structure
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
    RepoAnalyzer,
    RiskAnalyzer,
    RiskAssessment,
    Recommendation,
)
from analyzer.cli import main as cli_main  # noqa: E402
from analyzer.risk import (  # noqa: E402
    CATEGORY_REVIEW,
    CATEGORY_TEST,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def graph():
    """Build the dependency graph for sample_app once per test module."""
    return RepoAnalyzer(FIXTURE_REPO_ROOT).analyze()


@pytest.fixture(scope="module")
def ca(graph):
    """ChangeAnalyzer for sample_app."""
    return ChangeAnalyzer(graph, repo_root=FIXTURE_REPO_ROOT)


def make_empty_report() -> ChangeImpactReport:
    """Return a ChangeImpactReport with no affected modules."""
    return ChangeImpactReport(
        changed_files=["sample_app/models.py"],
        changed_modules=["sample_app.models"],
        change_type="MODIFIED",
        direct_affected_modules=[],
        indirect_affected_modules=[],
        all_affected_modules=[],
        affected_count=0,
        max_depth=0,
        impact_score=0.0,
        risk_level="LOW",
        explanations=[],
        unknown_modules=[],
    )


def make_medium_report() -> ChangeImpactReport:
    """Synthetic MEDIUM-risk report: 1 direct + 1 indirect affected module."""
    return ChangeImpactReport(
        changed_files=["sample_app/utils.py"],
        changed_modules=["sample_app.utils"],
        change_type="MODIFIED",
        direct_affected_modules=["sample_app.service"],
        indirect_affected_modules=["sample_app.main"],
        all_affected_modules=["sample_app.main", "sample_app.service"],
        affected_count=2,
        max_depth=2,
        impact_score=0.3,
        risk_level="MEDIUM",
        explanations=[],
        unknown_modules=[],
    )


def make_high_report() -> ChangeImpactReport:
    """Synthetic HIGH-risk report: 3 direct + 2 indirect."""
    return ChangeImpactReport(
        changed_files=["sample_app/core.py"],
        changed_modules=["sample_app.core"],
        change_type="MODIFIED",
        direct_affected_modules=["a", "b", "c"],
        indirect_affected_modules=["d", "e"],
        all_affected_modules=["a", "b", "c", "d", "e"],
        affected_count=5,
        max_depth=3,
        impact_score=0.55,
        risk_level="HIGH",
        explanations=[],
        unknown_modules=[],
    )


# ---------------------------------------------------------------------------
# 01. LOW risk assessment
# ---------------------------------------------------------------------------


def test_01_low_risk_assessment():
    """RiskAssessment for an isolated module has LOW risk and no recommendations."""
    report = make_empty_report()
    assessment = RiskAnalyzer(report).assess()

    assert assessment.risk_level == "LOW"
    assert assessment.affected_count == 0
    assert assessment.direct_count == 0
    assert assessment.indirect_count == 0
    assert assessment.recommendations == []


# ---------------------------------------------------------------------------
# 02. MEDIUM risk assessment
# ---------------------------------------------------------------------------


def test_02_medium_risk_assessment():
    """RiskAssessment for sample_app.utils is MEDIUM (1 direct + 1 indirect)."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    assert assessment.risk_level == "MEDIUM"
    assert assessment.affected_count == 2
    assert assessment.direct_count == 1
    assert assessment.indirect_count == 1


# ---------------------------------------------------------------------------
# 03. HIGH risk assessment
# ---------------------------------------------------------------------------


def test_03_high_risk_assessment():
    """RiskAssessment reflects HIGH risk when impact_score >= 0.50."""
    report = make_high_report()
    assessment = RiskAnalyzer(report).assess()

    assert assessment.risk_level == "HIGH"
    assert assessment.affected_count == 5


# ---------------------------------------------------------------------------
# 04. Impact score preserved
# ---------------------------------------------------------------------------


def test_04_impact_score_preserved():
    """Impact score from ChangeImpactReport is carried into RiskAssessment unchanged."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    assert assessment.impact_score == pytest.approx(0.3, abs=1e-9)


def test_04b_impact_score_preserved_high():
    """Impact score preserved for HIGH-risk report."""
    report = make_high_report()
    assessment = RiskAnalyzer(report).assess()

    assert assessment.impact_score == pytest.approx(0.55, abs=1e-9)


# ---------------------------------------------------------------------------
# 05. Evidence generation
# ---------------------------------------------------------------------------


def test_05_evidence_nonempty_for_affected():
    """Evidence list is non-empty when at least one module is affected."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    assert len(assessment.evidence) > 0


def test_05b_evidence_contains_affected_count():
    """Evidence mentions the number of affected modules."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    joined = " ".join(assessment.evidence)
    assert "2" in joined  # 2 modules are affected


def test_05c_evidence_mentions_direct_and_indirect():
    """Evidence mentions direct and indirect dependents."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    joined = " ".join(assessment.evidence)
    assert "direct" in joined.lower()
    assert "indirect" in joined.lower()


def test_05d_evidence_mentions_depth():
    """Evidence mentions propagation depth when depth > 0."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    joined = " ".join(assessment.evidence)
    assert "depth" in joined.lower() or "2" in joined


def test_05e_evidence_empty_impact():
    """Evidence for zero-impact change contains a 'no affected' statement."""
    report = make_empty_report()
    assessment = RiskAnalyzer(report).assess()

    assert len(assessment.evidence) == 1
    assert "no" in assessment.evidence[0].lower() or "0" in assessment.evidence[0]


# ---------------------------------------------------------------------------
# 06. Direct dependent gets HIGH test priority
# ---------------------------------------------------------------------------


def test_06_direct_dependent_high_test_priority():
    """Direct dependent gets a TEST recommendation with HIGH priority."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    test_recs = [r for r in assessment.recommendations if r.category == CATEGORY_TEST]
    high_test = [r for r in test_recs if r.priority == PRIORITY_HIGH]

    assert any(r.module == "sample_app.service" for r in high_test)


# ---------------------------------------------------------------------------
# 07. Indirect dependent gets MEDIUM test priority
# ---------------------------------------------------------------------------


def test_07_indirect_dependent_medium_test_priority():
    """Indirect dependent gets a TEST recommendation with MEDIUM priority."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    test_recs = [r for r in assessment.recommendations if r.category == CATEGORY_TEST]
    medium_test = [r for r in test_recs if r.priority == PRIORITY_MEDIUM]

    assert any(r.module == "sample_app.main" for r in medium_test)


# ---------------------------------------------------------------------------
# 08. Direct dependent gets HIGH review priority
# ---------------------------------------------------------------------------


def test_08_direct_dependent_high_review_priority():
    """Direct dependent gets a REVIEW recommendation with HIGH priority."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    review_recs = [r for r in assessment.recommendations if r.category == CATEGORY_REVIEW]
    high_review = [r for r in review_recs if r.priority == PRIORITY_HIGH]

    assert any(r.module == "sample_app.service" for r in high_review)


# ---------------------------------------------------------------------------
# 09. Indirect dependent gets MEDIUM review priority
# ---------------------------------------------------------------------------


def test_09_indirect_dependent_medium_review_priority():
    """Indirect dependent gets a REVIEW recommendation with MEDIUM priority."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    review_recs = [r for r in assessment.recommendations if r.category == CATEGORY_REVIEW]
    medium_review = [r for r in review_recs if r.priority == PRIORITY_MEDIUM]

    assert any(r.module == "sample_app.main" for r in medium_review)


# ---------------------------------------------------------------------------
# 10. Recommendations are deduplicated
# ---------------------------------------------------------------------------


def test_10_recommendations_deduplicated():
    """A module affected by two changed modules gets only one recommendation per category."""
    # Both changed_a and changed_b affect "shared_module" directly.
    report = ChangeImpactReport(
        changed_files=["a.py", "b.py"],
        changed_modules=["pkg.a", "pkg.b"],
        change_type="MODIFIED",
        direct_affected_modules=["pkg.shared"],
        indirect_affected_modules=[],
        all_affected_modules=["pkg.shared"],
        affected_count=1,
        max_depth=1,
        impact_score=0.2,
        risk_level="LOW",
        explanations=[],
        unknown_modules=[],
    )
    assessment = RiskAnalyzer(report).assess()

    test_for_shared = [
        r for r in assessment.recommendations
        if r.category == CATEGORY_TEST and r.module == "pkg.shared"
    ]
    review_for_shared = [
        r for r in assessment.recommendations
        if r.category == CATEGORY_REVIEW and r.module == "pkg.shared"
    ]

    assert len(test_for_shared) == 1
    assert len(review_for_shared) == 1


# ---------------------------------------------------------------------------
# 11. Multiple changed modules
# ---------------------------------------------------------------------------


def test_11_multiple_changed_modules(ca):
    """RiskAnalyzer handles a ChangeImpactReport from multiple changed modules."""
    change_report = ca.analyze_changes(["sample_app.utils", "sample_app.models"])
    assessment = RiskAnalyzer(change_report).assess()

    assert isinstance(assessment, RiskAssessment)
    assert assessment.affected_count >= 0
    # Both changed modules should not appear in recommendations
    changed_set = set(change_report.changed_modules)
    for rec in assessment.recommendations:
        assert rec.module not in changed_set


# ---------------------------------------------------------------------------
# 12. Deterministic recommendation ordering
# ---------------------------------------------------------------------------


def test_12_deterministic_ordering():
    """Calling assess() twice on the same report produces identical recommendation order."""
    report = make_medium_report()
    a1 = RiskAnalyzer(report).assess()
    a2 = RiskAnalyzer(report).assess()

    mods1 = [(r.category, r.module, r.priority) for r in a1.recommendations]
    mods2 = [(r.category, r.module, r.priority) for r in a2.recommendations]
    assert mods1 == mods2


def test_12b_ordering_review_before_test_or_consistent():
    """Recommendations are sorted by category then priority then module — deterministic."""
    report = make_high_report()
    assessment = RiskAnalyzer(report).assess()

    _rank = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
    keys = [(r.category, _rank[r.priority], r.module) for r in assessment.recommendations]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# 13. to_dict()
# ---------------------------------------------------------------------------


def test_13_to_dict_structure():
    """to_dict() returns a dict with all expected top-level keys."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()
    d = assessment.to_dict()

    for key in ("risk_level", "impact_score", "affected_count", "direct_count",
                "indirect_count", "max_depth", "evidence", "recommendations"):
        assert key in d, f"Missing key: {key}"


def test_13b_to_dict_types():
    """to_dict() values have correct types."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()
    d = assessment.to_dict()

    assert isinstance(d["risk_level"], str)
    assert isinstance(d["impact_score"], float)
    assert isinstance(d["affected_count"], int)
    assert isinstance(d["direct_count"], int)
    assert isinstance(d["indirect_count"], int)
    assert isinstance(d["max_depth"], int)
    assert isinstance(d["evidence"], list)
    assert isinstance(d["recommendations"], list)


def test_13c_to_dict_recommendations_structure():
    """Each recommendation dict has category, module, priority, action, reason."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()
    d = assessment.to_dict()

    for rec in d["recommendations"]:
        for key in ("category", "module", "priority", "action", "reason"):
            assert key in rec, f"Recommendation missing key: {key}"
        assert rec["category"] in (CATEGORY_TEST, CATEGORY_REVIEW)
        assert rec["priority"] in (PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW)


# ---------------------------------------------------------------------------
# 14. to_json()
# ---------------------------------------------------------------------------


def test_14_to_json_is_valid():
    """to_json() returns valid JSON."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()
    raw = assessment.to_json()

    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


def test_14b_to_json_matches_to_dict():
    """to_json() content matches to_dict()."""
    report = make_medium_report()
    assessment = RiskAnalyzer(report).assess()

    assert json.loads(assessment.to_json()) == assessment.to_dict()


# ---------------------------------------------------------------------------
# 15. CLI human-readable output
# ---------------------------------------------------------------------------


def test_15_cli_review_human(capsys):
    """CLI 'review' command produces human-readable output with expected sections."""
    exit_code = cli_main([
        "review",
        str(FIXTURE_REPO_ROOT),
        "sample_app.utils",
    ])
    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert "ImpactOS" in output
    assert "Change Risk Review" in output
    assert "sample_app.utils" in output
    assert "Risk Level" in output
    assert "Impact Score" in output


def test_15b_cli_review_human_shows_recommendations(capsys):
    """CLI 'review' human output shows recommendations when modules are affected."""
    exit_code = cli_main([
        "review",
        str(FIXTURE_REPO_ROOT),
        "sample_app.utils",
    ])
    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    # sample_app.service directly depends on utils
    assert "sample_app.service" in output


# ---------------------------------------------------------------------------
# 16. CLI JSON output
# ---------------------------------------------------------------------------


def test_16_cli_review_json(capsys):
    """CLI 'review --json' command produces valid JSON with expected keys."""
    exit_code = cli_main([
        "review",
        str(FIXTURE_REPO_ROOT),
        "sample_app.utils",
        "--json",
    ])
    captured = capsys.readouterr()

    assert exit_code == 0
    parsed = json.loads(captured.out)
    for key in ("risk_level", "impact_score", "affected_count",
                "direct_count", "indirect_count", "max_depth",
                "evidence", "recommendations"):
        assert key in parsed, f"Missing JSON key: {key}"


def test_16b_cli_review_json_recommendations(capsys):
    """CLI --json output includes recommendations list."""
    exit_code = cli_main([
        "review",
        str(FIXTURE_REPO_ROOT),
        "sample_app.utils",
        "--json",
    ])
    captured = capsys.readouterr()

    assert exit_code == 0
    parsed = json.loads(captured.out)
    assert isinstance(parsed["recommendations"], list)
    assert len(parsed["recommendations"]) > 0


# ---------------------------------------------------------------------------
# 17. Unknown target handling
# ---------------------------------------------------------------------------


def test_17_unknown_target_handled(capsys):
    """Passing an unknown module name results in a graceful empty assessment."""
    # The ChangeAnalyzer puts unknown modules in unknown_modules and produces
    # an empty ChangeImpactReport — the RiskAnalyzer should handle it cleanly.
    exit_code = cli_main([
        "review",
        str(FIXTURE_REPO_ROOT),
        "nonexistent.module.xyz",
    ])
    # Should exit 0 (graceful) and emit output
    assert exit_code == 0
    captured = capsys.readouterr()
    assert len(captured.out) > 0


def test_17b_unknown_module_zero_affected():
    """Unknown module produces an assessment with zero affected modules."""
    report = ChangeImpactReport(
        changed_files=["nonexistent.py"],
        changed_modules=[],
        change_type="MODIFIED",
        direct_affected_modules=[],
        indirect_affected_modules=[],
        all_affected_modules=[],
        affected_count=0,
        max_depth=0,
        impact_score=0.0,
        risk_level="LOW",
        explanations=[],
        unknown_modules=["nonexistent.py"],
    )
    assessment = RiskAnalyzer(report).assess()

    assert assessment.affected_count == 0
    assert assessment.recommendations == []


# ---------------------------------------------------------------------------
# 18. Empty change handling
# ---------------------------------------------------------------------------


def test_18_empty_change_no_recommendations():
    """A report with no changed modules and no affected modules has no recommendations."""
    report = ChangeImpactReport(
        changed_files=[],
        changed_modules=[],
        change_type="MODIFIED",
        direct_affected_modules=[],
        indirect_affected_modules=[],
        all_affected_modules=[],
        affected_count=0,
        max_depth=0,
        impact_score=0.0,
        risk_level="LOW",
        explanations=[],
        unknown_modules=[],
    )
    assessment = RiskAnalyzer(report).assess()

    assert assessment.risk_level == "LOW"
    assert assessment.recommendations == []


# ---------------------------------------------------------------------------
# 19. Public API importable from analyzer
# ---------------------------------------------------------------------------


def test_19_public_api_importable():
    """RiskAnalyzer, RiskAssessment, Recommendation are importable from analyzer."""
    from analyzer import RiskAnalyzer as RA, RiskAssessment as RS, Recommendation as R  # noqa: F401
    assert RA is RiskAnalyzer
    assert RS is RiskAssessment
    assert R is Recommendation


# ---------------------------------------------------------------------------
# 20. RiskAssessment preserves risk_level from report
# ---------------------------------------------------------------------------


def test_20_risk_level_preserved():
    """RiskAssessment.risk_level exactly matches the ChangeImpactReport.risk_level."""
    for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        report = ChangeImpactReport(
            changed_files=["x.py"],
            changed_modules=["x"],
            change_type="MODIFIED",
            direct_affected_modules=["y"] if level != "LOW" else [],
            indirect_affected_modules=[],
            all_affected_modules=["y"] if level != "LOW" else [],
            affected_count=1 if level != "LOW" else 0,
            max_depth=1 if level != "LOW" else 0,
            impact_score=0.0,
            risk_level=level,
            explanations=[],
            unknown_modules=[],
        )
        assessment = RiskAnalyzer(report).assess()
        assert assessment.risk_level == level


# ---------------------------------------------------------------------------
# 21. Recommendation.to_dict() structure
# ---------------------------------------------------------------------------


def test_21_recommendation_to_dict():
    """Recommendation.to_dict() returns a plain dict with all five keys."""
    rec = Recommendation(
        category=CATEGORY_TEST,
        module="pkg.foo",
        priority=PRIORITY_HIGH,
        action="Run or update tests for this module",
        reason="Directly depends on changed module.",
    )
    d = rec.to_dict()

    assert d == {
        "category": "TEST",
        "module": "pkg.foo",
        "priority": "HIGH",
        "action": "Run or update tests for this module",
        "reason": "Directly depends on changed module.",
    }


# ---------------------------------------------------------------------------
# 22. Integration: real graph → ChangeAnalyzer → RiskAnalyzer
# ---------------------------------------------------------------------------


def test_22_integration_sample_app_utils(ca):
    """Full integration: sample_app.utils change produces correct assessment."""
    change_report = ca.analyze_changes(["sample_app.utils"])
    assessment = RiskAnalyzer(change_report).assess()

    # sample_app.service directly imports sample_app.utils
    direct_mods = [
        r.module for r in assessment.recommendations
        if r.category == CATEGORY_TEST and r.priority == PRIORITY_HIGH
    ]
    assert "sample_app.service" in direct_mods

    # sample_app.main indirectly depends through sample_app.service
    indirect_mods = [
        r.module for r in assessment.recommendations
        if r.category == CATEGORY_TEST and r.priority == PRIORITY_MEDIUM
    ]
    assert "sample_app.main" in indirect_mods

    # Sanity: assessment serialises cleanly
    d = assessment.to_dict()
    assert json.loads(assessment.to_json()) == d
