"""
tests.test_api
~~~~~~~~~~~~~~

Tests for the ImpactOS HTTP JSON API (Task 05 — analyzer/api.py).

Covers:
    01. GET /health returns 200 with status and service fields
    02. POST /analyze success — single changed file
    03. POST /analyze success — multiple changed files
    04. POST /analyze response contains all required top-level keys
    05. POST /analyze risk fields are present and correct types
    06. POST /analyze recommendations are present and well-formed
    07. POST /analyze response is deterministic (idempotent)
    08. POST /analyze missing repo_path → 400 INVALID_REQUEST
    09. POST /analyze missing changed_files → 400 INVALID_REQUEST
    10. POST /analyze empty changed_files → 400 INVALID_REQUEST
    11. POST /analyze changed_files not a list → 400 INVALID_REQUEST
    12. POST /analyze invalid (non-existent) repo path → 404 REPO_NOT_FOUND
    13. POST /analyze unknown changed file → 422 UNKNOWN_CHANGED_FILES
    14. POST /analyze malformed JSON body → 400 MALFORMED_JSON
    15. GET /analyze (unsupported method) → 405 METHOD_NOT_ALLOWED
    16. POST /health (unsupported method) → 405 METHOD_NOT_ALLOWED
    17. Unknown route → 404 NOT_FOUND
    18. Error envelope has success=false and error.code
    19. Success envelope has success=true and data object
    20. No regression — previous 139 tests still pass (sanity import)
"""

from __future__ import annotations

import http.client
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Ensure the analyzer package is importable
# ---------------------------------------------------------------------------
IMPACTOS_DIR = Path(__file__).parent.parent.resolve()
if str(IMPACTOS_DIR) not in sys.path:
    sys.path.insert(0, str(IMPACTOS_DIR))

from analyzer.api import make_server  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
FIXTURE_REPO_ROOT = IMPACTOS_DIR / "tests" / "fixtures"


def _find_free_port() -> int:
    """Return an ephemeral port that is currently free."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_server():
    """Start the ImpactOS API server in a background thread for the test module.

    Yields a ``(host, port)`` tuple.  The server is shut down after all tests
    in this module have run.
    """
    port = _find_free_port()
    host = "127.0.0.1"
    server = make_server(host=host, port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Brief pause to let the server bind and start accepting connections
    time.sleep(0.05)
    yield host, port
    server.shutdown()
    server.server_close()


def _request(
    host: str,
    port: int,
    method: str,
    path: str,
    body: Any = None,
    content_type: str = "application/json",
) -> tuple[int, Dict[str, Any]]:
    """Make an HTTP request and return ``(status_code, parsed_json_body)``."""
    conn = http.client.HTTPConnection(host, port, timeout=10)
    headers = {}
    raw: bytes = b""
    if body is not None:
        if isinstance(body, (dict, list)):
            raw = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            raw = body.encode("utf-8")
        elif isinstance(body, bytes):
            raw = body
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(raw))
    conn.request(method, path, body=raw if raw else None, headers=headers)
    resp = conn.getresponse()
    status = resp.status
    data = json.loads(resp.read().decode("utf-8"))
    conn.close()
    return status, data


# ---------------------------------------------------------------------------
# Helper — sample_app fixture path (as string, relative-style for the API)
# ---------------------------------------------------------------------------
SAMPLE_APP_REPO = str(FIXTURE_REPO_ROOT)


# ===========================================================================
# Tests
# ===========================================================================


class TestHealth:
    """01 — GET /health."""

    def test_health_status_200(self, api_server):
        host, port = api_server
        status, body = _request(host, port, "GET", "/health")
        assert status == 200

    def test_health_status_field(self, api_server):
        host, port = api_server
        _, body = _request(host, port, "GET", "/health")
        assert body["status"] == "ok"

    def test_health_service_field(self, api_server):
        host, port = api_server
        _, body = _request(host, port, "GET", "/health")
        assert body["service"] == "ImpactOS"


class TestAnalyzeSuccess:
    """02/03 — POST /analyze success cases."""

    def test_single_file_success(self, api_server):
        """02 — Single changed file returns 200 with success=True."""
        host, port = api_server
        payload = {
            "repo_path": SAMPLE_APP_REPO,
            "changed_files": ["sample_app/utils.py"],
        }
        status, body = _request(host, port, "POST", "/analyze", body=payload)
        assert status == 200
        assert body["success"] is True

    def test_multiple_files_success(self, api_server):
        """03 — Multiple changed files returns 200."""
        host, port = api_server
        payload = {
            "repo_path": SAMPLE_APP_REPO,
            "changed_files": ["sample_app/utils.py", "sample_app/models.py"],
        }
        status, body = _request(host, port, "POST", "/analyze", body=payload)
        assert status == 200
        assert body["success"] is True

    def test_changed_files_in_response(self, api_server):
        """Changed files list is echoed in the data."""
        host, port = api_server
        payload = {
            "repo_path": SAMPLE_APP_REPO,
            "changed_files": ["sample_app/utils.py"],
        }
        _, body = _request(host, port, "POST", "/analyze", body=payload)
        assert "sample_app/utils.py" in body["data"]["changed_files"]

    def test_changed_modules_resolved(self, api_server):
        """Changed file is resolved to a dotted module name."""
        host, port = api_server
        payload = {
            "repo_path": SAMPLE_APP_REPO,
            "changed_files": ["sample_app/utils.py"],
        }
        _, body = _request(host, port, "POST", "/analyze", body=payload)
        assert "sample_app.utils" in body["data"]["changed_modules"]


class TestResponseStructure:
    """04/05/06 — Response structure, risk fields, recommendations."""

    @pytest.fixture(scope="class")
    def analysis_response(self, api_server):
        host, port = api_server
        payload = {
            "repo_path": SAMPLE_APP_REPO,
            "changed_files": ["sample_app/utils.py"],
        }
        _, body = _request(host, port, "POST", "/analyze", body=payload)
        return body["data"]

    def test_all_required_keys_present(self, analysis_response):
        """04 — All required top-level keys are present."""
        required = {
            "changed_files",
            "changed_modules",
            "risk_level",
            "impact_score",
            "affected_count",
            "direct_count",
            "indirect_count",
            "max_depth",
            "direct_affected",
            "indirect_affected",
            "all_affected",
            "evidence",
            "recommendations",
            "unknown_files",
        }
        assert required.issubset(set(analysis_response.keys()))

    def test_risk_level_is_string(self, analysis_response):
        """05 — risk_level is a string."""
        assert isinstance(analysis_response["risk_level"], str)
        assert analysis_response["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def test_impact_score_is_float(self, analysis_response):
        """05 — impact_score is a float in [0.0, 1.0]."""
        score = analysis_response["impact_score"]
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 1.0

    def test_affected_count_is_int(self, analysis_response):
        """05 — affected_count is a non-negative integer."""
        count = analysis_response["affected_count"]
        assert isinstance(count, int)
        assert count >= 0

    def test_affected_count_matches_all_affected(self, analysis_response):
        """affected_count equals len(all_affected)."""
        assert analysis_response["affected_count"] == len(analysis_response["all_affected"])

    def test_recommendations_is_list(self, analysis_response):
        """06 — recommendations is a list."""
        assert isinstance(analysis_response["recommendations"], list)

    def test_recommendation_has_required_fields(self, analysis_response):
        """06 — Each recommendation has category, module, priority, action, reason."""
        required = {"category", "module", "priority", "action", "reason"}
        for rec in analysis_response["recommendations"]:
            assert required.issubset(set(rec.keys())), f"Recommendation missing fields: {rec}"

    def test_recommendation_priority_values(self, analysis_response):
        """06 — Recommendation priority is HIGH, MEDIUM, or LOW."""
        for rec in analysis_response["recommendations"]:
            assert rec["priority"] in {"HIGH", "MEDIUM", "LOW"}

    def test_recommendation_category_values(self, analysis_response):
        """06 — Recommendation category is TEST or REVIEW."""
        for rec in analysis_response["recommendations"]:
            assert rec["category"] in {"TEST", "REVIEW"}

    def test_evidence_is_list_of_strings(self, analysis_response):
        """Evidence is a list of non-empty strings."""
        assert isinstance(analysis_response["evidence"], list)
        for item in analysis_response["evidence"]:
            assert isinstance(item, str) and item


class TestDeterminism:
    """07 — Response is deterministic."""

    def test_deterministic_response(self, api_server):
        """07 — Identical inputs produce identical JSON responses."""
        host, port = api_server
        payload = {
            "repo_path": SAMPLE_APP_REPO,
            "changed_files": ["sample_app/utils.py"],
        }
        _, body1 = _request(host, port, "POST", "/analyze", body=payload)
        _, body2 = _request(host, port, "POST", "/analyze", body=payload)
        assert body1 == body2


class TestValidationErrors:
    """08–11 — Request validation error handling."""

    def test_missing_repo_path(self, api_server):
        """08 — Missing repo_path → 400 INVALID_REQUEST."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"changed_files": ["sample_app/utils.py"]},
        )
        assert status == 400
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_REQUEST"
        assert "repo_path" in body["error"]["message"]

    def test_missing_changed_files(self, api_server):
        """09 — Missing changed_files triggers Git auto-detection (Task 06).

        When changed_files is omitted the API falls through to Git detection.
        The response must not be a validation error about 'changed_files'
        being required — it is now optional.  The fixture dir may or may not
        be inside a Git repo depending on the environment; we only assert
        that validation-level rejection is absent.
        """
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": SAMPLE_APP_REPO},
        )
        assert body["success"] is False or body["success"] is True  # either is valid
        # Must NOT return the old "changed_files is required" validation error
        if not body["success"]:
            assert not (
                body["error"]["code"] == "INVALID_REQUEST"
                and "changed_files" in body["error"]["message"]
            )

    def test_empty_changed_files(self, api_server):
        """10 — Empty changed_files list → 400 INVALID_REQUEST."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": SAMPLE_APP_REPO, "changed_files": []},
        )
        assert status == 400
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_REQUEST"

    def test_changed_files_not_a_list(self, api_server):
        """11 — changed_files is a string, not a list → 400 INVALID_REQUEST."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": SAMPLE_APP_REPO,
                "changed_files": "sample_app/utils.py",
            },
        )
        assert status == 400
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_REQUEST"


class TestPathErrors:
    """12 — Repository path errors."""

    def test_nonexistent_repo_path(self, api_server):
        """12 — Non-existent repo path → 404 REPO_NOT_FOUND."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": "/does/not/exist/anywhere",
                "changed_files": ["sample_app/utils.py"],
            },
        )
        assert status == 404
        assert body["success"] is False
        assert body["error"]["code"] == "REPO_NOT_FOUND"


class TestUnknownFile:
    """13 — Unknown changed file."""

    def test_unknown_changed_file(self, api_server):
        """13 — A file not in the repo graph → 422 UNKNOWN_CHANGED_FILES."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": SAMPLE_APP_REPO,
                "changed_files": ["totally_unknown_module.py"],
            },
        )
        assert status == 422
        assert body["success"] is False
        assert body["error"]["code"] == "UNKNOWN_CHANGED_FILES"


class TestMalformedRequest:
    """14 — Malformed JSON body."""

    def test_malformed_json(self, api_server):
        """14 — Non-JSON body → 400 MALFORMED_JSON."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body=b"this is not { json",
        )
        assert status == 400
        assert body["success"] is False
        assert body["error"]["code"] == "MALFORMED_JSON"


class TestMethodNotAllowed:
    """15/16 — Unsupported HTTP methods."""

    def test_get_analyze_not_allowed(self, api_server):
        """15 — GET /analyze is not supported → 405."""
        host, port = api_server
        status, body = _request(host, port, "GET", "/analyze")
        assert status == 405
        assert body["success"] is False
        assert body["error"]["code"] == "METHOD_NOT_ALLOWED"

    def test_post_health_not_allowed(self, api_server):
        """16 — POST /health is not supported → 405."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/health",
            body={"some": "body"},
        )
        assert status == 405
        assert body["success"] is False
        assert body["error"]["code"] == "METHOD_NOT_ALLOWED"


class TestNotFound:
    """17 — Unknown routes."""

    def test_unknown_route(self, api_server):
        """17 — Unknown route → 404 NOT_FOUND."""
        host, port = api_server
        status, body = _request(host, port, "GET", "/unknown/route")
        assert status == 404
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_FOUND"


class TestEnvelopeContract:
    """18/19 — Envelope shape contract."""

    def test_error_envelope_shape(self, api_server):
        """18 — Error envelope has success=False and error.code."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"changed_files": ["a.py"]},
        )
        assert body["success"] is False
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    def test_success_envelope_shape(self, api_server):
        """19 — Success envelope has success=True and data dict."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": SAMPLE_APP_REPO,
                "changed_files": ["sample_app/utils.py"],
            },
        )
        assert body["success"] is True
        assert isinstance(body["data"], dict)


class TestNoRegression:
    """20 — Smoke-test that Tasks 01–04 public API is still importable."""

    def test_all_public_api_importable(self):
        """20 — Tasks 01–04 public symbols remain importable."""
        from analyzer import (  # noqa: F401
            ChangeAnalyzer,
            ChangeImpactReport,
            ChangeType,
            DependencyGraph,
            GraphEdge,
            GraphNode,
            ImpactAnalyzer,
            ImpactReport,
            ParsedModule,
            Recommendation,
            RepoAnalyzer,
            RiskAnalyzer,
            RiskAssessment,
            parse_file,
        )
