<<<<<<< HEAD
def assess_risk(impact_result: dict) -> dict:
    """Augment impact_result with risk_level, impact_score, evidence, and recommendations."""
    affected_count: int = impact_result.get("affected_count", 0)
    direct_count: int = impact_result.get("direct_count", 0)
    indirect_count: int = impact_result.get("indirect_count", 0)
    max_depth: int = impact_result.get("max_depth", 0)
    changed_modules: list[str] = impact_result.get("changed_modules", [])
    direct_affected: list[str] = impact_result.get("direct_affected", [])

    # Risk level
    if affected_count == 0:
        risk_level = "LOW"
    elif affected_count <= 2 and max_depth <= 2:
        risk_level = "MEDIUM"
    elif affected_count <= 5:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # Impact score (clamped to [0.0, 1.0])
    # Weights: 1 direct + 1 indirect + depth 2 = 0.3 (matches spec)
    impact_score = min(
        1.0,
        direct_count * 0.2 + indirect_count * 0.05 + max_depth * 0.025,
    )

    # Evidence bullets
    evidence: list[str] = []
    for mod in changed_modules:
        evidence.append(f"Module {mod} is changed")
    evidence.append(
        f"{direct_count} module(s) directly depend on the changed code"
    )
    if indirect_count:
        evidence.append(f"{indirect_count} modules are indirectly affected")
    if max_depth:
        evidence.append(
            f"Change propagates {max_depth} level(s) deep through the dependency tree"
        )

    # Recommendations
    recommendations: list[str] = []
    for mod in direct_affected:
        recommendations.append(
            f"REVIEW: {mod} directly depends on changed code — review for breaking changes"
        )
    if direct_count:
        recommendations.append(
            f"TEST: Run tests for all {direct_count} directly affected module(s)"
        )
    for mod in impact_result.get("indirect_affected", []):
        recommendations.append(
            f"TEST: Verify {mod} still works end-to-end"
        )

    impact_result["risk_level"] = risk_level
    impact_result["impact_score"] = round(impact_score, 4)
    impact_result["evidence"] = evidence
    impact_result["recommendations"] = recommendations

    return impact_result
=======
"""
analyzer.risk
~~~~~~~~~~~~~

Risk & Action Recommendation Engine for ImpactOS (Task 04).

Given a :class:`~analyzer.change.ChangeImpactReport` produced by Task 03,
:class:`RiskAnalyzer` answers:

  "How significant is this dependency-based impact, and what should the
   developer validate/review?"

The assessment is deterministic, explainable, and based entirely on evidence
already present in the ChangeImpactReport — no machine learning, no external
APIs, no invented information.

Scoring model
-------------
The risk level and impact score are taken **directly** from the
:class:`~analyzer.change.ChangeImpactReport`; no second scoring system is
introduced.

Recommendation categories and priorities
-----------------------------------------
* **TEST** — run or update tests for the affected module.
* **REVIEW** — inspect the affected module for breaking changes.

Priority mapping:

  * Direct dependents  → HIGH
  * Indirect dependents → MEDIUM
  * No impact          → LOW (reflected in the assessment; no recommendations)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Set

from analyzer.change import ChangeImpactReport


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_TEST = "TEST"
CATEGORY_REVIEW = "REVIEW"

PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


@dataclass
class Recommendation:
    """A single actionable recommendation for the developer.

    Attributes:
        category: ``"TEST"`` or ``"REVIEW"``.
        module:   Dotted name of the affected module.
        priority: ``"HIGH"``, ``"MEDIUM"``, or ``"LOW"``.
        action:   Short imperative sentence describing what to do.
        reason:   Evidence-based explanation of *why* this is recommended.
    """

    category: str
    module: str
    priority: str
    action: str
    reason: str

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict of this recommendation.

        Returns:
            Plain dict with string values.
        """
        return {
            "category": self.category,
            "module": self.module,
            "priority": self.priority,
            "action": self.action,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# RiskAssessment
# ---------------------------------------------------------------------------


@dataclass
class RiskAssessment:
    """Structured result of a risk analysis derived from a ChangeImpactReport.

    Attributes:
        risk_level:     One of ``LOW``, ``MEDIUM``, ``HIGH``, ``CRITICAL``.
        impact_score:   Dependency-based change impact score in ``[0.0, 1.0]``.
                        Taken directly from the ChangeImpactReport; this is
                        *dependency-based change risk*, not a failure-probability
                        prediction.
        affected_count: Total number of affected modules.
        direct_count:   Number of directly affected modules.
        indirect_count: Number of indirectly affected modules.
        max_depth:      Maximum dependency chain depth.
        evidence:       Human-readable list of evidence statements explaining
                        the assessment.
        recommendations: Ordered list of :class:`Recommendation` objects,
                         deduplicated, sorted deterministically.
    """

    risk_level: str
    impact_score: float
    affected_count: int
    direct_count: int
    indirect_count: int
    max_depth: int
    evidence: List[str] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict of this assessment.

        The structure is designed to be frontend/API-friendly.

        Returns:
            Plain dict with JSON-native values.
        """
        return {
            "risk_level": self.risk_level,
            "impact_score": round(self.impact_score, 4),
            "affected_count": self.affected_count,
            "direct_count": self.direct_count,
            "indirect_count": self.indirect_count,
            "max_depth": self.max_depth,
            "evidence": self.evidence,
            "recommendations": [r.to_dict() for r in self.recommendations],
        }

    def to_json(self, indent: int = 2) -> str:
        """Return a pretty-printed JSON string of :meth:`to_dict`.

        Args:
            indent: Number of spaces for JSON indentation (default 2).

        Returns:
            Formatted JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# RiskAnalyzer
# ---------------------------------------------------------------------------


class RiskAnalyzer:
    """Converts a :class:`~analyzer.change.ChangeImpactReport` into an
    actionable :class:`RiskAssessment`.

    The analyser reuses all scoring information already present in the
    ChangeImpactReport — it does not duplicate graph traversal logic or
    introduce a second scoring system.

    Args:
        report: A :class:`~analyzer.change.ChangeImpactReport` produced by
                :class:`~analyzer.change.ChangeAnalyzer`.

    Example::

        from analyzer.repo_analyzer import RepoAnalyzer
        from analyzer.change import ChangeAnalyzer
        from analyzer.risk import RiskAnalyzer

        graph = RepoAnalyzer("/path/to/project").analyze()
        ca = ChangeAnalyzer(graph, repo_root="/path/to/project")
        change_report = ca.analyze_changes(["sample_app/utils.py"])
        risk = RiskAnalyzer(change_report).assess()
        print(risk.to_json())
    """

    def __init__(self, report: ChangeImpactReport) -> None:
        self._report = report

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(self) -> RiskAssessment:
        """Produce a :class:`RiskAssessment` from the stored ChangeImpactReport.

        Returns:
            A fully-populated :class:`RiskAssessment` with deduplicated,
            deterministically-ordered evidence and recommendations.
        """
        report = self._report

        direct_count = len(report.direct_affected_modules)
        indirect_count = len(report.indirect_affected_modules)

        evidence = _build_evidence(
            affected_count=report.affected_count,
            direct_count=direct_count,
            indirect_count=indirect_count,
            max_depth=report.max_depth,
        )

        recommendations = _build_recommendations(
            changed_modules=report.changed_modules,
            direct_affected=report.direct_affected_modules,
            indirect_affected=report.indirect_affected_modules,
        )

        return RiskAssessment(
            risk_level=report.risk_level,
            impact_score=report.impact_score,
            affected_count=report.affected_count,
            direct_count=direct_count,
            indirect_count=indirect_count,
            max_depth=report.max_depth,
            evidence=evidence,
            recommendations=recommendations,
        )


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


def _build_evidence(
    *,
    affected_count: int,
    direct_count: int,
    indirect_count: int,
    max_depth: int,
) -> List[str]:
    """Build a list of evidence statements from graph-derived numbers.

    Each statement is a concrete, grounded claim about the dependency impact.

    Args:
        affected_count: Total affected modules.
        direct_count:   Direct dependents.
        indirect_count: Indirect dependents.
        max_depth:      Maximum propagation depth.

    Returns:
        Ordered list of evidence strings.
    """
    evidence: List[str] = []

    if affected_count == 0:
        evidence.append("No other modules are affected by this change")
        return evidence

    module_word = "module" if affected_count == 1 else "modules"
    evidence.append(f"{affected_count} {module_word} are affected")

    direct_word = "direct dependent exists" if direct_count == 1 else "direct dependents exist"
    evidence.append(f"{direct_count} {direct_word}")

    indirect_word = "indirect dependent exists" if indirect_count == 1 else "indirect dependents exist"
    evidence.append(f"{indirect_count} {indirect_word}")

    if max_depth > 0:
        evidence.append(f"Propagation reaches depth {max_depth}")

    return evidence


def _build_recommendations(
    *,
    changed_modules: List[str],
    direct_affected: List[str],
    indirect_affected: List[str],
) -> List[Recommendation]:
    """Build deduplicated, deterministically-ordered recommendations.

    For each directly affected module a HIGH TEST and HIGH REVIEW recommendation
    are generated.  For each indirectly affected module a MEDIUM TEST and MEDIUM
    REVIEW recommendation are generated.  If a module appears in both lists
    (which the ChangeAnalyzer already prevents, but is handled defensively),
    only the higher-priority recommendation is kept.

    Recommendations are deduplicated by ``(category, module)`` key — if a
    module is affected by multiple changed modules, a single recommendation
    is produced whose reason references all relevant changed modules.

    Args:
        changed_modules:  Sorted list of changed module IDs.
        direct_affected:  Sorted list of directly affected modules.
        indirect_affected: Sorted list of indirectly affected modules.

    Returns:
        List of :class:`Recommendation` objects sorted by
        ``(category, priority_rank, module)`` for determinism.
    """
    # priority ordering for deduplication — lower number = higher priority
    _priority_rank: Dict[str, int] = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}

    # Build a set for fast lookup (indirect → to find intermediates in reasons)
    direct_set: Set[str] = set(direct_affected)

    # (category, module) → Recommendation (keep highest priority)
    rec_map: Dict[tuple, Recommendation] = {}

    def _upsert(rec: Recommendation) -> None:
        key = (rec.category, rec.module)
        existing = rec_map.get(key)
        if existing is None:
            rec_map[key] = rec
        elif _priority_rank[rec.priority] < _priority_rank[existing.priority]:
            rec_map[key] = rec

    # --- Direct dependents ------------------------------------------------
    for mod in direct_affected:
        # Determine which changed modules this module directly depends on.
        # Since ChangeAnalyzer already computed this, we describe it
        # generically but accurately.
        if len(changed_modules) == 1:
            reason_test = (
                f"Directly depends on the changed module {changed_modules[0]}."
            )
            reason_review = (
                f"Directly depends on the changed module {changed_modules[0]}."
            )
        else:
            reason_test = (
                f"Directly depends on one or more of the changed modules: "
                f"{', '.join(changed_modules)}."
            )
            reason_review = reason_test

        _upsert(Recommendation(
            category=CATEGORY_TEST,
            module=mod,
            priority=PRIORITY_HIGH,
            action="Run or update tests for this module",
            reason=reason_test,
        ))
        _upsert(Recommendation(
            category=CATEGORY_REVIEW,
            module=mod,
            priority=PRIORITY_HIGH,
            action="Review this module for breaking changes",
            reason=reason_review,
        ))

    # --- Indirect dependents ----------------------------------------------
    for mod in indirect_affected:
        # Find the shortest intermediate path description.
        # The ChangeImpactReport's direct_affected_modules tells us which
        # modules sit between mod and the changed module(s).
        intermediates = sorted(direct_set)
        if intermediates:
            via = intermediates[0]
            reason_test = (
                f"Indirectly affected through {via}."
            )
            reason_review = (
                f"Downstream affected module; dependency chain passes through {via}."
            )
        else:
            reason_test = "Indirectly affected by the changed module(s)."
            reason_review = "Downstream affected module."

        _upsert(Recommendation(
            category=CATEGORY_TEST,
            module=mod,
            priority=PRIORITY_MEDIUM,
            action="Run or update tests for this module",
            reason=reason_test,
        ))
        _upsert(Recommendation(
            category=CATEGORY_REVIEW,
            module=mod,
            priority=PRIORITY_MEDIUM,
            action="Review this module for downstream effects",
            reason=reason_review,
        ))

    # --- Sort deterministically: category, then priority rank, then module
    sorted_recs = sorted(
        rec_map.values(),
        key=lambda r: (r.category, _priority_rank[r.priority], r.module),
    )
    return sorted_recs
>>>>>>> origin/main
