"""MCP domain tool servers and their explicit, inspectable tool contracts.

These in-process adapters are fully functional demonstration implementations.
In production retain the same contracts but replace their bodies with mTLS-authenticated
calls to the bank's core systems; no agent should connect to a core system directly.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    server: str
    tool: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    required_scope: str


class BaseMCPServer:
    """Shared MCP-style capability declaration for discovery and policy review."""

    name: str
    tools: tuple[ToolDefinition, ...]

    def tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self.tools)


class AccountsMCPServer(BaseMCPServer):
    name = "accounts-mcp"
    tools = (ToolDefinition("balance_enquiry", "Return available account balance", "accounts:read"),)

    def balance_enquiry(self, customer_id: str) -> ToolResult:
        return ToolResult(self.name, "balance_enquiry", {"customer_id": customer_id, "currency": "USD", "available_balance": "1,250.00"})


class TransactionsMCPServer(BaseMCPServer):
    name = "transactions-mcp"
    tools = (
        ToolDefinition("transaction_details", "Return recent transaction details", "transactions:read"),
        ToolDefinition("statement_request", "Queue statement delivery to secure inbox", "transactions:read"),
    )

    def transaction_details(self, customer_id: str) -> ToolResult:
        return ToolResult(self.name, "transaction_details", {"customer_id": customer_id, "transactions": [{"date": "2026-09-12", "description": "Grocer", "amount": "-45.20"}]})

    def statement_request(self, customer_id: str) -> ToolResult:
        return ToolResult(self.name, "statement_request", {"customer_id": customer_id, "status": "queued", "delivery": "secure inbox"})


class ServiceMCPServer(BaseMCPServer):
    name = "service-mcp"
    tools = (
        ToolDefinition("change_address", "Start an address-change confirmation workflow", "service:write"),
        ToolDefinition("cheque_book_request", "Queue a cheque-book request", "service:write"),
        ToolDefinition("kyc_update", "Start a KYC document-upload workflow", "service:write"),
    )

    def change_address(self, customer_id: str) -> ToolResult:
        return ToolResult(self.name, "change_address", {"customer_id": customer_id, "status": "requires_confirmation"})

    def cheque_book_request(self, customer_id: str) -> ToolResult:
        return ToolResult(self.name, "cheque_book_request", {"customer_id": customer_id, "status": "queued"})

    def kyc_update(self, customer_id: str) -> ToolResult:
        return ToolResult(self.name, "kyc_update", {"customer_id": customer_id, "status": "secure_upload_required"})
