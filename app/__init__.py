"""Banking Agentic Chat application package.

The public package surface intentionally exposes an application factory rather than
importing the FastAPI application at package import time. This keeps command-line
utilities, tests, and MCP integrations from creating logging/application side
effects merely by importing :mod:`app`.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["create_app", "__version__"]
__version__ = "1.0.0"


def create_app() -> "FastAPI":
    """Return the configured FastAPI application.

    The import is deliberately lazy: runtime dependencies are needed only when a
    web application is actually created. Uvicorn continues to use ``app.main:app``
    while ASGI factories and integration tests may use this supported entry point.
    """
    from .main import app
    return app
