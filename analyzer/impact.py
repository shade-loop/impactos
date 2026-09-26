"""
analyzer.impact
~~~~~~~~~~~~~~~

Change-impact / blast-radius engine for ImpactOS.

Given a :class:`~analyzer.graph.DependencyGraph` built by Task 01 and the
dotted name of a changed module, :class:`ImpactAnalyzer` answers:

  "What could break, how far does the change propagate, and why?"

It does so purely through the reverse-traversal API already implemented in
:class:`~analyzer.graph.DependencyGraph`; no graph logic is duplicated here.

Scoring model
-------------
The **impact score** is a deterministic, evidence-based float in ``[0.0, 1.0]``
computed from three weighted graph signals:

    coverage  = affected_count / total_module_count          (weight 0.50)
    directness = direct_count  / total_module_count          (weight 0.30)
    depth_ratio = min(max_depth / 10, 1.0)                   (weight 0.20)

    impact_score = min(1.0, coverage*0.5 + directness*0.3 + depth_ratio*0.2)

All three signals are derived from actual graph evidence.

Risk levels are thresholded on the impact score:

    CRITICAL  score >= 0.75
    HIGH      score >= 0.50
    MEDIUM    score >= 0.25
    LOW       score <  0.25

The score is intentionally labelled "dependency-based change impact" rather
than a failure-probability prediction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List

from analyzer.graph import DependencyGraph


# ---------------------------------------------------------------------------
# Risk level constants
# ---------------------------------------------------------------------------

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"

# Threshold boundaries (inclusive lower bound).
_RISK_THRESHOLDS = [
    (0.75, RISK_CRITICAL),
    (0.50, RISK_HIGH),
    (0.25, RISK_MEDIUM),
    (0.0, RISK_LOW),
]


# ---------------------------------------------------------------------------
# ImpactReport
# ---------------------------------------------------------------------------


@dataclass
class ImpactReport:
    """Structured result of a single impact analysis.

    Attributes:
        target:              Dotted module name that was analysed.
        direct_dependents:   Modules that *directly* depend on ``target``
                             (one-hop reverse traversal), sorted.
        indirect_dependents: Modules that *transitively* depend on ``target``
                             but are **not** in ``direct_dependents``, sorted.
        affected_modules:    Union of direct and indirect dependents, sorted.
        affected_count:      ``len(affected_modules)``.
        max_depth:           Longest dependency chain from ``target`` to any
                             affected module (BFS level).
        impact_score:        Deterministic float in ``[0.0, 1.0]`` encoding
                             how central this module is to the project.
        risk_level:          One of ``LOW``, ``MEDIUM``, ``HIGH``,
                             ``CRITICAL``.
        reasons:             Human-readable list of explanations for the score.
    """

    target: str
    direct_dependents: List[str] = field(default_factory=list)
    indirect_dependents: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    affected_count: int = 0
    max_depth: int = 0
    impact_score: float = 0.0
    risk_level: str = RISK_LOW
    reasons: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of this report.

        Returns:
            A plain ``dict`` with all attributes at the top level.  All
            values are JSON-native (str, int, float, list).
        """
        return {
            "target": self.target,
            "direct_dependents": self.direct_dependents,
            "indirect_dependents": self.indirect_dependents,
            "affected_modules": self.affected_modules,
            "affected_count": self.affected_count,
            "max_depth": self.max_depth,
            "impact_score": round(self.impact_score, 4),
            "risk_level": self.risk_level,
            "reasons": self.reasons,
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
# ImpactAnalyzer
# ---------------------------------------------------------------------------


class ImpactAnalyzer:
    """Computes change-impact reports for modules in a dependency graph.

    The analyser is a stateless wrapper around an existing
    :class:`~analyzer.graph.DependencyGraph`; it adds no new graph state.

    Args:
        graph: A populated :class:`~analyzer.graph.DependencyGraph`, typically
               produced by :class:`~analyzer.repo_analyzer.RepoAnalyzer`.

    Raises:
        ValueError: If *graph* contains no module nodes (empty analysis).
    """

    def __init__(self, graph: DependencyGraph) -> None:
        self._graph = graph
        # Count only module-type nodes so the score is grounded in modules,
        # not inflated by class/function nodes.
        self._total_modules: int = sum(
            1 for n in graph.get_nodes() if n.type == "module"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, target: str) -> ImpactReport:
        """Produce an :class:`ImpactReport` for a changed *target* module.

        Uses the reverse-traversal methods of :class:`DependencyGraph` to
        find which modules would be affected if *target* changed, then
        computes a deterministic impact score and risk level.

        Args:
            target: Dotted module name of the changed module
                    (e.g. ``"sample_app.utils"``).

        Returns:
            A fully-populated :class:`ImpactReport`.

        Raises:
            ValueError: If *target* is not found in the graph.
        """
        if self._graph.get_node(target) is None:
            raise ValueError(
                f"Module {target!r} not found in the dependency graph. "
                "Ensure the repository has been analysed and the module "
                "name is correct."
            )

        # ------------------------------------------------------------------
        # 1. Blast-radius traversal via the existing DependencyGraph API.
        # ------------------------------------------------------------------
        direct_nodes = self._graph.find_direct_dependents(target)
        all_dependent_nodes = self._graph.find_indirect_dependents(target)

        direct_ids: set[str] = {n.id for n in direct_nodes}
        # Indirect = reachable transitively but NOT via a single hop.
        indirect_ids: set[str] = {
            n.id for n in all_dependent_nodes if n.id not in direct_ids
        }

        direct_sorted = sorted(direct_ids)
        indirect_sorted = sorted(indirect_ids)
        affected_sorted = sorted(direct_ids | indirect_ids)
        affected_count = len(affected_sorted)

        # ------------------------------------------------------------------
        # 2. Maximum dependency depth (BFS level of the furthest dependent).
        # ------------------------------------------------------------------
        max_depth = _compute_max_depth(target, self._graph)

        # ------------------------------------------------------------------
        # 3. Impact score (deterministic, bounded [0.0, 1.0]).
        # ------------------------------------------------------------------
        impact_score = _compute_impact_score(
            affected_count=affected_count,
            direct_count=len(direct_sorted),
            max_depth=max_depth,
            total_modules=self._total_modules,
        )

        # ------------------------------------------------------------------
        # 4. Risk level from score thresholds.
        # ------------------------------------------------------------------
        risk_level = _score_to_risk_level(impact_score)

        # ------------------------------------------------------------------
        # 5. Human-readable reasons.
        # ------------------------------------------------------------------
        reasons = _build_reasons(
            target=target,
            direct_count=len(direct_sorted),
            indirect_count=len(indirect_sorted),
            affected_count=affected_count,
            max_depth=max_depth,
            impact_score=impact_score,
            risk_level=risk_level,
        )

        return ImpactReport(
            target=target,
            direct_dependents=direct_sorted,
            indirect_dependents=indirect_sorted,
            affected_modules=affected_sorted,
            affected_count=affected_count,
            max_depth=max_depth,
            impact_score=round(impact_score, 4),
            risk_level=risk_level,
            reasons=reasons,
        )


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


def _compute_max_depth(target: str, graph: DependencyGraph) -> int:
    """Return the maximum BFS depth of the reverse dependents graph.

    A depth of 0 means no dependents; depth 1 means there is at least one
    direct dependent; depth 2 means at least one indirect dependent, etc.

    Args:
        target: Starting node ID.
        graph:  The dependency graph.

    Returns:
        Maximum number of hops to the furthest dependent module.
    """
    from collections import deque

    radj = graph._radj  # type: ignore[attr-defined]  # accessing internal index
    visited: set[str] = {target}
    queue: deque[tuple[str, int]] = deque(
        (nbr, 1) for nbr in radj.get(target, [])
    )
    max_depth = 0

    while queue:
        node_id, depth = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        if depth > max_depth:
            max_depth = depth
        for nbr in radj.get(node_id, []):
            if nbr not in visited:
                queue.append((nbr, depth + 1))

    return max_depth


def _compute_impact_score(
    affected_count: int,
    direct_count: int,
    max_depth: int,
    total_modules: int,
) -> float:
    """Compute a deterministic impact score in ``[0.0, 1.0]``.

    Formula
    -------
    ::

        coverage    = affected_count / total_modules      (weight 0.50)
        directness  = direct_count   / total_modules      (weight 0.30)
        depth_ratio = min(max_depth  / 10, 1.0)           (weight 0.20)

        score = min(1.0, coverage*0.5 + directness*0.3 + depth_ratio*0.2)

    All three terms are bounded, so the sum is always in ``[0.0, 1.0]``.

    Args:
        affected_count: Total number of affected modules.
        direct_count:   Number of direct dependents.
        max_depth:      Maximum propagation depth.
        total_modules:  Total module nodes in the graph.

    Returns:
        Impact score as a float in ``[0.0, 1.0]``.
    """
    if total_modules == 0:
        return 0.0
    coverage = affected_count / total_modules
    directness = direct_count / total_modules
    depth_ratio = min(max_depth / 10.0, 1.0)
    score = coverage * 0.5 + directness * 0.3 + depth_ratio * 0.2
    return min(1.0, score)


def _score_to_risk_level(score: float) -> str:
    """Map an impact score to a risk level string.

    Thresholds (inclusive lower bound)::

        CRITICAL  score >= 0.75
        HIGH      score >= 0.50
        MEDIUM    score >= 0.25
        LOW       score <  0.25

    Args:
        score: Impact score in ``[0.0, 1.0]``.

    Returns:
        One of ``"LOW"``, ``"MEDIUM"``, ``"HIGH"``, ``"CRITICAL"``.
    """
    for threshold, level in _RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return RISK_LOW


def _build_reasons(
    *,
    target: str,
    direct_count: int,
    indirect_count: int,
    affected_count: int,
    max_depth: int,
    impact_score: float,
    risk_level: str,
) -> list[str]:
    """Build a human-readable list of reasons explaining the impact score.

    Each reason is a concrete statement grounded in graph evidence.

    Args:
        target:         Target module name.
        direct_count:   Number of direct dependents.
        indirect_count: Number of indirect dependents.
        affected_count: Total affected modules.
        max_depth:      Maximum propagation depth.
        impact_score:   Computed impact score.
        risk_level:     Derived risk level.

    Returns:
        List of reason strings.
    """
    reasons: list[str] = []

    if affected_count == 0:
        reasons.append("No other modules depend on this module")
        return reasons

    # Affected modules
    module_word = "module" if affected_count == 1 else "modules"
    reasons.append(f"{affected_count} {module_word} depend on this module")

    # Direct dependents
    if direct_count > 0:
        d_word = "module directly imports" if direct_count == 1 else "modules directly import"
        reasons.append(f"{direct_count} {d_word} this module")

    # Indirect dependents
    if indirect_count > 0:
        i_word = "module is" if indirect_count == 1 else "modules are"
        reasons.append(f"{indirect_count} {i_word} indirectly affected")

    # Depth
    if max_depth > 1:
        reasons.append(
            f"Change propagates through {max_depth} dependency levels"
        )
    elif max_depth == 1:
        reasons.append("Change propagates through 1 dependency level")

    return reasons
