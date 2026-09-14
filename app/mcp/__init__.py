"""MCP domain-server registry and public tool-server contracts.

The coordinator delegates through specialist agents, each of which is bound to a
single server. ``MCP_SERVERS`` is an inspectable registry for readiness checks,
debug tooling, and future MCP transport adapters; it is not a bypass around the
coordinator's authorization boundary.
"""
from .servers import AccountsMCPServer, BaseMCPServer, ServiceMCPServer, ToolDefinition, ToolResult, TransactionsMCPServer

MCP_SERVERS = {
    AccountsMCPServer.name: AccountsMCPServer,
    TransactionsMCPServer.name: TransactionsMCPServer,
    ServiceMCPServer.name: ServiceMCPServer,
}


def available_servers() -> tuple[str, ...]:
    """Return stable registered server names without instantiating bank adapters."""
    return tuple(MCP_SERVERS)


__all__ = [
    "AccountsMCPServer",
    "BaseMCPServer",
    "ServiceMCPServer",
    "ToolDefinition",
    "ToolResult",
    "TransactionsMCPServer",
    "MCP_SERVERS",
    "available_servers",
]
