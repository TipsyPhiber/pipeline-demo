"""A deliberately tiny FastAPI service.

The application is intentionally minimal: it exists to give the CI/CD pipeline
something real to test, build, scan, and deploy. The interesting work is the
pipeline and the security posture, not the business logic.

Security posture baked into the app itself:
  * All input is validated and bounded (Pydantic constraints + a payload cap).
  * The "action" parameter is default-deny via an allow-list, never free-form.
  * Request bodies are never logged, so user input can't leak into logs.
"""

from enum import Enum

from fastapi import FastAPI
from pydantic import BaseModel, Field

# Cap the request body to bound memory use and reject oversized payloads early.
MAX_BODY_BYTES = 4096
MAX_TEXT_LEN = 1000

app = FastAPI(title="pipeline-demo", version="0.1.0")


class Action(str, Enum):
    """Allow-list of supported transforms. Anything else is rejected by the
    schema before it ever reaches the handler (default-deny)."""

    upper = "upper"
    lower = "lower"
    reverse = "reverse"


class TransformRequest(BaseModel):
    # Bounded, required field. Pydantic rejects missing/oversized/empty values.
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LEN)
    action: Action


class TransformResponse(BaseModel):
    result: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe: the process is up and serving."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    """Readiness probe: ready to accept traffic. No external deps, so this is
    static — but the separate endpoint keeps the orchestration contract honest."""
    return {"status": "ready"}


@app.post("/transform", response_model=TransformResponse)
def transform(req: TransformRequest) -> TransformResponse:
    """Apply an allow-listed transform to bounded input.

    Note: operates on the validated model only; req.text is never logged.
    """
    if req.action is Action.upper:
        result = req.text.upper()
    elif req.action is Action.lower:
        result = req.text.lower()
    else:  # Action.reverse — exhaustive over the allow-list
        result = req.text[::-1]
    return TransformResponse(result=result)
