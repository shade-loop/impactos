# Task 01 — Repository Analysis Foundation: Implementation Plan

## Top-Level Overview

**Goal:** Given a local Python repository, walk its source files, parse them with Python's `ast` module, extract meaningful symbols (modules, classes, functions, imports, calls), and build an in-memory directed dependency graph that can be queried for direct/indirect dependencies **and** direct/indirect dependents (reverse traversal for blast-radius analysis).

**Scope:** `analyzer/` package only. No frontend, no auth, no ML, no external databases.

**Approach:**
- Fill the existing empty stubs in `analyzer/` (`parser.py`, `graph.py`) and add `__init__.py` and `repo_analyzer.py`.
- Use only Python stdlib (`ast`, `os`, `pathlib`, `collections`, `typing`).
- Provide a small fixture repo under `tests/fixtures/` and a test suite at `tests/test_analyzer.py`.

**Files to create or modify:**

| File | Action |
|---|---|
| `analyzer/__init__.py` | Create — public package exports |
| `analyzer/parser.py` | Fill — AST parsing and symbol extraction |
| `analyzer/graph.py` | Fill — in-memory dependency graph |
| `analyzer/repo_analyzer.py` | Create — orchestrates walk + parse + graph build |
| `tests/__init__.py` | Create — make tests a package |
| `tests/fixtures/sample_app/__init__.py` | Create — fixture package root |
| `tests/fixtures/sample_app/models.py` | Create — defines classes |
| `tests/fixtures/sample_app/utils.py` | Create — utility functions, imports models |
| `tests/fixtures/sample_app/service.py` | Create — imports utils + models, defines functions |
| `tests/fixtures/sample_app/main.py` | Create — entry point, calls service functions |
| `tests/test_analyzer.py` | Create — full unit test suite |

---

## Sub-Task 1 — AST Parser (`analyzer/parser.py`)

**Intent:** Implement the core AST-based symbol extractor. This module is the engine that reads a single `.py` file and produces a structured list of extracted symbols (imports, classes, functions, function calls).

**Expected Outcomes:**
- `parse_file(path)` accepts an absolute path to a `.py` file and returns a `ParsedModule` dataclass.
- `ParsedModule` contains: `file_path`, `module_name`, `imports` (list of imported module names), `classes` (list of class names defined), `functions` (list of function names defined), `calls` (list of function names called within the module).
- Handles `import foo`, `from foo import bar`, nested functions, and method calls.
- Returns an empty-but-valid `ParsedModule` on syntax errors (with a logged warning).

**Todo List:**
1. Define `ParsedModule` dataclass with typed fields.
2. Implement an `ast.NodeVisitor` subclass (`_SymbolVisitor`) that collects imports, class defs, function defs, and call expressions.
3. Implement `parse_file(path: Path) -> ParsedModule` that reads, parses, visits, and returns the result.
4. Add module-level docstrings and type annotations throughout.

**Relevant Context:**
- File: `analyzer/parser.py` (currently empty stub)
- `ast.Import` → `.names[].name`
- `ast.ImportFrom` → `.module`
- `ast.ClassDef` → `.name`
- `ast.FunctionDef` / `ast.AsyncFunctionDef` → `.name`
- `ast.Call` → `.func` (can be `ast.Name` or `ast.Attribute`)

**Status:** `[ ] pending`

---

## Sub-Task 2 — In-Memory Dependency Graph (`analyzer/graph.py`)

**Intent:** Implement a lightweight directed graph that stores nodes and edges in plain Python data structures, supporting **both forward traversal** (what does this module depend on?) **and reverse traversal** (what depends on this module — the blast-radius direction). This is the queryable primitive that Task 02's impact engine will consume. No data is duplicated: the canonical edge list is stored once; adjacency and reverse-adjacency indices are derived from it at `add_edge` time.

**Expected Outcomes:**
- `GraphNode` dataclass with fields: `id` (str), `type` (str — `"module"`, `"class"`, `"function"`, `"external"`), `file_path` (str), `symbol_name` (str).
- `GraphEdge` dataclass with fields: `source` (str), `target` (str), `relationship` (str — `"imports"`, `"defines_class"`, `"defines_function"`, `"calls"`).
- `DependencyGraph` class with methods:
  - `add_node(node: GraphNode) -> None`
  - `add_edge(edge: GraphEdge) -> None`
  - `get_nodes() -> list[GraphNode]`
  - `get_edges() -> list[GraphEdge]`
  - `get_node(node_id: str) -> GraphNode | None`
  - `find_direct_dependencies(node_id: str) -> list[GraphNode]` — outbound: what `node_id` imports/uses
  - `find_indirect_dependencies(node_id: str) -> list[GraphNode]` — transitive outbound BFS
  - `find_direct_dependents(node_id: str) -> list[GraphNode]` — inbound: what imports/uses `node_id`
  - `find_indirect_dependents(node_id: str) -> list[GraphNode]` — transitive inbound BFS (blast radius)
- **Internal storage — no duplication:**
  - `_nodes: dict[str, GraphNode]` — node registry
  - `_edges: list[GraphEdge]` — canonical edge list (single source of truth)
  - `_adj: dict[str, list[str]]` — forward adjacency index (source → list of targets), built at `add_edge` time
  - `_radj: dict[str, list[str]]` — reverse adjacency index (target → list of sources), built at `add_edge` time
- BFS for both `find_indirect_dependencies` and `find_indirect_dependents` uses `_adj` and `_radj` respectively — O(V+E), no edge list re-scanning.
- Duplicate node IDs are idempotently handled (first write wins).
- Duplicate edges (same source/target/relationship) are deduplicated at `add_edge` time.

**Todo List:**
1. Define `GraphNode` and `GraphEdge` dataclasses.
2. Implement `DependencyGraph.__init__` initialising `_nodes`, `_edges`, `_adj`, `_radj`.
3. Implement `add_node`, `get_nodes`, `get_edges`, `get_node`.
4. Implement `add_edge` — append to `_edges`, update `_adj[source]` and `_radj[target]`.
5. Implement `find_direct_dependencies` (single hop via `_adj`).
6. Implement `find_indirect_dependencies` (BFS via `_adj`).
7. Implement `find_direct_dependents` (single hop via `_radj`).
8. Implement `find_indirect_dependents` (BFS via `_radj` — blast-radius traversal).
9. Add docstrings and type annotations throughout.

**Relevant Context:**
- File: `analyzer/graph.py` (currently empty stub)
- No external libraries. Pure Python `dict`, `list`, `collections.deque` for BFS.
- `_adj` and `_radj` are **indices** — they hold node ID strings only, not copies of nodes or edges.

**Status:** `[ ] pending`

---

## Sub-Task 3 — Repository Analyzer (`analyzer/repo_analyzer.py`)

**Intent:** Orchestrate the full pipeline: walk a repository directory, invoke the parser on each `.py` file, translate `ParsedModule` results into graph nodes and edges, and return a populated `DependencyGraph`.

**Expected Outcomes:**
- `RepoAnalyzer` class with:
  - `__init__(self, repo_path: str | Path)` — stores root path.
  - `analyze() -> DependencyGraph` — walks, parses, builds and returns the graph.
- Node ID scheme: `<relative_module_path>` for modules (e.g. `sample_app.utils`), `<module>.<ClassName>` for classes, `<module>.<func_name>` for functions.
- Edges created:
  - `module → imported_module` with relationship `"imports"` for each import.
  - `module → class` with relationship `"defines_class"` for each class in the file.
  - `module → function` with relationship `"defines_function"` for each function in the file.
  - `module → called_name` with relationship `"calls"` for each call expression (target node may be external/unresolved — add a stub node with `type="external"`).
- Skips non-`.py` files and `__pycache__` directories silently.

**Todo List:**
1. Implement `_walk_python_files(root: Path) -> list[Path]` helper that yields all `.py` files recursively, excluding `__pycache__`.
2. Implement `_module_name_from_path(root: Path, file: Path) -> str` helper that converts a file path to a dotted module name.
3. Implement `analyze()` — iterate files, call `parse_file`, create nodes and edges, populate graph, return graph.
4. Add docstrings and type annotations throughout.

**Relevant Context:**
- File: `analyzer/repo_analyzer.py` (new file)
- Depends on `analyzer/parser.py` (`parse_file`, `ParsedModule`)
- Depends on `analyzer/graph.py` (`DependencyGraph`, `GraphNode`, `GraphEdge`)

**Status:** `[ ] pending`

---

## Sub-Task 4 — Package Init and Public API (`analyzer/__init__.py`)

**Intent:** Expose a clean public API from the `analyzer` package so callers can do `from analyzer import RepoAnalyzer, DependencyGraph`.

**Expected Outcomes:**
- `analyzer/__init__.py` exports: `RepoAnalyzer`, `DependencyGraph`, `GraphNode`, `GraphEdge`, `ParsedModule`, `parse_file`.

**Todo List:**
1. Create `analyzer/__init__.py` with explicit `__all__` and re-exports.

**Relevant Context:**
- File: `analyzer/__init__.py` (new file)

**Status:** `[ ] pending`

---

## Sub-Task 5 — Test Fixtures (`tests/fixtures/sample_app/`)

**Intent:** Create a self-contained mini Python repository under `tests/fixtures/` that exercises all the graph construction paths: inter-module imports, class definitions, function definitions, and cross-module function calls.

**Expected Outcomes:**
- Four Python files with realistic but minimal content:
  - `models.py` — defines two classes (`User`, `Product`), no imports from sibling modules.
  - `utils.py` — imports from `models`, defines two utility functions.
  - `service.py` — imports from `utils` and `models`, defines a service function that calls utility functions.
  - `main.py` — imports from `service`, calls the service function.
- Enough cross-file relationships to test direct and indirect dependency traversal (e.g. `main` → `service` → `utils` → `models`).

**Todo List:**
1. Create `tests/__init__.py`.
2. Create `tests/fixtures/sample_app/__init__.py`.
3. Create `tests/fixtures/sample_app/models.py`.
4. Create `tests/fixtures/sample_app/utils.py`.
5. Create `tests/fixtures/sample_app/service.py`.
6. Create `tests/fixtures/sample_app/main.py`.

**Relevant Context:**
- Fixtures are consumed by `tests/test_analyzer.py`. They must be stable and deterministic.

**Status:** `[ ] pending`

---

## Sub-Task 6 — Unit Tests (`tests/test_analyzer.py`)

**Intent:** Verify every layer of the system against the fixture repository. Tests are the proof that the implementation is correct and the system is explainable.

**Expected Outcomes:**
Tests pass covering:
1. **Repository discovery** — `RepoAnalyzer` finds exactly the expected set of `.py` files in the fixture repo.
2. **AST parsing** — `parse_file` on `models.py` returns correct class names; `parse_file` on `utils.py` returns correct import and function names.
3. **Import extraction** — imports from `service.py` include `utils` and `models`.
4. **Graph construction** — after `analyze()`, the graph contains nodes for each module, class, function, and edges of the correct relationship types.
5. **Direct dependency lookup** — `find_direct_dependencies` on the `main` module node returns the `service` module node.
6. **Indirect dependency lookup** — `find_indirect_dependencies` on the `main` module node returns `service`, `utils`, and `models` nodes (transitive closure).
7. **Direct dependent lookup** — `find_direct_dependents` on the `utils` module node returns the `service` module node.
8. **Indirect dependent lookup (blast radius)** — `find_indirect_dependents` on the `utils` module node returns both `service` and `main` nodes (everything that transitively depends on `utils`).

**Todo List:**
1. Create `tests/test_analyzer.py` with a `pytest` test suite.
2. Use a `@pytest.fixture` that runs `RepoAnalyzer` on `tests/fixtures/sample_app/` once per session.
3. Write one test function per coverage item listed above (8 tests total).
4. Assert on node IDs, node types, and edge relationship strings — no magic numbers.

**Relevant Context:**
- File: `tests/test_analyzer.py` (new file)
- Fixture path: `tests/fixtures/sample_app/`
- Uses `pytest` (add to requirements if not present).

**Status:** `[ ] pending`

---

## Sub-Task 7 — Project Setup (`requirements.txt` / `pyproject.toml`)

**Intent:** Ensure the project has a minimal runnable Python environment definition so tests can be executed.

**Expected Outcomes:**
- A `requirements.txt` (or `pyproject.toml`) at `impactos/` level listing `pytest` as a dev dependency.
- No other runtime dependencies (the analyzer uses only stdlib).

**Todo List:**
1. Create `impactos/requirements.txt` with `pytest>=7.0`.

**Relevant Context:**
- No existing requirements file found in the project.

**Status:** `[ ] pending`

---

## Implementation Order

Sub-tasks should be implemented in this sequence, as later tasks depend on earlier ones:

1. Sub-Task 1 — Parser (foundation)
2. Sub-Task 2 — Graph (foundation)
3. Sub-Task 3 — RepoAnalyzer (uses 1 + 2)
4. Sub-Task 4 — Package init (uses 1 + 2 + 3)
5. Sub-Task 5 — Fixtures (independent, but needed before tests)
6. Sub-Task 6 — Tests (needs all of the above)
7. Sub-Task 7 — Requirements (can be done anytime)
