"""
analyzer
~~~~~~~~

ImpactOS repository analysis engine.

Provides tools to walk a Python repository, extract symbols via AST parsing,
build an in-memory directed dependency graph, and perform dependency-based
change-impact analysis.

Public API
----------
::

    from analyzer import RepoAnalyzer, DependencyGraph, GraphNode, GraphEdge
    from analyzer import ParsedModule, parse_file
    from analyzer import ImpactAnalyzer, ImpactReport
    from analyzer import ChangeAnalyzer, ChangeImpactReport, ChangeType

    # Task 01 — build the dependency graph
    graph = RepoAnalyzer("/path/to/repo").analyze()

    # Task 02 — analyse the blast radius of a change
    ia = ImpactAnalyzer(graph)
    report = ia.analyze("mypackage.utils")
    print(report.to_json())

    # Task 03 — change impact for a set of changed files
    ca = ChangeAnalyzer(graph, repo_root="/path/to/repo")
    cr = ca.analyze_changes(["mypackage/utils.py", "mypackage/models.py"])
    print(cr.to_json())
"""

from __future__ import annotations

from analyzer.change import ChangeAnalyzer, ChangeImpactReport, ChangeType
from analyzer.graph import DependencyGraph, GraphEdge, GraphNode
from analyzer.impact import ImpactAnalyzer, ImpactReport
from analyzer.parser import ParsedModule, parse_file
from analyzer.repo_analyzer import RepoAnalyzer

__all__ = [
    # Task 01
    "DependencyGraph",
    "GraphEdge",
    "GraphNode",
    "ParsedModule",
    "RepoAnalyzer",
    "parse_file",
    # Task 02
    "ImpactAnalyzer",
    "ImpactReport",
    # Task 03
    "ChangeAnalyzer",
    "ChangeImpactReport",
    "ChangeType",
]
