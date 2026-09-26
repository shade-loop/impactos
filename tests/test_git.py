"""
tests.test_git
~~~~~~~~~~~~~~

Tests for the Git change detection module (Task 06 — analyzer/git.py) and
the new automatic Git mode of the ImpactOS HTTP API.

Each test creates a real temporary Git repository via ``git init``, makes
controlled changes, and verifies that GitChangeDetector reports the correct
set of :class:`~analyzer.git.GitChange` objects.

Coverage
--------
GitChangeDetector unit tests:
  01. Git repository detection — valid repo
  02. Git repository detection — non-Git directory
  03. Modified Python file (unstaged)
  04. Staged Python file (staged only)
  05. Staged + unstaged modification (both X and Y set)
  06. Added/new Python file (untracked)
  07. Deleted Python file
  08. Renamed Python file
  09. Non-Python files are ignored
  10. Untracked Python file classified as added
  11. Deterministic sorted output
  12. Filename containing spaces
  13. Missing repository path raises RepositoryNotFound
  14. Git command failure / error handling (non-Git dir raises NotAGitRepository)

API integration tests (Git mode):
  15. Manual changed_files mode still works exactly as before
  16. Omitted changed_files triggers Git detection (source="git")
  17. source="git" present in response when Git mode used
  18. source="manual" present in response when changed_files supplied
  19. git_changes contents are present and correct
  20. No changed Python files → success with empty lists
  21. Invalid / non-Git repository returns 400 NOT_A_GIT_REPO
  22. Deleted Python file — behaviour documented, no crash
"""

from __future__ import annotations

import http.client
import json
import os
import subprocess
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

from analyzer.git import (  # noqa: E402
    GitChange,
    GitChangeDetector,
    GitError,
    NotAGitRepository,
    RepositoryNotFound,
)
from analyzer.api import make_server  # noqa: E402

# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

_GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t.com"}


def _git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    """Run a git command; raise if it fails."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_GIT_ENV,
        check=True,
    )


def _init_repo(path: Path) -> None:
    """Initialise a bare Git repo with an initial empty commit."""
    _git(["init", "--initial-branch=main"], str(path))
    _git(["config", "user.email", "test@test.com"], str(path))
    _git(["config", "user.name", "Test"], str(path))
    # Create initial commit so HEAD exists
    (path / "README.md").write_text("# test\n")
    _git(["add", "README.md"], str(path))
    _git(["commit", "-m", "init"], str(path))


# ---------------------------------------------------------------------------
# Fixture — server
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_server():
    """Start the ImpactOS API server in a background thread for this module."""
    port = _find_free_port()
    host = "127.0.0.1"
    server = make_server(host=host, port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
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
) -> tuple[int, Dict[str, Any]]:
    conn = http.client.HTTPConnection(host, port, timeout=10)
    headers: dict[str, str] = {}
    raw: bytes = b""
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(raw))
    conn.request(method, path, body=raw if raw else None, headers=headers)
    resp = conn.getresponse()
    status = resp.status
    data = json.loads(resp.read().decode("utf-8"))
    conn.close()
    return status, data


FIXTURE_REPO_ROOT = str(IMPACTOS_DIR / "tests" / "fixtures")

# ===========================================================================
# 01–14: GitChangeDetector unit tests
# ===========================================================================


class TestIsGitRepository:
    """01–02 — is_git_repository()."""

    def test_valid_git_repo(self, tmp_path):
        """01 — Valid Git repo returns True."""
        _init_repo(tmp_path)
        detector = GitChangeDetector(tmp_path)
        assert detector.is_git_repository() is True

    def test_non_git_directory(self, tmp_path):
        """02 — Plain directory returns False."""
        detector = GitChangeDetector(tmp_path)
        assert detector.is_git_repository() is False

    def test_missing_path_returns_false(self, tmp_path):
        """Missing path returns False (is_git_repository never raises)."""
        detector = GitChangeDetector(tmp_path / "nonexistent")
        assert detector.is_git_repository() is False


class TestModifiedFile:
    """03 — Unstaged modification."""

    def test_unstaged_modified_python_file(self, tmp_path):
        """03 — An unstaged modified .py file is detected as 'modified'."""
        _init_repo(tmp_path)
        py_file = tmp_path / "foo.py"
        py_file.write_text("x = 1\n")
        _git(["add", "foo.py"], str(tmp_path))
        _git(["commit", "-m", "add foo.py"], str(tmp_path))

        # Now modify it without staging
        py_file.write_text("x = 2\n")

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "foo.py" in paths
        match = next(c for c in changes if c.path == "foo.py")
        assert match.status == "modified"


class TestStagedFile:
    """04 — Staged modification."""

    def test_staged_modified_python_file(self, tmp_path):
        """04 — A staged modified .py file is detected as 'modified'."""
        _init_repo(tmp_path)
        py_file = tmp_path / "staged.py"
        py_file.write_text("a = 1\n")
        _git(["add", "staged.py"], str(tmp_path))
        _git(["commit", "-m", "add staged.py"], str(tmp_path))

        py_file.write_text("a = 2\n")
        _git(["add", "staged.py"], str(tmp_path))

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "staged.py" in paths
        match = next(c for c in changes if c.path == "staged.py")
        assert match.status == "modified"


class TestStagedAndUnstaged:
    """05 — Staged + unstaged modification (MM status)."""

    def test_staged_plus_unstaged(self, tmp_path):
        """05 — File modified both staged and unstaged is still reported."""
        _init_repo(tmp_path)
        py_file = tmp_path / "both.py"
        py_file.write_text("v = 1\n")
        _git(["add", "both.py"], str(tmp_path))
        _git(["commit", "-m", "add both.py"], str(tmp_path))

        # Stage one change
        py_file.write_text("v = 2\n")
        _git(["add", "both.py"], str(tmp_path))

        # Then make another unstaged change
        py_file.write_text("v = 3\n")

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "both.py" in paths
        match = next(c for c in changes if c.path == "both.py")
        assert match.status == "modified"


class TestAddedFile:
    """06 — Staged new file."""

    def test_staged_new_python_file(self, tmp_path):
        """06 — A staged-but-not-committed .py file is detected as 'added'."""
        _init_repo(tmp_path)
        new_file = tmp_path / "new.py"
        new_file.write_text("pass\n")
        _git(["add", "new.py"], str(tmp_path))

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "new.py" in paths
        match = next(c for c in changes if c.path == "new.py")
        assert match.status == "added"


class TestDeletedFile:
    """07 — Deleted Python file."""

    def test_deleted_python_file(self, tmp_path):
        """07 — A deleted .py file is detected as 'deleted'."""
        _init_repo(tmp_path)
        py_file = tmp_path / "old.py"
        py_file.write_text("pass\n")
        _git(["add", "old.py"], str(tmp_path))
        _git(["commit", "-m", "add old.py"], str(tmp_path))

        _git(["rm", "old.py"], str(tmp_path))

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "old.py" in paths
        match = next(c for c in changes if c.path == "old.py")
        assert match.status == "deleted"

    def test_deleted_file_unstaged(self, tmp_path):
        """07b — A file deleted from disk (not staged) is also detected."""
        _init_repo(tmp_path)
        py_file = tmp_path / "gone.py"
        py_file.write_text("pass\n")
        _git(["add", "gone.py"], str(tmp_path))
        _git(["commit", "-m", "add gone.py"], str(tmp_path))

        os.remove(py_file)

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "gone.py" in paths
        match = next(c for c in changes if c.path == "gone.py")
        assert match.status == "deleted"


class TestRenamedFile:
    """08 — Renamed Python file."""

    def test_renamed_python_file(self, tmp_path):
        """08 — A renamed .py file is detected as 'renamed' with new path."""
        _init_repo(tmp_path)
        old_file = tmp_path / "oldname.py"
        old_file.write_text("pass\n")
        _git(["add", "oldname.py"], str(tmp_path))
        _git(["commit", "-m", "add oldname.py"], str(tmp_path))

        _git(["mv", "oldname.py", "newname.py"], str(tmp_path))

        changes = GitChangeDetector(tmp_path).detect_changes()
        # new path is reported as renamed
        paths = [c.path for c in changes]
        assert "newname.py" in paths
        match = next(c for c in changes if c.path == "newname.py")
        assert match.status == "renamed"


class TestNonPythonIgnored:
    """09 — Non-Python files are ignored."""

    def test_non_python_files_not_reported(self, tmp_path):
        """09 — .txt, .md, .json files do not appear in results."""
        _init_repo(tmp_path)
        (tmp_path / "notes.txt").write_text("hello\n")
        (tmp_path / "data.json").write_text("{}\n")
        (tmp_path / "docs.md").write_text("# doc\n")
        _git(["add", "."], str(tmp_path))

        changes = GitChangeDetector(tmp_path).detect_changes()
        assert all(c.path.endswith(".py") for c in changes)


class TestUntrackedFile:
    """10 — Untracked Python file is classified as 'added'."""

    def test_untracked_python_file_is_added(self, tmp_path):
        """10 — An untracked .py file appears with status='added'."""
        _init_repo(tmp_path)
        (tmp_path / "untracked.py").write_text("pass\n")
        # NOT staged

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "untracked.py" in paths
        match = next(c for c in changes if c.path == "untracked.py")
        assert match.status == "added"


class TestDeterministicOutput:
    """11 — Sorted, deterministic output."""

    def test_output_sorted_by_path(self, tmp_path):
        """11 — Results are sorted lexicographically by path."""
        _init_repo(tmp_path)
        for name in ["zzz.py", "aaa.py", "mmm.py"]:
            (tmp_path / name).write_text("pass\n")
        # Leave as untracked (will be "added")

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert paths == sorted(paths)

    def test_identical_calls_produce_same_result(self, tmp_path):
        """11b — Two successive calls produce the same list."""
        _init_repo(tmp_path)
        (tmp_path / "stable.py").write_text("x = 1\n")

        d = GitChangeDetector(tmp_path)
        r1 = d.detect_changes()
        r2 = d.detect_changes()
        assert r1 == r2


class TestFilenameWithSpaces:
    """12 — Filename containing spaces."""

    def test_file_with_spaces_in_name(self, tmp_path):
        """12 — Paths containing spaces are handled correctly."""
        _init_repo(tmp_path)
        spaced = tmp_path / "my module.py"
        spaced.write_text("pass\n")
        # Leave untracked

        changes = GitChangeDetector(tmp_path).detect_changes()
        paths = [c.path for c in changes]
        assert "my module.py" in paths


class TestMissingPath:
    """13 — Missing repository path."""

    def test_missing_path_raises_repository_not_found(self, tmp_path):
        """13 — detect_changes raises RepositoryNotFound for missing path."""
        missing = tmp_path / "does_not_exist"
        with pytest.raises(RepositoryNotFound):
            GitChangeDetector(missing).detect_changes()

    def test_missing_path_is_git_repo_returns_false(self, tmp_path):
        """13b — is_git_repository() returns False for missing path."""
        detector = GitChangeDetector(tmp_path / "nope")
        assert detector.is_git_repository() is False


class TestGitCommandFailure:
    """14 — Git command failure / error handling."""

    def test_non_git_directory_raises_not_a_git_repo(self, tmp_path):
        """14 — detect_changes raises NotAGitRepository for plain dir."""
        with pytest.raises(NotAGitRepository):
            GitChangeDetector(tmp_path).detect_changes()

    def test_not_a_git_repo_is_subclass_of_git_error(self):
        """14b — NotAGitRepository is a GitError subclass."""
        assert issubclass(NotAGitRepository, GitError)

    def test_repository_not_found_is_subclass_of_git_error(self):
        """14c — RepositoryNotFound is a GitError subclass."""
        assert issubclass(RepositoryNotFound, GitError)


# ===========================================================================
# 15–22: API integration tests for Git mode
# ===========================================================================


class TestManualModeUnchanged:
    """15/18 — Manual mode (changed_files supplied) is unaffected."""

    def test_manual_mode_returns_200(self, api_server):
        """15 — Supplying changed_files still returns 200."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": FIXTURE_REPO_ROOT,
                "changed_files": ["sample_app/utils.py"],
            },
        )
        assert status == 200
        assert body["success"] is True

    def test_manual_mode_source_is_manual(self, api_server):
        """18 — source='manual' when changed_files supplied."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": FIXTURE_REPO_ROOT,
                "changed_files": ["sample_app/utils.py"],
            },
        )
        assert body["data"]["source"] == "manual"

    def test_manual_mode_git_changes_empty(self, api_server):
        """18b — git_changes=[] when changed_files supplied manually."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": FIXTURE_REPO_ROOT,
                "changed_files": ["sample_app/utils.py"],
            },
        )
        assert body["data"]["git_changes"] == []

    def test_manual_mode_preserves_existing_fields(self, api_server):
        """15b — All existing response fields are still present in manual mode."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={
                "repo_path": FIXTURE_REPO_ROOT,
                "changed_files": ["sample_app/utils.py"],
            },
        )
        required = {
            "changed_files", "changed_modules", "risk_level", "impact_score",
            "affected_count", "direct_count", "indirect_count", "max_depth",
            "direct_affected", "indirect_affected", "all_affected",
            "evidence", "recommendations", "unknown_files",
        }
        assert required.issubset(set(body["data"].keys()))


class TestGitAutoMode:
    """16/17/19 — Automatic Git detection (changed_files omitted)."""

    @pytest.fixture(scope="class")
    def git_repo_with_changes(self, tmp_path_factory):
        """Create a temp Git repo with a staged Python change."""
        repo = tmp_path_factory.mktemp("git_repo")
        _init_repo(repo)
        # Create a Python file and commit it
        (repo / "service.py").write_text("x = 1\n")
        _git(["add", "service.py"], str(repo))
        _git(["commit", "-m", "add service"], str(repo))
        # Stage a modification
        (repo / "service.py").write_text("x = 2\n")
        _git(["add", "service.py"], str(repo))
        return repo

    def test_git_mode_returns_200(self, api_server, git_repo_with_changes):
        """16 — Omitting changed_files with a valid Git repo returns 200."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(git_repo_with_changes)},
        )
        assert status == 200
        assert body["success"] is True

    def test_git_mode_source_is_git(self, api_server, git_repo_with_changes):
        """17 — source='git' when changed_files is omitted."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(git_repo_with_changes)},
        )
        assert body["data"]["source"] == "git"

    def test_git_mode_git_changes_present(self, api_server, git_repo_with_changes):
        """19 — git_changes is a list of objects with path and status."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(git_repo_with_changes)},
        )
        git_changes = body["data"]["git_changes"]
        assert isinstance(git_changes, list)
        # At least one change expected (service.py staged)
        assert len(git_changes) >= 1
        for change in git_changes:
            assert "path" in change
            assert "status" in change
            assert change["path"].endswith(".py")

    def test_git_mode_changed_files_populated(self, api_server, git_repo_with_changes):
        """19b — changed_files in the response reflects git-detected files."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(git_repo_with_changes)},
        )
        assert isinstance(body["data"]["changed_files"], list)


class TestNoChanges:
    """20 — No changed Python files returns a clean success response."""

    @pytest.fixture(scope="class")
    def clean_git_repo(self, tmp_path_factory):
        """Create a clean Git repo with no uncommitted changes."""
        repo = tmp_path_factory.mktemp("clean_repo")
        _init_repo(repo)
        (repo / "app.py").write_text("pass\n")
        _git(["add", "app.py"], str(repo))
        _git(["commit", "-m", "add app.py"], str(repo))
        return repo

    def test_no_changes_returns_success(self, api_server, clean_git_repo):
        """20 — Clean repo returns success=True."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(clean_git_repo)},
        )
        assert status == 200
        assert body["success"] is True

    def test_no_changes_empty_lists(self, api_server, clean_git_repo):
        """20b — Clean repo returns empty changed_files and git_changes."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(clean_git_repo)},
        )
        d = body["data"]
        assert d["changed_files"] == []
        assert d["git_changes"] == []
        assert d["changed_modules"] == []

    def test_no_changes_risk_level_low(self, api_server, clean_git_repo):
        """20c — Clean repo has risk_level='LOW' and impact_score=0.0."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(clean_git_repo)},
        )
        d = body["data"]
        assert d["risk_level"] == "LOW"
        assert d["impact_score"] == 0.0
        assert d["affected_count"] == 0

    def test_no_changes_source_is_git(self, api_server, clean_git_repo):
        """20d — source='git' even when there are no changes."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(clean_git_repo)},
        )
        assert body["data"]["source"] == "git"


class TestInvalidGitRepo:
    """21 — Non-Git repository path → 400 NOT_A_GIT_REPO."""

    def test_non_git_repo_returns_400(self, api_server, tmp_path):
        """21 — A plain directory (not a Git repo) returns 400."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(tmp_path)},
        )
        assert status == 400
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_A_GIT_REPO"

    def test_fixture_dir_inside_git_repo_succeeds(self, api_server, tmp_path):
        """21b — Using a plain tmp_path (not a Git repo) → 400 NOT_A_GIT_REPO.

        Note: The fixture directory itself is inside the impactos Git repo,
        so it WILL succeed with Git auto-detection.  This test uses a plain
        temp directory instead.
        """
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(tmp_path)},
        )
        assert status == 400
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_A_GIT_REPO"


class TestDeletedFileBehavior:
    """22 — Deleted Python file — no crash, documented behavior."""

    @pytest.fixture(scope="class")
    def repo_with_deleted_file(self, tmp_path_factory):
        """Git repo where a Python file has been staged for deletion."""
        repo = tmp_path_factory.mktemp("deleted_file_repo")
        _init_repo(repo)
        (repo / "utils.py").write_text("def helper(): pass\n")
        _git(["add", "utils.py"], str(repo))
        _git(["commit", "-m", "add utils"], str(repo))
        # Stage the deletion
        _git(["rm", "utils.py"], str(repo))
        return repo

    def test_deleted_file_does_not_crash(self, api_server, repo_with_deleted_file):
        """22 — Analysis with a deleted file does not raise an exception."""
        host, port = api_server
        status, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(repo_with_deleted_file)},
        )
        # Must not be a 500 — either 200 (if module resolved) or 200
        # (empty result if not found in graph).  Never a hard crash.
        assert status in (200,)
        assert body["success"] is True

    def test_deleted_file_source_is_git(self, api_server, repo_with_deleted_file):
        """22b — Deleted file scenario still uses source='git'."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(repo_with_deleted_file)},
        )
        assert body["data"]["source"] == "git"

    def test_deleted_file_appears_in_git_changes(self, api_server, repo_with_deleted_file):
        """22c — The deleted file is visible in git_changes."""
        host, port = api_server
        _, body = _request(
            host, port, "POST", "/analyze",
            body={"repo_path": str(repo_with_deleted_file)},
        )
        git_changes = body["data"]["git_changes"]
        statuses = [c["status"] for c in git_changes]
        assert "deleted" in statuses

    def test_deleted_file_unit(self, tmp_path):
        """22d — GitChangeDetector unit test for deleted file status."""
        _init_repo(tmp_path)
        (tmp_path / "todelete.py").write_text("pass\n")
        _git(["add", "todelete.py"], str(tmp_path))
        _git(["commit", "-m", "add"], str(tmp_path))
        _git(["rm", "todelete.py"], str(tmp_path))

        changes = GitChangeDetector(tmp_path).detect_changes()
        assert any(c.path == "todelete.py" and c.status == "deleted" for c in changes)
