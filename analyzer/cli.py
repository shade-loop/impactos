"""
analyzer.cli
~~~~~~~~~~~~

Lightweight command-line interface for ImpactOS.

Supports three commands:

``impact`` (default / Task 02)
    Analyse the blast radius of a single changed module.

``change`` (Task 03)
    Full change-impact analysis across one or more changed files / modules,
    with explainable output and optional JSON serialisation.

``review`` (Task 04)
    Risk & action recommendation report for one or more changed modules.

Usage
-----
::

    # Task 02 — single module impact (human-readable)
    python -m analyzer.cli impact <repo_path> <target_module>

    # Task 02 — single module impact (JSON)
    python -m analyzer.cli impact <repo_path> <target_module> --json

    # Task 03 — change impact across multiple modules (human-readable)
    python -m analyzer.cli change <repo_path> <module_or_file> [<module_or_file> ...] [--type MODIFIED|ADDED|DELETED] [--json]

    # Task 04 — risk & recommendation review (human-readable)
    python -m analyzer.cli review <repo_path> <module_or_file> [<module_or_file> ...]

    # Task 04 — risk & recommendation review (JSON)
    python -m analyzer.cli review <repo_path> <module_or_file> [<module_or_file> ...] --json

Examples::

    python -m analyzer.cli impact tests/fixtures sample_app.utils
    python -m analyzer.cli impact tests/fixtures sample_app.models --json

    python -m analyzer.cli change tests/fixtures sample_app.utils
    python -m analyzer.cli change tests/fixtures sample_app.utils sample_app.models
    python -m analyzer.cli change tests/fixtures sample_app.utils --json

    python -m analyzer.cli review tests/fixtures/sample_app sample_app.utils
    python -m analyzer.cli review tests/fixtures/sample_app sample_app.utils --json

Exit codes
----------
0  — analysis completed successfully
1  — bad arguments or analysis error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="analyzer.cli",
        description=(
            "ImpactOS — dependency-based change impact analyser.\n\n"
            "Commands:\n"
            "  impact  Analyse the blast radius of a single changed module.\n"
            "  change  Full change-impact analysis across one or more changed files.\n"
            "  review  Risk & action recommendation report (Task 04).\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    # ------------------------------------------------------------------ impact
    impact_parser = subparsers.add_parser(
        "impact",
        help="Analyse the blast radius of a single changed module (Task 02).",
        description=(
            "Analyse a Python repository and report the blast radius of "
            "changing a specific module."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    impact_parser.add_argument(
        "repo_path",
        metavar="REPO_PATH",
        help="Root directory of the Python repository to analyse.",
    )
    impact_parser.add_argument(
        "target",
        metavar="TARGET_MODULE",
        help="Dotted module name of the changed module (e.g. 'sample_app.utils').",
    )
    impact_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Print the ImpactReport as machine-readable JSON.",
    )

    # ------------------------------------------------------------------ change
    change_parser = subparsers.add_parser(
        "change",
        help="Full change-impact analysis across one or more changed files (Task 03).",
        description=(
            "Analyse a Python repository and report the combined blast radius "
            "of changing one or more modules, with explainable output."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    change_parser.add_argument(
        "repo_path",
        metavar="REPO_PATH",
        help="Root directory of the Python repository to analyse.",
    )
    change_parser.add_argument(
        "changed",
        metavar="MODULE_OR_FILE",
        nargs="+",
        help=(
            "One or more changed dotted module names or file paths "
            "(e.g. 'sample_app.utils' or 'sample_app/utils.py')."
        ),
    )
    change_parser.add_argument(
        "--type",
        dest="change_type",
        metavar="CHANGE_TYPE",
        default="MODIFIED",
        choices=["MODIFIED", "ADDED", "DELETED"],
        help="Change type: MODIFIED (default), ADDED, or DELETED.",
    )
    change_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Print the ChangeImpactReport as machine-readable JSON.",
    )

    # ------------------------------------------------------------------ review
    review_parser = subparsers.add_parser(
        "review",
        help="Risk & action recommendation report for changed modules (Task 04).",
        description=(
            "Analyse a Python repository, compute change impact, and produce "
            "a risk assessment with actionable TEST and REVIEW recommendations."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    review_parser.add_argument(
        "repo_path",
        metavar="REPO_PATH",
        help="Root directory of the Python repository to analyse.",
    )
    review_parser.add_argument(
        "changed",
        metavar="MODULE_OR_FILE",
        nargs="+",
        help=(
            "One or more changed dotted module names or file paths "
            "(e.g. 'sample_app.utils' or 'sample_app/utils.py')."
        ),
    )
    review_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Print the RiskAssessment as machine-readable JSON.",
    )

    return parser


# ---------------------------------------------------------------------------
# Human-readable formatters
# ---------------------------------------------------------------------------


def _format_impact_human(report) -> str:  # type: ignore[no-untyped-def]
    """Render an :class:`~analyzer.impact.ImpactReport` as human-readable output.

    Args:
        report: The :class:`~analyzer.impact.ImpactReport` to render.

    Returns:
        Multi-line string suitable for terminal output.
    """
    sep = "-" * 60
    lines: list[str] = [
        "",
        sep,
        "  ImpactOS -- Change Impact Report",
        sep,
        f"  Target        : {report.target}",
        f"  Risk Level    : {report.risk_level}",
        f"  Impact Score  : {report.impact_score:.4f}",
        f"  Affected Count: {report.affected_count}",
        f"  Max Depth     : {report.max_depth}",
        sep,
    ]

    lines.append("  Direct Dependents:")
    if report.direct_dependents:
        for dep in report.direct_dependents:
            lines.append(f"    - {dep}")
    else:
        lines.append("    (none)")

    lines.append("")
    lines.append("  Indirect Dependents:")
    if report.indirect_dependents:
        for dep in report.indirect_dependents:
            lines.append(f"    - {dep}")
    else:
        lines.append("    (none)")

    lines.append("")
    lines.append("  All Affected Modules:")
    if report.affected_modules:
        for mod in report.affected_modules:
            lines.append(f"    - {mod}")
    else:
        lines.append("    (none)")

    lines.append("")
    lines.append("  Reasons:")
    for reason in report.reasons:
        lines.append(f"    [+] {reason}")

    lines.append(sep)
    lines.append("")
    return "\n".join(lines)


def _format_change_human(report) -> str:  # type: ignore[no-untyped-def]
    """Render a :class:`~analyzer.change.ChangeImpactReport` as demo-quality output.

    Args:
        report: The :class:`~analyzer.change.ChangeImpactReport` to render.

    Returns:
        Multi-line string suitable for terminal output.
    """
    sep = "=" * 60
    thin = "-" * 60
    lines: list[str] = [
        "",
        sep,
        " ImpactOS - Change Impact Analysis",
        sep,
    ]

    # Changed modules
    lines.append("")
    lines.append(f" Change Type: {report.change_type}")
    lines.append("")
    if len(report.changed_modules) == 1:
        lines.append(f" Changed:")
        lines.append(f"   {report.changed_modules[0]}")
    else:
        lines.append(f" Changed ({len(report.changed_modules)} modules):")
        for mod in report.changed_modules:
            lines.append(f"   {mod}")

    if report.unknown_modules:
        lines.append("")
        lines.append(" [!] Unresolved inputs (not in graph):")
        for u in report.unknown_modules:
            lines.append(f"   ? {u}")

    # Risk and score
    lines.append("")
    lines.append(f" Risk Level: {report.risk_level}")
    lines.append(f" Impact Score: {report.impact_score:.4f}")
    lines.append("")
    lines.append(thin)

    # Directly affected
    lines.append("")
    if report.direct_affected_modules:
        lines.append(f" Directly Affected ({len(report.direct_affected_modules)}):")
        for mod in report.direct_affected_modules:
            lines.append(f"   -> {mod}")
    else:
        lines.append(" Directly Affected: (none)")

    # Indirectly affected
    lines.append("")
    if report.indirect_affected_modules:
        lines.append(f" Indirectly Affected ({len(report.indirect_affected_modules)}):")
        for mod in report.indirect_affected_modules:
            lines.append(f"   ~> {mod}")
    else:
        lines.append(" Indirectly Affected: (none)")

    # Totals
    lines.append("")
    lines.append(thin)
    lines.append(f" Total Blast Radius: {report.affected_count} modules")
    lines.append(f" Maximum Depth     : {report.max_depth}")

    # Explanations
    if report.explanations:
        lines.append("")
        lines.append(" Why?")
        for exp in report.explanations:
            lines.append(f"   * {exp}")

    lines.append("")
    lines.append(sep)
    lines.append("")
    return "\n".join(lines)


def _format_review_human(
    assessment,  # type: ignore[no-untyped-def]
    changed: list,
) -> str:
    """Render a :class:`~analyzer.risk.RiskAssessment` as demo-quality output.

    Args:
        assessment: The :class:`~analyzer.risk.RiskAssessment` to render.
        changed:    List of changed module names (for the header).

    Returns:
        Multi-line string suitable for terminal output.
    """
    sep = "=" * 60
    lines: list[str] = [
        "",
        sep,
        " ImpactOS - Change Risk Review",
        sep,
        "",
    ]

    # Changed modules
    if len(changed) == 1:
        lines.append(" Changed:")
        lines.append(f"   {changed[0]}")
    else:
        lines.append(f" Changed ({len(changed)} modules):")
        for mod in changed:
            lines.append(f"   {mod}")

    lines.append("")
    lines.append(f" Risk Level   : {assessment.risk_level}")
    lines.append(f" Impact Score : {assessment.impact_score:.4f}")
    lines.append("")

    # Evidence
    if assessment.evidence:
        lines.append(" Evidence:")
        for ev in assessment.evidence:
            lines.append(f"   * {ev}")
        lines.append("")

    # TEST recommendations
    test_recs = [r for r in assessment.recommendations if r.category == "TEST"]
    if test_recs:
        lines.append(" Recommended Validation:")
        for rec in test_recs:
            lines.append(f"   [TEST] {rec.module}")
            lines.append(f"     {rec.priority} -- {rec.reason}")
            lines.append("")

    # REVIEW recommendations
    review_recs = [r for r in assessment.recommendations if r.category == "REVIEW"]
    if review_recs:
        lines.append(" Recommended Review:")
        for rec in review_recs:
            lines.append(f"   [REVIEW] {rec.module}")
            lines.append(f"     {rec.priority} -- {rec.reason}")
            lines.append("")

    lines.append(sep)
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _run_impact(args: argparse.Namespace) -> int:
    """Execute the ``impact`` command.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    from analyzer.impact import ImpactAnalyzer  # noqa: PLC0415
    from analyzer.repo_analyzer import RepoAnalyzer  # noqa: PLC0415

    repo_path = Path(args.repo_path)
    if not repo_path.is_dir():
        print(
            f"ERROR: repo_path {str(repo_path)!r} is not a directory.",
            file=sys.stderr,
        )
        return 1

    try:
        graph = RepoAnalyzer(repo_path).analyze()
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Repository analysis failed: {exc}", file=sys.stderr)
        return 1

    analyzer = ImpactAnalyzer(graph)
    try:
        report = analyzer.analyze(args.target)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        print(report.to_json())
    else:
        print(_format_impact_human(report))

    return 0


def _run_change(args: argparse.Namespace) -> int:
    """Execute the ``change`` command.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    from analyzer.change import ChangeAnalyzer, ChangeType  # noqa: PLC0415
    from analyzer.repo_analyzer import RepoAnalyzer  # noqa: PLC0415

    repo_path = Path(args.repo_path)
    if not repo_path.is_dir():
        print(
            f"ERROR: repo_path {str(repo_path)!r} is not a directory.",
            file=sys.stderr,
        )
        return 1

    try:
        graph = RepoAnalyzer(repo_path).analyze()
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Repository analysis failed: {exc}", file=sys.stderr)
        return 1

    ca = ChangeAnalyzer(graph, repo_root=repo_path)
    change_type = ChangeType(args.change_type)
    report = ca.analyze_changes(args.changed, change_type=change_type)

    if args.output_json:
        print(report.to_json())
    else:
        print(_format_change_human(report))

    return 0


def _run_review(args: argparse.Namespace) -> int:
    """Execute the ``review`` command.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    from analyzer.change import ChangeAnalyzer  # noqa: PLC0415
    from analyzer.repo_analyzer import RepoAnalyzer  # noqa: PLC0415
    from analyzer.risk import RiskAnalyzer  # noqa: PLC0415

    repo_path = Path(args.repo_path)
    if not repo_path.is_dir():
        print(
            f"ERROR: repo_path {str(repo_path)!r} is not a directory.",
            file=sys.stderr,
        )
        return 1

    try:
        graph = RepoAnalyzer(repo_path).analyze()
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Repository analysis failed: {exc}", file=sys.stderr)
        return 1

    ca = ChangeAnalyzer(graph, repo_root=repo_path)
    change_report = ca.analyze_changes(args.changed)
    assessment = RiskAnalyzer(change_report).assess()

    if args.output_json:
        print(assessment.to_json())
    else:
        print(_format_review_human(assessment, change_report.changed_modules))

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ImpactOS CLI.

    Args:
        argv: Argument list.  Defaults to ``sys.argv[1:]`` when ``None``.

    Returns:
        Exit code: ``0`` on success, ``1`` on error.
    """
    _ensure_package_importable()

    # Determine whether a subcommand was provided.
    # Use the *first* non-flag token and compare it against known subcommands.
    # This allows the legacy positional form ``<repo> <target>`` to still
    # work for backwards compatibility with Task 02 tests.
    args_list: list[str] = list(argv) if argv is not None else sys.argv[1:]
    known_commands = {"impact", "change", "review"}
    first_token = next(
        (a for a in args_list if not a.startswith("-")), None
    )

    if first_token in known_commands:
        parser = _build_parser()
        args = parser.parse_args(args_list)
        if args.command == "change":
            return _run_change(args)
        if args.command == "review":
            return _run_review(args)
        return _run_impact(args)
    else:
        # No recognised subcommand — fall back to legacy positional form for
        # backwards compatibility with Task 02 tests.
        return _legacy_impact(args_list)


def _legacy_impact(argv: list[str]) -> int:
    """Handle the legacy ``<repo_path> <target>`` positional form (Task 02).

    When the CLI is called without a subcommand, treat the arguments as
    ``impact <repo_path> <target> [--json]`` to stay backwards compatible
    with existing Task 02 tests.

    Args:
        argv: Argument list (already converted to a plain list).

    Returns:
        Exit code.
    """
    legacy = argparse.ArgumentParser(prog="analyzer.cli (legacy)")
    legacy.add_argument("repo_path")
    legacy.add_argument("target")
    legacy.add_argument("--json", action="store_true", dest="output_json")

    try:
        args = legacy.parse_args(argv)
    except SystemExit:
        print(
            "Usage: analyzer.cli {impact,change} ...\n"
            "       analyzer.cli <repo_path> <target_module> [--json]",
            file=sys.stderr,
        )
        return 1

    return _run_impact(args)


def _ensure_package_importable() -> None:
    """Add the parent directory of *analyzer/* to ``sys.path`` if needed."""
    this_file = Path(__file__).resolve()
    package_parent = str(this_file.parent.parent)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
