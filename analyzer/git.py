"""
analyzer.git
~~~~~~~~~~~~

Git-based change detection for ImpactOS (Task 06).

Provides :class:`GitChangeDetector`, which inspects a real Git repository's
working-tree and staging-area state using ``git status --porcelain=v1`` and
returns a deterministic list of :class:`GitChange` objects limited to Python
files.

Architecture
------------
::

    GitChangeDetector
         ↓
    git status --porcelain=v1  (subprocess)
         ↓
    list[GitChange]            (path, status)
         ↓
    ImpactOS analysis pipeline

Design principles
-----------------
* Standard library only — no external dependencies.
* Deterministic: results are sorted by path.
* Never crashes with a raw subprocess exception; propagates clean errors.
* Only Python files are returned (non-``.py`` files are filtered out).

Deleted-file handling
---------------------
When Git reports a file as deleted it no longer exists on disk.
:class:`GitChangeDetector` faithfully reports it with ``status="deleted"``.
The caller (``api.py``) passes the path to :class:`~analyzer.change.ChangeAnalyzer`
which tries to resolve it to a module via the graph.  If the module was
previously indexed it will be found; otherwise it appears in ``unknown_modules``
and the analysis continues gracefully without crashing.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------


@dataclass
class GitChange:
    """A single changed file detected by Git.

    Attributes:
        path:   Repository-relative path, normalised to forward slashes.
        status: One of ``"added"``, ``"modified"``, ``"deleted"``,
                ``"renamed"``.
    """

    path: str
    status: str


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GitError(RuntimeError):
    """Raised when a Git command fails or the directory is not a repository."""


class NotAGitRepository(GitError):
    """Raised when the supplied path is not inside a Git repository."""


class RepositoryNotFound(GitError):
    """Raised when the supplied path does not exist on disk."""


# ---------------------------------------------------------------------------
# Ignore patterns
# ---------------------------------------------------------------------------

_IGNORED_PREFIXES = (
    ".git/",
    "__pycache__/",
    # Common virtual-environment directory names
    "venv/",
    ".venv/",
    "env/",
    ".env/",
    "virtualenv/",
    ".tox/",
    "site-packages/",
)


def _should_ignore(path: str) -> bool:
    """Return ``True`` when *path* should be excluded from results.

    Args:
        path: Repository-relative forward-slash path.

    Returns:
        ``True`` if the path is inside a directory that should be skipped.
    """
    for prefix in _IGNORED_PREFIXES:
        if path.startswith(prefix) or ("/" + prefix) in ("/" + path + "/"):
            return True
    # Also skip paths that contain any ignored segment anywhere.
    parts = path.split("/")
    ignore_dirs = {
        ".git", "__pycache__",
        "venv", ".venv", "env", ".env", "virtualenv", ".tox",
        "site-packages",
    }
    return any(p in ignore_dirs for p in parts[:-1])  # don't check the filename itself


# ---------------------------------------------------------------------------
# Status parsing
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "added",      # copied — treat as added
    "U": "modified",   # unmerged — treat as modified
    "?": "added",      # untracked — treat as added
    "!": None,         # ignored by Git — skip
    " ": None,         # field placeholder — handled contextually
}


def _unquote_git_path(raw: str) -> str:
    """Remove Git's C-style quoting from a path if present.

    Git quotes file paths that contain special characters (including spaces)
    by wrapping them in double-quotes and using C-escape sequences.  This
    function strips the outer quotes and unescapes the common sequences.

    Args:
        raw: The raw path token from porcelain output (may or may not be quoted).

    Returns:
        The unquoted, unescaped path string.
    """
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
        # Unescape common C escape sequences used by Git
        raw = (
            raw.replace('\\"', '"')
               .replace("\\\\", "\\")
               .replace("\\n", "\n")
               .replace("\\t", "\t")
        )
    return raw.replace("\\", "/")


def _parse_porcelain_line(line: str) -> list[GitChange]:
    """Parse a single ``git status --porcelain=v1`` output line.

    The porcelain v1 format is:
    ``XY PATH`` or ``XY ORIG -> PATH`` for renames.

    ``X`` is the staged status; ``Y`` is the unstaged (worktree) status.

    Git quotes file paths that contain special characters (spaces, etc.)
    using C-style quoting, e.g. ``?? "my file.py"``.  This is handled
    transparently by :func:`_unquote_git_path`.

    Args:
        line: A single line of porcelain output (no trailing newline).

    Returns:
        A list of :class:`GitChange` objects.  Usually one entry; zero for
        ignored lines.
    """
    if len(line) < 4:
        return []

    xy = line[:2]
    rest = line[3:]

    x = xy[0]  # staged status
    y = xy[1]  # worktree status

    # Untracked files
    if xy == "??":
        path = _unquote_git_path(rest)
        if not path.endswith(".py") or _should_ignore(path):
            return []
        return [GitChange(path=path, status="added")]

    # Renames: "R  old.py -> new.py" or "R  old.py\x00new.py" (null-sep; we
    # use --porcelain=v1 which uses " -> " for display).
    # git status --porcelain=v1 uses NUL separation for -z flag but without -z
    # it uses " -> " for renames in porcelain v1 output:
    # "R  old.py -> new.py"  — note: old -> new on same line
    if x == "R" or y == "R":
        # porcelain v1 without -z: "R  from -> to"
        if " -> " in rest:
            parts = rest.split(" -> ", 1)
            new_path = _unquote_git_path(parts[1])
        else:
            # Fallback: treat the whole thing as the new path
            new_path = _unquote_git_path(rest)
        changes: list[GitChange] = []
        if new_path.endswith(".py") and not _should_ignore(new_path):
            changes.append(GitChange(path=new_path, status="renamed"))
        return changes

    # Determine the effective status from X and Y.
    # If either X or Y is D → deleted.
    # If either X or Y is A → added.
    # Otherwise → modified.
    effective: str | None = None
    for char in (x, y):
        if char == "D":
            effective = "deleted"
            break
        if char == "A":
            effective = "added"
        elif char in ("M", "C", "U") and effective != "added":
            effective = "modified"

    if effective is None:
        return []

    path = _unquote_git_path(rest)
    if not path.endswith(".py") or _should_ignore(path):
        return []

    return [GitChange(path=path, status=effective)]


# ---------------------------------------------------------------------------
# GitChangeDetector
# ---------------------------------------------------------------------------


class GitChangeDetector:
    """Detect changed Python files in a Git repository.

    Args:
        repo_path: Path to the root of the Git repository (or any sub-path).

    Raises:
        :class:`RepositoryNotFound`: If *repo_path* does not exist.
        :class:`NotAGitRepository`: If *repo_path* is not inside a Git repo.
    """

    def __init__(self, repo_path: str | Path) -> None:
        self._path = Path(repo_path).resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_git_repository(self) -> bool:
        """Return ``True`` if ``_path`` is inside a Git repository.

        Does NOT raise; callers that want an exception should use
        :meth:`detect_changes` directly.
        """
        if not self._path.exists():
            return False
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(self._path),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except FileNotFoundError:
            # git not installed
            return False
        except OSError:
            return False

    def detect_changes(self) -> List[GitChange]:
        """Run ``git status --porcelain=v1`` and return changed Python files.

        Returns:
            Sorted list of :class:`GitChange` objects for Python files that
            are staged, unstaged, untracked, deleted, or renamed.

        Raises:
            :class:`RepositoryNotFound`: If the path does not exist.
            :class:`NotAGitRepository`: If the path is not a Git repo.
            :class:`GitError`: For other Git command failures.
        """
        if not self._path.exists():
            raise RepositoryNotFound(
                f"Repository path does not exist: {self._path}"
            )
        if not self._path.is_dir():
            raise RepositoryNotFound(
                f"Repository path is not a directory: {self._path}"
            )

        # Verify it is actually a Git repository.
        try:
            rev_parse = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(self._path),
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise GitError("git executable not found") from exc
        except OSError as exc:
            raise GitError(f"Failed to run git: {exc}") from exc

        if rev_parse.returncode != 0 or rev_parse.stdout.strip() != "true":
            raise NotAGitRepository(
                f"Not a Git repository: {self._path}"
            )

        # Run git status --porcelain=v1
        try:
            status_result = subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=str(self._path),
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise GitError(f"git status failed: {exc}") from exc

        if status_result.returncode != 0:
            raise GitError(
                f"git status exited with code {status_result.returncode}: "
                f"{status_result.stderr.strip()}"
            )

        changes: list[GitChange] = []
        for line in status_result.stdout.splitlines():
            changes.extend(_parse_porcelain_line(line))

        # Deduplicate by path (keep first occurrence).
        seen: set[str] = set()
        unique: list[GitChange] = []
        for change in changes:
            if change.path not in seen:
                seen.add(change.path)
                unique.append(change)

        # Sort deterministically by path.
        return sorted(unique, key=lambda c: c.path)
