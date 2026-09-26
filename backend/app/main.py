import sys
import os

# Ensure the repo root (parent of backend/app) is on the path so that
# `from analyzer.X import Y` resolves when running from any working directory.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from analyzer.impact import compute_impact, compute_git_impact
from analyzer.risk import assess_risk

app = FastAPI(title="ImpactOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_path: str
    changed_files: Optional[list[str]] = None


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        if request.changed_files:
            result = compute_impact(request.repo_path, request.changed_files)
            result["source"] = "manual"
            result["git_changes"] = []
        else:
            result = compute_git_impact(request.repo_path)

        result = assess_risk(result)
        return {"success": True, "data": result}

    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
