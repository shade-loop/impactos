# ImpactOS API Contract

This document describes the ImpactOS HTTP JSON API (Task 05).  
The API is a thin integration layer over the Tasks 01–04 intelligence pipeline.

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

**Successful response `200 OK`:**

```json
{
  "success": true,
  "data": {
    "changed_files": ["sample_app/utils.py"],
    "changed_modules": ["sample_app.utils"],
    "risk_level": "MEDIUM",
    "impact_score": 0.3,
    "affected_count": 2,
    "direct_count": 1,
    "indirect_count": 1,
    "max_depth": 2,
    "direct_affected": ["sample_app.service"],
    "indirect_affected": ["sample_app.main"],
    "all_affected": ["sample_app.main", "sample_app.service"],
    "evidence": [
      "2 modules are affected",
      "1 direct dependent exists",
      "1 indirect dependent exists",
      "Propagation reaches depth 2"
    ],
    "recommendations": [
      {
        "category": "REVIEW",
        "module": "sample_app.service",
        "priority": "HIGH",
        "action": "Review this module for breaking changes",
        "reason": "Directly depends on the changed module sample_app.utils."
      },
      {
        "category": "TEST",
        "module": "sample_app.service",
        "priority": "HIGH",
        "action": "Run or update tests for this module",
        "reason": "Directly depends on the changed module sample_app.utils."
      }
    ],
    "unknown_files": []
  }
}
```

**Response fields:**

| Field               | Type            | Description                                              |
|---------------------|-----------------|----------------------------------------------------------|
| `changed_files`     | array of string | Input file paths as provided.                            |
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

**Recommendation object:**

| Field      | Type   | Values                          |
|------------|--------|---------------------------------|
| `category` | string | `REVIEW` or `TEST`              |
| `module`   | string | Dotted module name              |
| `priority` | string | `HIGH`, `MEDIUM`, or `LOW`      |
| `action`   | string | Short imperative instruction    |
| `reason`   | string | Evidence-grounded explanation   |

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
| 400         | `INVALID_REQUEST`       | Missing/invalid `repo_path` or `changed_files`      |
| 400         | `MALFORMED_JSON`        | Request body is not valid JSON                      |
| 404         | `REPO_NOT_FOUND`        | `repo_path` does not exist on disk                  |
| 400         | `REPO_NOT_A_DIRECTORY`  | `repo_path` exists but is not a directory           |
| 405         | `METHOD_NOT_ALLOWED`    | Unsupported HTTP method                             |
| 404         | `NOT_FOUND`             | Unknown route                                       |
| 422         | `UNKNOWN_CHANGED_FILES` | None of `changed_files` resolved to a known module  |
| 500         | `ANALYSIS_ERROR`        | Unexpected internal error                           |

---

## Builder B Integration

Call the endpoint from your dashboard JavaScript:

```js
const response = await fetch("http://127.0.0.1:8000/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    repo_path: "/path/to/repo",
    changed_files: ["mypackage/utils.py"]
  })
});
const result = await response.json();

if (result.success) {
  const d = result.data;
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
| Risk Level badge   | `data.risk_level`        |
| Impact Score       | `data.impact_score`      |
| Affected Count     | `data.affected_count`    |
| Direct Affected    | `data.direct_affected`   |
| Indirect Affected  | `data.indirect_affected` |
| Evidence list      | `data.evidence`          |
| Recommendations    | `data.recommendations`   |
