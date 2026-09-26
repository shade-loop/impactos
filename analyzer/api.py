"""
analyzer.api
~~~~~~~~~~~~

ImpactOS HTTP JSON API — Tasks 05–06.

Exposes the ImpactOS analysis pipeline through a minimal HTTP server built on
the Python standard library (``http.server`` + ``socketserver``).  No external
web framework is required.

Architecture
------------
::

    HTTP Request
         ↓
     ImpactOS API  (this module)
         ↓
     GitChangeDetector (when changed_files omitted — Task 06)
         ↓
     RepoAnalyzer
         ↓
     DependencyGraph
         ↓
     ChangeAnalyzer
         ↓
     RiskAnalyzer
         ↓
     JSON Response

This module is a **thin integration layer only**.  All business logic lives in
the analyzer sub-modules from Tasks 01–04.

Usage
-----
Start the server::

    python -m analyzer.api                          # default 127.0.0.1:8000
    python -m analyzer.api --host 0.0.0.0 --port 9000

Endpoints
---------
GET  /health   — liveness check
POST /analyze  — full dependency-change-risk analysis

CORS
----
Development CORS is enabled for all origins (``Access-Control-Allow-Origin: *``).
This is intentional for a local hackathon demo.  Do not use in production.
"""

from __future__ import annotations

import argparse
import json
import logging
import socketserver
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ensure the analyzer package is importable when the module is run directly.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent.parent  # …/impactos
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from analyzer.change import ChangeAnalyzer  # noqa: E402
from analyzer.git import (  # noqa: E402
    GitChange,
    GitChangeDetector,
    GitError,
    NotAGitRepository,
    RepositoryNotFound,
)
from analyzer.repo_analyzer import RepoAnalyzer  # noqa: E402
from analyzer.risk import RiskAnalyzer  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
SERVICE_NAME = "ImpactOS"

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap *data* in the standard success envelope."""
    return {"success": True, "data": data}


def _error_response(code: str, message: str) -> Dict[str, Any]:
    """Wrap an error in the standard error envelope."""
    return {"success": False, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# Analysis pipeline
# ---------------------------------------------------------------------------


def _run_analysis(
    repo_path: str,
    changed_files: Optional[List[str]],
) -> Tuple[bool, int, Dict[str, Any]]:
    """Run the full ImpactOS pipeline and return a serialisable result.

    Delegates entirely to Tasks 01–06 classes; contains no business logic.

    Args:
        repo_path:     Path to the repository root directory.
        changed_files: List of file paths to analyse, or ``None`` to trigger
                       automatic Git change detection (Task 06).

    Returns:
        A 3-tuple ``(ok, http_status, body_dict)``.  When *ok* is ``True``
        *body_dict* is a success envelope; otherwise it is an error envelope.
    """
    path = Path(repo_path)
    if not path.exists():
        return (
            False,
            404,
            _error_response(
                "REPO_NOT_FOUND",
                f"Repository path does not exist: {repo_path}",
            ),
        )
    if not path.is_dir():
        return (
            False,
            400,
            _error_response(
                "REPO_NOT_A_DIRECTORY",
                f"Repository path is not a directory: {repo_path}",
            ),
        )

    # ------------------------------------------------------------------
    # Task 06 — automatic Git change detection
    # ------------------------------------------------------------------
    git_changes: List[GitChange] = []
    source: str

    if changed_files is None:
        # Automatic mode: detect changes from Git.
        try:
            detector = GitChangeDetector(path)
            git_changes = detector.detect_changes()
        except RepositoryNotFound as exc:
            return (
                False,
                404,
                _error_response("REPO_NOT_FOUND", str(exc)),
            )
        except NotAGitRepository as exc:
            return (
                False,
                400,
                _error_response("NOT_A_GIT_REPO", str(exc)),
            )
        except GitError as exc:
            return (
                False,
                500,
                _error_response("GIT_ERROR", f"Git detection failed: {exc}"),
            )

        source = "git"
        changed_files = [c.path for c in git_changes]

        # No changed Python files — return a clean empty success response.
        if not changed_files:
            empty_data: Dict[str, Any] = {
                "source": source,
                "git_changes": [],
                "changed_files": [],
                "changed_modules": [],
                "risk_level": "LOW",
                "impact_score": 0.0,
                "affected_count": 0,
                "direct_count": 0,
                "indirect_count": 0,
                "max_depth": 0,
                "direct_affected": [],
                "indirect_affected": [],
                "all_affected": [],
                "evidence": [],
                "recommendations": [],
                "unknown_files": [],
            }
            return True, 200, _success_response(empty_data)
    else:
        source = "manual"

    try:
        # Task 01 — build dependency graph
        graph = RepoAnalyzer(path).analyze()

        # Task 03 — change impact
        ca = ChangeAnalyzer(graph, repo_root=path)
        change_report = ca.analyze_changes(changed_files)

        # Task 04 — risk assessment
        risk = RiskAnalyzer(change_report).assess()

    except Exception as exc:  # pragma: no cover — unexpected internal error
        logger.exception("Internal analysis error")
        return (
            False,
            500,
            _error_response("ANALYSIS_ERROR", f"Internal analysis error: {exc}"),
        )

    # Check for unknown files/modules (soft error — still return 200 with data
    # but flag unknown_modules so the caller can surface them).
    # Only raise this error for manual mode; in git mode, deleted files may
    # not be in the graph and that is expected/acceptable.
    if source == "manual" and change_report.unknown_modules and not change_report.changed_modules:
        # Every input was unknown — nothing could be analysed
        return (
            False,
            422,
            _error_response(
                "UNKNOWN_CHANGED_FILES",
                (
                    "None of the provided changed_files could be resolved to a "
                    f"known module: {change_report.unknown_modules}"
                ),
            ),
        )

    # Build the combined response data by serialising ChangeImpactReport +
    # RiskAssessment.  No logic is duplicated; we simply merge the two dicts.
    change_dict = change_report.to_dict()
    risk_dict = risk.to_dict()

    # Serialise git_changes for the response.
    git_changes_list = [
        {"path": c.path, "status": c.status} for c in git_changes
    ]

    data: Dict[str, Any] = {
        # --- Task 06 fields ---
        "source": source,
        "git_changes": git_changes_list,
        # --- from ChangeImpactReport ---
        "changed_files": change_dict["changed_files"],
        "changed_modules": change_dict["changed_modules"],
        # --- from RiskAssessment (authoritative risk numbers) ---
        "risk_level": risk_dict["risk_level"],
        "impact_score": risk_dict["impact_score"],
        "affected_count": risk_dict["affected_count"],
        "direct_count": risk_dict["direct_count"],
        "indirect_count": risk_dict["indirect_count"],
        "max_depth": risk_dict["max_depth"],
        # --- affected module lists (from ChangeImpactReport) ---
        "direct_affected": change_dict["direct_affected_modules"],
        "indirect_affected": change_dict["indirect_affected_modules"],
        "all_affected": change_dict["all_affected_modules"],
        # --- evidence + recommendations (from RiskAssessment) ---
        "evidence": risk_dict["evidence"],
        "recommendations": risk_dict["recommendations"],
        # --- extra context ---
        "unknown_files": change_dict["unknown_modules"],
    }

    return True, 200, _success_response(data)


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def _validate_request(body: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Validate the POST /analyze request body.

    ``changed_files`` is now **optional** (Task 06 automatic mode).  When
    omitted, Git change detection is used.  When supplied it must be a
    non-empty list of strings (unchanged from Task 05).

    Args:
        body: Parsed JSON dict from the request.

    Returns:
        ``None`` if valid, or a ``(error_code, message)`` tuple if not.
    """
    if "repo_path" not in body:
        return ("INVALID_REQUEST", "repo_path is required")
    if not isinstance(body["repo_path"], str) or not body["repo_path"].strip():
        return ("INVALID_REQUEST", "repo_path must be a non-empty string")
    # changed_files is optional in Task 06 automatic mode.
    if "changed_files" in body:
        if not isinstance(body["changed_files"], list):
            return ("INVALID_REQUEST", "changed_files must be a list")
        if len(body["changed_files"]) == 0:
            return ("INVALID_REQUEST", "changed_files must not be empty")
        for item in body["changed_files"]:
            if not isinstance(item, str):
                return ("INVALID_REQUEST", "each entry in changed_files must be a string")
    return None


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------


class _ImpactOSHandler(BaseHTTPRequestHandler):
    """Minimal HTTP request handler for the ImpactOS API.

    Handles:
        GET  /health
        POST /analyze
        OPTIONS *  (CORS pre-flight)

    All other method/path combinations return appropriate error responses.
    """

    # ------------------------------------------------------------------
    # Logging — suppress the default per-request stdout noise unless debug
    # ------------------------------------------------------------------
    def log_message(self, fmt: str, *args: Any) -> None:  # type: ignore[override]
        logger.debug("%s - - %s", self.address_string(), fmt % args)

    # ------------------------------------------------------------------
    # CORS helper
    # ------------------------------------------------------------------
    def _send_cors_headers(self) -> None:
        for key, value in _CORS_HEADERS.items():
            self.send_header(key, value)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------
    def _send_json(self, status: int, body: Dict[str, Any]) -> None:
        payload = json.dumps(body, sort_keys=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    # Known routes: path → set of allowed HTTP methods
    _ROUTES: Dict[str, set] = {
        "/health": {"GET"},
        "/analyze": {"POST"},
    }

    # ------------------------------------------------------------------
    # Route dispatch
    # ------------------------------------------------------------------
    def do_OPTIONS(self) -> None:  # noqa: N802
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _dispatch(self) -> None:
        """Central dispatcher: checks path existence before method."""
        method = self.command
        path = self.path

        if path not in self._ROUTES:
            self._send_json(
                404,
                _error_response("NOT_FOUND", f"No route for {method} {path}"),
            )
            return

        if method not in self._ROUTES[path]:
            self._send_json(
                405,
                _error_response(
                    "METHOD_NOT_ALLOWED",
                    f"Method {method} is not allowed on {path}",
                ),
            )
            return

        if path == "/health":
            self._handle_health()
        elif path == "/analyze":
            self._handle_analyze()

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _handle_unsupported_method(self) -> None:
        self._dispatch()

    # Map unhandled verbs to the central dispatcher
    do_PUT = do_DELETE = do_PATCH = _handle_unsupported_method  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _handle_health(self) -> None:
        self._send_json(200, {"status": "ok", "service": SERVICE_NAME})

    def _handle_analyze(self) -> None:
        # 1. Parse Content-Length and body
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raw = b""
        else:
            try:
                length = int(length_header)
            except ValueError:
                self._send_json(
                    400,
                    _error_response("INVALID_REQUEST", "Invalid Content-Length header"),
                )
                return
            raw = self.rfile.read(length)

        # 2. Parse JSON
        if not raw:
            self._send_json(
                400,
                _error_response("INVALID_REQUEST", "Request body must be JSON"),
            )
            return
        try:
            body: Dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json(
                400,
                _error_response("MALFORMED_JSON", f"Request body is not valid JSON: {exc}"),
            )
            return
        if not isinstance(body, dict):
            self._send_json(
                400,
                _error_response("INVALID_REQUEST", "Request body must be a JSON object"),
            )
            return

        # 3. Validate fields
        validation_error = _validate_request(body)
        if validation_error is not None:
            code, message = validation_error
            self._send_json(400, _error_response(code, message))
            return

        # 4. Run the analysis pipeline
        # changed_files is optional (Task 06): pass None when absent to
        # trigger automatic Git change detection.
        ok, status, response_body = _run_analysis(
            repo_path=body["repo_path"],
            changed_files=body.get("changed_files"),  # None if omitted
        )
        self._send_json(status, response_body)


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> socketserver.TCPServer:
    """Create and return a configured ``TCPServer`` instance.

    The server uses ``allow_reuse_address = True`` so it can be restarted
    quickly during development.

    Args:
        host: Bind address (default ``"127.0.0.1"``).
        port: Bind port (default ``8000``).

    Returns:
        A ready-to-serve ``socketserver.TCPServer`` instance.
    """

    class _ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    return _ReusableTCPServer((host, port), _ImpactOSHandler)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m analyzer.api",
        description="ImpactOS HTTP JSON API server",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Bind port (default: {DEFAULT_PORT})",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    """Start the ImpactOS API server.

    This is the ``python -m analyzer.api`` entry point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
    )
    args = _parse_args(argv)
    server = make_server(host=args.host, port=args.port)
    logger.info("ImpactOS API listening on http://%s:%d", args.host, args.port)
    logger.info("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":  # pragma: no cover
    main()
