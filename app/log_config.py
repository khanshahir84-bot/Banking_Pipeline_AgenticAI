"""Structured, correlation-aware logs for every agentic workflow hop."""
import contextvars, json, logging, sys, time, uuid
from typing import Any
trace_id_var = contextvars.ContextVar("trace_id", default="-")

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {"timestamp": self.formatTime(record), "level": record.levelname,
            "logger": record.name, "message": record.getMessage(), "trace_id": trace_id_var.get()}
        if hasattr(record, "event"): event.update(record.event)
        return json.dumps(event, default=str)

def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout); handler.setFormatter(JsonFormatter())
    root = logging.getLogger(); root.handlers = [handler]; root.setLevel(level)

def log_event(logger: logging.Logger, message: str, **event: Any) -> None:
    logger.info(message, extra={"event": event})

def new_trace_id() -> str: return uuid.uuid4().hex

def timed(operation: str):
    def wrap(fn):
        async def inner(*args, **kwargs):
            start = time.monotonic()
            try: return await fn(*args, **kwargs)
            finally: log_event(logging.getLogger("timing"), "operation_complete", operation=operation, duration_ms=round((time.monotonic()-start)*1000, 2))
        return inner
    return wrap
