"""Specialist agents map approved intents onto their least-privilege MCP tools."""
import logging
from collections.abc import Callable

from ..logging import log_event
from ..mcp.servers import AccountsMCPServer, ServiceMCPServer, ToolResult, TransactionsMCPServer

logger = logging.getLogger(__name__)


class AccountsAgent:
    async def run(self, intent: str, customer_id: str) -> ToolResult:
        if intent != "balance":
            raise ValueError(f"AccountsAgent does not support intent: {intent}")
        log_event(logger, "agent_tool_call", agent="accounts", intent=intent, tool="balance_enquiry")
        return AccountsMCPServer().balance_enquiry(customer_id)


class TransactionAgent:
    _tool_by_intent: dict[str, str] = {"transaction": "transaction_details", "statement": "statement_request"}

    async def run(self, intent: str, customer_id: str) -> ToolResult:
        tool = self._tool_by_intent[intent]
        log_event(logger, "agent_tool_call", agent="transactions", intent=intent, tool=tool)
        server = TransactionsMCPServer()
        return server.transaction_details(customer_id) if tool == "transaction_details" else server.statement_request(customer_id)


class ServiceAgent:
    _tool_by_intent: dict[str, str] = {"address_change": "change_address", "cheque_book": "cheque_book_request", "kyc": "kyc_update"}

    async def run(self, intent: str, customer_id: str) -> ToolResult:
        tool = self._tool_by_intent[intent]
        log_event(logger, "agent_tool_call", agent="service", intent=intent, tool=tool)
        server = ServiceMCPServer()
        handlers: dict[str, Callable[[str], ToolResult]] = {"change_address": server.change_address, "cheque_book_request": server.cheque_book_request, "kyc_update": server.kyc_update}
        return handlers[tool](customer_id)
