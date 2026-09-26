"""
analyzer.cli
~~~~~~~~~~~~

Lightweight command-line interface for ImpactOS.

Usage
-----
::

    # Human-readable report (default)
    python -m analyzer.cli <repo_path> <target_module>

    # Machine-readable JSON
    python -m analyzer.cli <repo_path> <target_module> --json

Examples::

    python -m analyzer.cli tests/fixtures sample_app.utils
    python -m analyzer.cli tests/fixtures sample_app.models --json

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


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="analyzer.cli",
        description=(
            "ImpactOS — dependency-based change impact analyser.\n\n"
            "Analyses a Python repository and reports the blast radius of "
            "changing a specific module."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "repo_path",
        metavar="REPO_PATH",
        help="Root directory of the Python repository to analyse.",
    )
    parser.add_argument(
        "target",
        metavar="TARGET_MODULE",
        help=(
            "Dotted module name of the changed module "
            "(e.g. 'sample_app.utils')."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Print the ImpactReport as machine-readable JSON.",
    )
    return parser


def _format_human(report) -> str:  # type: ignore[no-untyped-def]
    """Render an :class:`~analyzer.impact.ImpactReport` as a human-readable string.

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


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ImpactOS CLI.

    Args:
        argv: Argument list.  Defaults to ``sys.argv[1:]`` when ``None``.

    Returns:
        Exit code: ``0`` on success, ``1`` on error.
    """
    # Ensure the analyzer package is importable when called as
    # ``python -m analyzer.cli`` from the impactos/ directory.
    _ensure_package_importable()

    from analyzer.impact import ImpactAnalyzer  # noqa: PLC0415  (late import)
    from analyzer.repo_analyzer import RepoAnalyzer  # noqa: PLC0415

    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_path = Path(args.repo_path)
    if not repo_path.is_dir():
        print(
            f"ERROR: repo_path {str(repo_path)!r} is not a directory.",
            file=sys.stderr,
        )
        return 1

    # --- Analyse the repository ---
    try:
        graph = RepoAnalyzer(repo_path).analyze()
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Repository analysis failed: {exc}", file=sys.stderr)
        return 1

    # --- Compute the impact report ---
    analyzer = ImpactAnalyzer(graph)
    try:
        report = analyzer.analyze(args.target)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # --- Output ---
    if args.output_json:
        print(report.to_json())
    else:
        print(_format_human(report))

    return 0


def _ensure_package_importable() -> None:
    """Add the parent directory of *analyzer/* to ``sys.path`` if needed.

    When the CLI is run via ``python -m analyzer.cli`` from the ``impactos/``
    directory Python already resolves the package.  This guard handles the
    case where the script is run from a parent directory.
    """
    # The analyzer package lives at <impactos>/analyzer/.
    # Its parent (<impactos>/) must be on sys.path.
    this_file = Path(__file__).resolve()
    package_parent = str(this_file.parent.parent)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
