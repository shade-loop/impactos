# ImpactOS API Contract

This document describes the ImpactOS HTTP JSON API (Tasks 05–06).  
The API is a thin integration layer over the Tasks 01–06 intelligence pipeline.

---

## Starting the API

```bash
# Default: 127.0.0.1:8000
python -m analyzer.api

# Custom host/port
python -m analyzer.api --host 0.0.0.0 --port 9000
```

> **Note:** Run the command from the `impactos/` directory, or ensure the
> `impactos/` directory is on `PYTHONPATH`.

Default base URL: `http://127.0.0.1:8000`

---

## CORS

Development CORS is enabled for **all origins** (`Access-Control-Allow-Origin: *`).  
No authentication is required. This is intentional for local hackathon use.

---

## Endpoints

### GET /health

Liveness check. Returns immediately without touching the analysis pipeline.

**Response `200 OK`:**

```json
{
  "status": "ok",
  "service": "ImpactOS"
}
```

---

### POST /analyze

Run the full dependency-change-risk analysis pipeline.

The endpoint supports **two modes**:

| Mode      | `changed_files` | Description                              |
|-----------|-----------------|------------------------------------------|
| Manual    | Supplied        | Analyse the explicitly provided files.   |
| Automatic | Omitted         | Auto-detect changes from Git working tree (Task 06). |

---

#### Manual mode

Analyse specific changed files.

**Request headers:**

```
Content-Type: application/json
```

**Request body:**

```json
{
  "repo_path": "tests/fixtures/sample_app",
  "changed_files": [
    "sample_app/utils.py"
  ]
}
```

| Field           | Type            | Required | Description                                           |
|-----------------|-----------------|----------|-------------------------------------------------------|
| `repo_path`     | string          | ✔        | Path to the repository root (relative or absolute).   |
| `changed_files` | array of string | ✔        | One or more changed file paths to analyse.            |

---

#### Automatic mode (Task 06)

Omit `changed_files` to trigger automatic Git change detection.  
ImpactOS will run `git status` on the repository and detect all changed
Python files (staged, unstaged, added, deleted, renamed, untracked).

**Request body:**

```json
{
  "repo_path": "/path/to/git/repository"
}
```

| Field       | Type   | Required | Description                                              |
|-------------|--------|----------|----------------------------------------------------------|
| `repo_path` | string | ✔        | Path to the **Git** repository root.                     |

> **Requirement:** `repo_path` must be a Git repository. A plain directory
> that is not a Git repo will return `400 NOT_A_GIT_REPO`.

---

#### Successful response `200 OK`

```json
{
  "success": true,
  "data": {
    "source": "git",
    "git_changes": [
      {"path": "myapp/service.py", "status": "modified"}
    ],
    "changed_files": ["myapp/service.py"],
    "changed_modules": ["myapp.service"],
    "risk_level": "MEDIUM",
    "impact_score": 0.3,
    "affected_count": 2,
    "direct_count": 1,
    "indirect_count": 1,
    "max_depth": 2,
    "direct_affected": ["myapp.api"],
    "indirect_affected": ["myapp.main"],
    "all_affected": ["myapp.api", "myapp.main"],
    "evidence": [
      "2 modules are affected",
      "1 direct dependent exists"
    ],
    "recommendations": [
      {
        "category": "REVIEW",
        "module": "myapp.api",
        "priority": "HIGH",
        "action": "Review this module for breaking changes",
        "reason": "Directly depends on the changed module myapp.service."
      }
    ],
    "unknown_files": []
  }
}
```

**Response fields:**

| Field               | Type            | Description                                              |
|---------------------|-----------------|----------------------------------------------------------|
| `source`            | string          | `"git"` (automatic mode) or `"manual"` (explicit files). |
| `git_changes`       | array of object | Git-detected changes. Empty `[]` for manual mode.        |
| `changed_files`     | array of string | Input file paths as provided / detected.                 |
| `changed_modules`   | array of string | Resolved dotted module names.                            |
| `risk_level`        | string          | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.                  |
| `impact_score`      | float           | Dependency-based impact score in `[0.0, 1.0]`.           |
| `affected_count`    | integer         | Total number of affected modules.                        |
| `direct_count`      | integer         | Number of directly affected modules.                     |
| `indirect_count`    | integer         | Number of indirectly affected modules.                   |
| `max_depth`         | integer         | Longest dependency chain depth.                          |
| `direct_affected`   | array of string | Modules that directly depend on a changed module.        |
| `indirect_affected` | array of string | Modules transitively affected.                           |
| `all_affected`      | array of string | Union of direct + indirect.                              |
| `evidence`          | array of string | Human-readable grounded evidence statements.             |
| `recommendations`   | array of object | Actionable recommendations (see below).                  |
| `unknown_files`     | array of string | Inputs not resolved to a known module (informational).   |

**`git_changes` object:**

| Field    | Type   | Values                                        |
|----------|--------|-----------------------------------------------|
| `path`   | string | Repository-relative path with forward slashes |
| `status` | string | `added`, `modified`, `deleted`, `renamed`     |

**Recommendation object:**

| Field      | Type   | Values                          |
|------------|--------|---------------------------------|
| `category` | string | `REVIEW` or `TEST`              |
| `module`   | string | Dotted module name              |
| `priority` | string | `HIGH`, `MEDIUM`, or `LOW`      |
| `action`   | string | Short imperative instruction    |
| `reason`   | string | Evidence-grounded explanation   |

---

#### No-change case

When Git detects no changed Python files, the API returns a clean success response:

```json
{
  "success": true,
  "data": {
    "source": "git",
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
    "unknown_files": []
  }
}
```

---

## Error Responses

All errors return JSON with `"success": false`.

**Shape:**

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "repo_path is required"
  }
}
```

**Error codes:**

| HTTP Status | Code                    | Cause                                               |
|-------------|-------------------------|-----------------------------------------------------|
| 400         | `INVALID_REQUEST`       | Missing/invalid `repo_path` or malformed `changed_files` |
| 400         | `MALFORMED_JSON`        | Request body is not valid JSON                      |
| 400         | `NOT_A_GIT_REPO`        | `repo_path` is not a Git repository (automatic mode) |
| 400         | `REPO_NOT_A_DIRECTORY`  | `repo_path` exists but is not a directory           |
| 404         | `REPO_NOT_FOUND`        | `repo_path` does not exist on disk                  |
| 405         | `METHOD_NOT_ALLOWED`    | Unsupported HTTP method                             |
| 404         | `NOT_FOUND`             | Unknown route                                       |
| 422         | `UNKNOWN_CHANGED_FILES` | None of `changed_files` resolved to a known module (manual mode) |
| 500         | `GIT_ERROR`             | Unexpected Git command failure                      |
| 500         | `ANALYSIS_ERROR`        | Unexpected internal analysis error                  |

---

## Real Git workflow

```
Developer edits service.py
        ↓
Git working tree changes
        ↓
GitChangeDetector
 (git status --porcelain=v1)
        ↓
Python-only filter + sort
        ↓
DependencyGraph
 (AST-based module graph)
        ↓
Blast-radius analysis
        ↓
Risk assessment
        ↓
Recommended tests/review
        ↓
Builder B dashboard
```

### Example — Git auto-detect call

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"repo_path": "/path/to/my/git/project"}'
```

### Example — Manual call (unchanged from Task 05)

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_path": "/path/to/project",
    "changed_files": ["mypackage/service.py"]
  }'
```

---

## Deleted-file handling

When Git reports a Python file as deleted it no longer exists on disk and
cannot be AST-parsed. ImpactOS handles this as follows:

1. `GitChangeDetector` faithfully reports the file with `status="deleted"`.
2. The deleted path is passed to `ChangeAnalyzer`.
3. `ChangeAnalyzer` attempts to resolve the path to a module node that was
   previously indexed in the dependency graph.
4. If the module is found in the graph, downstream dependents are identified
   and the analysis proceeds normally.
5. If the module is **not** found (e.g., it was never committed as Python
   code), it appears in `unknown_files` and the analysis continues for any
   other changed modules.

**Limitation:** The graph is built from currently existing files. If the only
changed file is the deleted one and it has never been indexed in the graph,
`unknown_files` will contain it but the blast-radius analysis will be empty.
This is expected and safe — the API returns `200` with an empty affected set
rather than crashing.

---

## CLI — git-status command (Task 06)

```bash
python -m analyzer.cli git-status <repo_path>
```

**Example output:**

```
Detected changes:

  M  analyzer/foo.py
  A  analyzer/bar.py
  D  analyzer/old.py
  R  analyzer/renamed.py
```

| Symbol | Status   |
|--------|----------|
| `M`    | modified |
| `A`    | added    |
| `D`    | deleted  |
| `R`    | renamed  |

---

## Builder B Integration

Call the endpoint from your dashboard JavaScript:

```js
const response = await fetch("http://127.0.0.1:8000/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  // Automatic Git mode — omit changed_files:
  body: JSON.stringify({ repo_path: "/path/to/repo" })
});
const result = await response.json();

if (result.success) {
  const d = result.data;
  // d.source          — "git" or "manual"
  // d.git_changes     — [{path, status}, ...]
  // d.risk_level, d.impact_score, d.affected_count
  // d.direct_affected, d.indirect_affected
  // d.evidence, d.recommendations
} else {
  console.error(result.error.code, result.error.message);
}
```

Fields to render in the dashboard:

| UI Element         | Field                    |
|--------------------|--------------------------|
| Source badge       | `data.source`            |
| Git changes list   | `data.git_changes`       |
| Risk Level badge   | `data.risk_level`        |
| Impact Score       | `data.impact_score`      |
| Affected Count     | `data.affected_count`    |
| Direct Affected    | `data.direct_affected`   |
| Indirect Affected  | `data.indirect_affected` |
| Evidence list      | `data.evidence`          |
| Recommendations    | `data.recommendations`   |
