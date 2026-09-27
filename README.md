# ImpactOS

**Developer Impact Intelligence**

ImpactOS helps developers understand the potential impact of code changes before they become production problems.

It analyzes a Python repository, builds dependency relationships, identifies directly and indirectly affected modules, calculates change risk, and provides evidence-based recommendations for review and investigation.

---

## Overview

A small code change can have a much larger blast radius than expected.

Traditional development workflows often answer:

> "Did the tests pass?"

ImpactOS asks an additional question:

> "What else could this change affect?"

The system combines repository analysis, dependency traversal, risk assessment, Git change detection, and a web-based dashboard to make code-change impact easier to understand.

## Core Workflow

```
Repository
    │
    ▼
Repository Analysis
    │
    ▼
Dependency Graph
    │
    ▼
Impact / Blast Radius
    │
    ▼
Risk Assessment
    │
    ├── Evidence
    ├── Recommendations
    └── Affected Modules
    │
    ▼
Backend API
    │
    ▼
React Dashboard
```

## Features

### Repository Analysis
- Discovers and analyzes Python source files
- Identifies modules and their relationships
- Builds dependency information for impact traversal
- Handles unknown or unsupported targets safely

### Dependency & Impact Analysis

ImpactOS distinguishes between:

- **Direct impact** — modules directly affected by a change
- **Indirect impact** — downstream modules affected through dependency chains
- **Propagation depth** — how far the change travels through the dependency graph

### Risk Assessment

The analysis engine produces:

- Risk level
- Impact score
- Changed modules
- Directly affected modules
- Indirectly affected modules
- Maximum propagation depth
- Supporting evidence
- Investigation recommendations

### Git Integration

ImpactOS can detect changes directly from a Git repository.

It supports:

- Modified files
- Staged files
- Unstaged files
- Untracked files
- Deleted files
- Renamed files
- Python-file filtering
- Git C-style filename quoting
- Ignored-directory handling
- Deterministic change ordering

### Investigation Guidance

ImpactOS goes beyond a risk score by providing recommended investigation steps, including:

- Inspecting affected modules
- Reviewing dependency relationships
- Running relevant integration tests
- Checking downstream modules for correlated issues

### Web Dashboard

The React/Vite frontend provides:

- Repository overview
- Dependency graph
- Change impact analysis
- Risk visualization
- Affected-module information
- Investigation recommendations
- Backend analysis results
- Repository-aware investigation views

## Architecture

```
┌───────────────────────────────────────────────┐
│                 React / Vite                   │
│                  Frontend                       │
│                                                   │
│  Dashboard · Graph · Risk · Investigation        │
└───────────────────────┬───────────────────────┘
                         │
                         │ HTTP API
                         ▼
┌───────────────────────────────────────────────┐
│                 Python Backend                  │
│                                                   │
│  API · Analyzer · Risk Engine · Git Detector     │
└───────────────────────┬───────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────┐
│               Repository Analysis                │
│                                                   │
│  Python Modules · Dependencies · Git Changes     │
└───────────────────────────────────────────────┘
```

## Project Structure

```
impactos/
├── backend/
│   ├── app/
│   │   └── main.py
│   ├── analyzer/
│   │   ├── api.py
│   │   └── ...
│   └── tests/
│       ├── fixtures/
│       └── test_*.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── data/
│   │   └── App.tsx
│   ├── package.json
│   └── ...
│
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.x
- Node.js and npm
- Git

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite development server will normally be available at:

```
http://localhost:5173
```

### Production Build

```bash
npm run build
```

The production build is generated in:

```
frontend/dist/
```

### Backend

From the project environment, install the backend dependencies and start the configured Python API application.

The backend provides the repository analysis functionality consumed by the frontend.

## Testing

Run the backend test suite with:

```bash
pytest tests/
```

Current validation:

```
208 passed
0 failed
```

The tests cover repository analysis, dependency traversal, risk calculations, serialization, CLI behavior, API behavior, Git integration, edge cases, and integration scenarios.

The frontend production build has also been validated successfully with TypeScript and Vite.

## API

The backend exposes repository analysis through an API endpoint.

Analysis accepts repository information and changed files and returns structured results including risk, impact, affected modules, evidence, and recommendations.

Example:

```json
{
  "risk_level": "MEDIUM",
  "impact_score": 0.3,
  "direct_affected": 1,
  "indirect_affected": 1
}
```

## Git Change Detection

ImpactOS includes a `GitChangeDetector` for identifying repository changes.

It uses:

```bash
git status --porcelain=v1
```

The Git integration handles:

- Modified files
- Staged and unstaged changes
- Untracked files
- Deleted files
- Renamed files
- Python-file filtering
- Git C-style quoting
- Ignored directories
- Deterministic sorting

Typed exceptions include:

- `RepositoryNotFound`
- `NotAGitRepository`
- `GitError`

## Live Demo

The frontend is deployed at:

**https://impactos-five.vercel.app**

The backend is deployed separately and provides the analysis API.

> **Note:** Repository analysis and the Backend Analyzer are connected to the Python analysis engine. The incident-investigation section contains clearly labelled demonstration data because a production incident-management, APM, deployment, or telemetry system is not connected in the current version.

## IBM Bob

IBM Bob was used throughout the development of ImpactOS as a coding, debugging, testing, integration, and review assistant.

Bob assisted with:

- Python repository-analysis implementation
- Dependency and impact traversal
- Risk and recommendation logic
- JSON serialization and CLI functionality
- Backend API implementation and debugging
- React/Vite frontend integration
- Git change detection
- Frontend/backend integration issues
- Demo-data and live-data auditing
- Automated test development and debugging
- Build and integration validation

Developers remained responsible for requirements, architecture, reviewing changes, running tests, and validating the final system.

## Technology Stack

### Frontend
- React
- TypeScript
- Vite

### Backend
- Python
- REST API
- Repository analysis engine
- Git integration

### Development
- Git
- GitHub
- Pytest
- TypeScript
- Vite
- IBM Bob
- watsonx

### Deployment
- **Vercel** — Frontend
- **Render** — Backend

## Design Principles

**Evidence over assumptions**
ImpactOS distinguishes repository-derived analysis from information that requires external operational systems.

**Explainable impact**
The system provides affected modules, dependency relationships, evidence, and recommendations alongside the risk assessment.

**Change-aware analysis**
Git integration allows analysis of actual repository changes rather than relying exclusively on manually supplied files.

**Developer-first workflow**
ImpactOS is designed to help developers understand the potential consequences of a change without manually tracing the entire dependency graph.

## Current Limitations

The current version does not directly integrate with:

- Production APM systems
- Deployment platforms
- Incident-management systems
- Service-mesh telemetry
- Real-time production monitoring

The incident investigation interface therefore demonstrates how these signals could be incorporated, while repository-derived analysis is provided by the actual backend analysis engine.

## Future Directions

Potential extensions include:

- GitHub/GitLab repository integration
- Pull-request impact analysis
- APM and telemetry integration
- Deployment correlation
- Incident-management integrations
- Historical change-risk tracking
- Automated regression-test selection
- Service-level dependency mapping
- CI/CD integration
- Repository-wide impact visualization

## Why ImpactOS?

Software changes rarely stay isolated.

ImpactOS provides a developer-focused workflow that moves from:

> "What did I change?"

to:

> "What could this change affect?"

and finally:

> "What should I investigate next?"

**ImpactOS** — understand the blast radius before it becomes a production problem.