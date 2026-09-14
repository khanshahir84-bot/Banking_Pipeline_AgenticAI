"""FastAPI boundary: authentication, PII redaction, session ownership, and telemetry."""
import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# `python app/main.py` puts the app directory first on sys.path. Add the
# repository root so package imports resolve exactly as they do under Uvicorn.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agents.coordinator import CoordinatorAgent
from app.config import settings
from app.observability import configure_logging, log_event, new_trace_id, trace_id_var
from app.pii import redact
from app.security import authenticated_user
from app.store import add_message, audit_workflow, ensure_session, history
from app.ui import chat_page

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    trace_id: str
    intent: str
    response: str
    tool: str | None


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    log_event(logger, "application_started", auth_mode=settings.auth_mode, llm_configured=bool(settings.llm_api_key))
    yield
    log_event(logger, "application_stopped")


app = FastAPI(title="Banking Agentic Chat", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def observability(request: Request, call_next):
    token = trace_id_var.set(request.headers.get("x-trace-id", new_trace_id()))
    start = time.monotonic()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["x-trace-id"] = trace_id_var.get()
        return response
    finally:
        log_event(logger, "http_request_complete", path=request.url.path, method=request.method, status_code=status_code, duration_ms=round((time.monotonic() - start) * 1000, 2))
        trace_id_var.reset(token)


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "trace_id": trace_id_var.get()})


@app.get("/", include_in_schema=False)
def chat_ui():
    return chat_page()


@app.get("/health")
def health():
    return {"status": "ok", "llm_configured": bool(settings.llm_api_key), "auth_mode": settings.auth_mode}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    user = authenticated_user(request)
    try:
        ensure_session(payload.session_id, user["sub"])
    except PermissionError as exc:
        raise HTTPException(403, "Session is not owned by authenticated user") from exc

    safe_message = redact(payload.message)
    prior_history = history(payload.session_id)
    add_message(payload.session_id, "user", safe_message)
    try:
        outcome = await CoordinatorAgent().run(safe_message, user, prior_history)
    except HTTPException:
        audit_workflow(trace_id_var.get(), user["sub"], None, None, "denied")
        raise
    except Exception:
        logger.exception("workflow_failed")
        audit_workflow(trace_id_var.get(), user["sub"], None, None, "failed")
        raise HTTPException(502, "Unable to complete banking workflow")

    safe_answer = redact(outcome.answer)
    add_message(payload.session_id, "assistant", safe_answer)
    audit_workflow(trace_id_var.get(), user["sub"], outcome.intent, outcome.tool, "completed")
    return ChatResponse(trace_id=trace_id_var.get(), intent=outcome.intent, response=safe_answer, tool=outcome.tool)


if __name__ == "__main__":
    # Direct execution is supported for local development; production should run
    # the container command or `uvicorn app.main:app`.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
