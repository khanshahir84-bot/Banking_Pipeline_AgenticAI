"""Agent layer public contracts.

Only the coordinator is intended to be called by the HTTP boundary. Specialist
agents are exported for integration tests and controlled workflow extensions;
they should not be exposed directly to untrusted callers because the coordinator
owns intent allow-listing, authorization, PII handling, and trace logging.
"""
from .coordinator import CoordinatorAgent, WorkflowResult, classify
from .specialists import AccountsAgent, ServiceAgent, TransactionAgent

__all__ = [
    "AccountsAgent",
    "CoordinatorAgent",
    "ServiceAgent",
    "TransactionAgent",
    "WorkflowResult",
    "classify",
]
