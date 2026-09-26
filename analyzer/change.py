"""
analyzer.change
~~~~~~~~~~~~~~~

Change Analysis Engine for ImpactOS.

Given a :class:`~analyzer.graph.DependencyGraph` and a set of changed files
or modules, :class:`ChangeAnalyzer` answers:

  "What happens if this code changes?"

It drives the complete developer workflow::

    Code change
        ↓
    Detect changed files/modules
        ↓
    Map changes to dependency graph
        ↓
    Calculate blast radius
        ↓
    Explain affected modules
        ↓
    ChangeImpactReport

Architecture
------------
:class:`ChangeAnalyzer` sits above :class:`~analyzer.impact.ImpactAnalyzer`
in the stack and handles the multi-module aggregation that single-module
analysis cannot express:

    RepoAnalyzer → DependencyGraph → ImpactAnalyzer → ChangeAnalyzer → ChangeImpactReport

Change types
------------
``MODIFIED``  — existing file was changed (default).
``ADDED``     — new file was introduced.
``DELETED``   — file was removed.

Scoring model
-------------
The aggregate impact score is derived from the same formula used in
:mod:`analyzer.impact`, applied to the *union* of affected modules across all
changed modules, so that multi-file change sets are scored consistently.
"""

from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from analyzer.graph import DependencyGraph


# ---------------------------------------------------------------------------
# Change type
# ---------------------------------------------------------------------------


class ChangeType(str, Enum):
    """Classification of how a file changed."""

    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    DELETED = "DELETED"


# ---------------------------------------------------------------------------
# ChangeImpactReport
# ---------------------------------------------------------------------------


@dataclass
class ChangeImpactReport:
    """Structured result of a multi-module change impact analysis.

    Attributes:
        changed_files:             Input file paths (as provided).
        changed_modules:           Dotted module names resolved from the
                                   changed files, sorted.
        change_type:               How the files changed (MODIFIED / ADDED /
                                   DELETED).
        direct_affected_modules:   Modules that **directly** depend on at
                                   least one changed module (one-hop reverse
                                   traversal), sorted.  Does not include
                                   changed modules themselves.
        indirect_affected_modules: Modules that transitively depend on at
                                   least one changed module but are not in
                                   ``direct_affected_modules``, sorted.
        all_affected_modules:      Union of direct and indirect, sorted.
                                   Does not include changed modules.
        affected_count:            ``len(all_affected_modules)``.
        max_depth:                 Longest dependency chain from any changed
                                   module to any affected module.
        impact_score:              Deterministic float in ``[0.0, 1.0]``
                                   (same formula as ImpactAnalyzer).
        risk_level:                One of ``LOW``, ``MEDIUM``, ``HIGH``,
                                   ``CRITICAL``.
        explanations:              Human-readable per-module explanations
                                   grounded in actual graph evidence.
        unknown_modules:           Inputs that could not be resolved to a
                                   graph node.
    """

    changed_files: List[str] = field(default_factory=list)
    changed_modules: List[str] = field(default_factory=list)
    change_type: str = ChangeType.MODIFIED.value
    direct_affected_modules: List[str] = field(default_factory=list)
    indirect_affected_modules: List[str] = field(default_factory=list)
    all_affected_modules: List[str] = field(default_factory=list)
    affected_count: int = 0
    max_depth: int = 0
    impact_score: float = 0.0
    risk_level: str = "LOW"
    explanations: List[str] = field(default_factory=list)
    unknown_modules: List[str] = field(default_factory=list)

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
            "changed_files": self.changed_files,
            "changed_modules": self.changed_modules,
            "change_type": self.change_type,
            "direct_affected_modules": self.direct_affected_modules,
            "indirect_affected_modules": self.indirect_affected_modules,
            "all_affected_modules": self.all_affected_modules,
            "affected_count": self.affected_count,
            "max_depth": self.max_depth,
            "impact_score": round(self.impact_score, 4),
            "risk_level": self.risk_level,
            "explanations": self.explanations,
            "unknown_modules": self.unknown_modules,
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
# ChangeAnalyzer
# ---------------------------------------------------------------------------


class ChangeAnalyzer:
    """Computes change impact reports for a *set* of changed modules.

    Sits on top of the existing :class:`~analyzer.graph.DependencyGraph`
    and reuses its reverse-traversal API to avoid duplicating graph logic.

    Args:
        graph:     A populated :class:`~analyzer.graph.DependencyGraph`,
                   typically produced by
                   :class:`~analyzer.repo_analyzer.RepoAnalyzer`.
        repo_root: Optional root directory used when resolving file paths to
                   module names.  Required if callers pass file paths rather
                   than dotted module names.

    Example::

        from analyzer.repo_analyzer import RepoAnalyzer
        from analyzer.change import ChangeAnalyzer

        graph = RepoAnalyzer("/path/to/project").analyze()
        ca = ChangeAnalyzer(graph, repo_root="/path/to/project")
        report = ca.analyze_changes(["sample_app/utils.py"])
        print(report.to_json())
    """

    def __init__(
        self,
        graph: DependencyGraph,
        repo_root: Optional[str | Path] = None,
    ) -> None:
        self._graph = graph
        self._repo_root: Optional[Path] = (
            Path(repo_root).resolve() if repo_root is not None else None
        )
        self._total_modules: int = sum(
            1 for n in graph.get_nodes() if n.type == "module"
        )
        # Build a lookup: file_path (normalised) → module_id
        self._path_to_module: Dict[str, str] = {}
        for node in graph.get_nodes():
            if node.type == "module" and node.file_path:
                normalised = str(Path(node.file_path).resolve())
                self._path_to_module[normalised] = node.id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_changes(
        self,
        changed_files: List[str],
        change_type: ChangeType | str = ChangeType.MODIFIED,
    ) -> ChangeImpactReport:
        """Produce a :class:`ChangeImpactReport` for a set of changed files.

        Each item in *changed_files* may be:

        * A dotted module name that exists in the graph (e.g.
          ``"sample_app.utils"``).
        * A file path (relative to ``repo_root`` or absolute) that can be
          resolved to a module node (e.g. ``"sample_app/utils.py"``).

        Items that cannot be resolved are collected in
        :attr:`ChangeImpactReport.unknown_modules` and skipped.

        Args:
            changed_files: List of changed file paths or module names.
            change_type:   How the files changed.  Defaults to ``MODIFIED``.

        Returns:
            A fully-populated :class:`ChangeImpactReport` with deduplicated,
            sorted module lists and human-readable explanations.
        """
        if isinstance(change_type, ChangeType):
            change_type_str = change_type.value
        else:
            change_type_str = str(change_type)

        # ---- 1. Resolve inputs to module names ---------------------------
        resolved_modules: List[str] = []
        unknown: List[str] = []
        for item in changed_files:
            mod = self._resolve_to_module(item)
            if mod is None:
                unknown.append(item)
            else:
                resolved_modules.append(mod)

        # Deduplicate while preserving order, then sort for determinism.
        seen: set[str] = set()
        unique_changed: List[str] = []
        for m in resolved_modules:
            if m not in seen:
                seen.add(m)
                unique_changed.append(m)
        changed_modules_sorted = sorted(unique_changed)

        # ---- 2. Gather affected modules from all changed modules ---------
        # Per-changed-module data used for explanations.
        per_module_direct: Dict[str, set[str]] = {}
        per_module_indirect: Dict[str, set[str]] = {}
        per_module_depth: Dict[str, int] = {}

        changed_set = set(changed_modules_sorted)

        for mod in changed_modules_sorted:
            direct_nodes = self._graph.find_direct_dependents(mod)
            all_dep_nodes = self._graph.find_indirect_dependents(mod)

            direct_ids = {n.id for n in direct_nodes} - changed_set
            all_ids = {n.id for n in all_dep_nodes} - changed_set
            indirect_ids = all_ids - direct_ids

            per_module_direct[mod] = direct_ids
            per_module_indirect[mod] = indirect_ids
            per_module_depth[mod] = _compute_max_depth_for_module(mod, self._graph)

        # ---- 3. Union and classify ---------------------------------------
        all_direct: set[str] = set()
        all_indirect_candidates: set[str] = set()
        for mod in changed_modules_sorted:
            all_direct |= per_module_direct[mod]
            all_indirect_candidates |= per_module_indirect[mod]

        # A module is "indirect" only if it is NOT directly affected by
        # any changed module.
        truly_indirect = all_indirect_candidates - all_direct
        # Remove changed modules from affected sets (defensive).
        all_direct -= changed_set
        truly_indirect -= changed_set

        direct_sorted = sorted(all_direct)
        indirect_sorted = sorted(truly_indirect)
        all_affected_sorted = sorted(all_direct | truly_indirect)
        affected_count = len(all_affected_sorted)
        max_depth = max(per_module_depth.values()) if per_module_depth else 0

        # ---- 4. Score and risk -------------------------------------------
        impact_score = _compute_impact_score(
            affected_count=affected_count,
            direct_count=len(direct_sorted),
            max_depth=max_depth,
            total_modules=self._total_modules,
        )
        risk_level = _score_to_risk_level(impact_score)

        # ---- 5. Build explanations ---------------------------------------
        explanations = _build_explanations(
            changed_modules=changed_modules_sorted,
            per_module_direct=per_module_direct,
            per_module_indirect=per_module_indirect,
            all_affected=all_affected_sorted,
            max_depth=max_depth,
            graph=self._graph,
        )

        return ChangeImpactReport(
            changed_files=list(changed_files),
            changed_modules=changed_modules_sorted,
            change_type=change_type_str,
            direct_affected_modules=direct_sorted,
            indirect_affected_modules=indirect_sorted,
            all_affected_modules=all_affected_sorted,
            affected_count=affected_count,
            max_depth=max_depth,
            impact_score=round(impact_score, 4),
            risk_level=risk_level,
            explanations=explanations,
            unknown_modules=sorted(unknown),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_to_module(self, name: str) -> Optional[str]:
        """Resolve *name* (module name or file path) to a graph module ID.

        Strategy:
        1. Exact match against known module node IDs.
        2. Resolve as a file path (absolute or relative to ``repo_root``),
           normalise, and look up in the path-to-module index.

        Args:
            name: A dotted module name or file path string.

        Returns:
            The matching module ID, or ``None`` if unresolvable.
        """
        # Try direct module name lookup first.
        node = self._graph.get_node(name)
        if node is not None and node.type == "module":
            return name

        # Try as a file path.
        candidate = Path(name)
        if not candidate.is_absolute() and self._repo_root is not None:
            candidate = self._repo_root / candidate
        try:
            normalised = str(candidate.resolve())
        except OSError:
            normalised = str(candidate)

        return self._path_to_module.get(normalised)


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


def _compute_max_depth_for_module(target: str, graph: DependencyGraph) -> int:
    """BFS depth of the furthest dependent of *target* in *graph*.

    Args:
        target: Starting module ID.
        graph:  The dependency graph.

    Returns:
        Maximum hop count to the furthest transitive dependent.
    """
    radj = graph._radj  # type: ignore[attr-defined]
    visited: set[str] = {target}
    queue: deque[Tuple[str, int]] = deque(
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
    """Deterministic impact score in ``[0.0, 1.0]`` (same formula as ImpactAnalyzer).

    Args:
        affected_count: Total affected modules.
        direct_count:   Direct dependents.
        max_depth:      Maximum propagation depth.
        total_modules:  Total module nodes in the graph.

    Returns:
        Impact score float.
    """
    if total_modules == 0:
        return 0.0
    coverage = affected_count / total_modules
    directness = direct_count / total_modules
    depth_ratio = min(max_depth / 10.0, 1.0)
    return min(1.0, coverage * 0.5 + directness * 0.3 + depth_ratio * 0.2)


_RISK_THRESHOLDS = [
    (0.75, "CRITICAL"),
    (0.50, "HIGH"),
    (0.25, "MEDIUM"),
    (0.0, "LOW"),
]


def _score_to_risk_level(score: float) -> str:
    """Map an impact score to a risk level string."""
    for threshold, level in _RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return "LOW"


def _build_explanations(
    *,
    changed_modules: List[str],
    per_module_direct: Dict[str, set[str]],
    per_module_indirect: Dict[str, set[str]],
    all_affected: List[str],
    max_depth: int,
    graph: DependencyGraph,
) -> List[str]:
    """Generate human-readable explanations grounded in graph evidence.

    For each changed module, explains which modules directly import it and
    which are indirectly affected (with the path through the dependency chain).

    Args:
        changed_modules:    Sorted list of changed module IDs.
        per_module_direct:  Direct dependents per changed module.
        per_module_indirect: Indirect dependents per changed module.
        all_affected:       All uniquely affected module IDs.
        max_depth:          Maximum propagation depth across all changed modules.
        graph:              The dependency graph (for chain lookups).

    Returns:
        Ordered list of explanation strings.
    """
    explanations: List[str] = []

    if not all_affected:
        if len(changed_modules) == 1:
            explanations.append(
                f"No other modules depend on {changed_modules[0]}."
            )
        else:
            explanations.append(
                "No other modules depend on any of the changed modules."
            )
        return explanations

    # Per changed module — direct
    for mod in changed_modules:
        direct = sorted(per_module_direct[mod])
        for dep in direct:
            short_dep = dep.split(".")[-1]
            short_mod = mod.split(".")[-1]
            explanations.append(
                f"{dep} directly imports the changed module {mod}."
            )

    # Per changed module — indirect (with chain)
    for mod in changed_modules:
        indirect = sorted(per_module_indirect[mod])
        for dep in indirect:
            chain = _find_shortest_chain(dep, mod, graph)
            if chain and len(chain) > 1:
                # chain: dep -> ... -> mod
                chain_str = " -> ".join(chain)
                explanations.append(
                    f"{dep} is indirectly affected through the chain: {chain_str}."
                )
            else:
                explanations.append(
                    f"{dep} is indirectly affected by changes to {mod}."
                )

    # Summary
    unique_count = len(all_affected)
    module_word = "module" if unique_count == 1 else "modules"
    level_word = "level" if max_depth == 1 else "levels"
    explanations.append(
        f"{unique_count} unique {module_word} may be affected "
        f"across {max_depth} dependency {level_word}."
    )

    return explanations


def _find_shortest_chain(
    affected_module: str, changed_module: str, graph: DependencyGraph
) -> List[str]:
    """Find the shortest dependency chain from *affected_module* back to *changed_module*.

    The chain is returned in dependent-first order:
    ``[affected_module, intermediate, ..., changed_module]``.

    Uses BFS over the forward adjacency index so that we trace the path
    ``affected_module → ... → changed_module`` following import edges.

    Args:
        affected_module: The module that is indirectly affected.
        changed_module:  The module that was changed.
        graph:           The dependency graph.

    Returns:
        List of module ID strings representing the path, or an empty list
        if no path is found.
    """
    adj = graph._adj  # type: ignore[attr-defined]
    # BFS: find path from affected_module to changed_module via forward edges.
    queue: deque[List[str]] = deque([[affected_module]])
    visited: set[str] = {affected_module}

    while queue:
        path = queue.popleft()
        current = path[-1]
        for neighbour in adj.get(current, []):
            if neighbour == changed_module:
                return path + [changed_module]
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return []
