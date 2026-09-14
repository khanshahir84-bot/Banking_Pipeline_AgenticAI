"""Safe coordinator for intent routing, authorization, tool dispatch, and response synthesis.

The LLM receives redacted, approved tool output only; it never selects tools,
constructs tool arguments, or sees raw customer messages/history.
"""
import json
import logging
from dataclasses import dataclass

from ..llm import LLMProviderError, ThirdPartyLLM
from ..logging import log_event, timed
from ..pii import redact
from ..security import require_scope
from .specialists import AccountsAgent, ServiceAgent, TransactionAgent

logger = logging.getLogger(__name__)
INTENTS = {
    "balance": ("accounts:read", AccountsAgent()),
    "transaction": ("transactions:read", TransactionAgent()),
    "statement": ("transactions:read", TransactionAgent()),
    "address_change": ("service:write", ServiceAgent()),
    "cheque_book": ("service:write", ServiceAgent()),
    "kyc": ("service:write", ServiceAgent()),
}
_INTENT_RULES = (("balance", "balance"), ("statement", "statement"), ("transaction", "transaction"), ("address_change", "address"), ("cheque_book", "cheque"), ("kyc", "kyc"))


def classify(text: str) -> str | None:
    """Deterministically classify only supported banking intents."""
    lowered = text.lower()
    return next((intent for word, intent in _INTENT_RULES if word in lowered), None)


@dataclass(frozen=True)
class WorkflowResult:
    intent: str
    answer: str
    tool: str | None


class CoordinatorAgent:
    @timed("coordinator_workflow")
    async def run(self, message: str, user: dict, prior_history: list[dict]) -> WorkflowResult:
        intent = classify(message)
        # Do not log message/history content; they may contain sensitive data.
        log_event(logger, "workflow_started", intent=intent, history_count=len(prior_history))
        if not intent:
            return WorkflowResult("unknown", "I can help with balances, transactions, statements, address changes, cheque books, and KYC updates.", None)

        scope, agent = INTENTS[intent]
        require_scope(user, scope)
        result = await agent.run(intent, user["sub"])
        # Customer IDs are correlation identifiers, not customer-facing context.
        approved_data = {key: value for key, value in result.data.items() if key != "customer_id"}
        safe_result = redact(json.dumps(approved_data, separators=(",", ":")))
        system = "You are a banking assistant. Explain only the supplied approved tool result. Do not invent facts, request secrets, or reveal redacted data."
        try:
            answer = redact(await ThirdPartyLLM().complete(system, f"Approved tool result: {safe_result}"))
        except LLMProviderError:
            logger.exception("llm_synthesis_failed", extra={"event": {"intent": intent, "tool": result.tool}})
            answer = "Your request was completed. Please check your secure banking channel for the result."
        log_event(logger, "workflow_completed", intent=intent, server=result.server, tool=result.tool)
        return WorkflowResult(intent, answer, result.tool)
