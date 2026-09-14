import asyncio
import jwt
from app.agents.coordinator import CoordinatorAgent, classify
from app.config import settings

def test_classification():
    assert classify("What is my balance?") == "balance"
    assert classify("I want weather") is None

def test_balance_agent_and_scope():
    user={"sub":"customer-42","scope":"accounts:read"}
    result=asyncio.run(CoordinatorAgent().run("show my balance",user,[]))
    assert result.intent == "balance" and result.tool == "balance_enquiry"

def test_signed_demo_token_round_trip():
    token=jwt.encode({"sub":"customer-42","scope":"accounts:read"},settings.jwt_secret,algorithm="HS256")
    assert jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])["sub"] == "customer-42"


def test_public_package_interfaces():
    from app import __version__, create_app
    from app.agents import CoordinatorAgent
    from app.mcp import available_servers

    assert __version__ == "1.0.0"
    assert CoordinatorAgent is not None
    assert set(available_servers()) == {"accounts-mcp", "transactions-mcp", "service-mcp"}
    assert create_app().title == "Banking Agentic Chat"


def test_session_cannot_be_reused_by_another_customer(tmp_path, monkeypatch):
    from app import store
    from app.config import settings

    monkeypatch.setattr(settings, "database_path", str(tmp_path / "sessions.db"))
    store.ensure_session("owned-session", "customer-a")
    try:
        store.ensure_session("owned-session", "customer-b")
        assert False, "a second customer must not claim an existing session"
    except PermissionError:
        pass


def test_pii_redaction_removes_common_sensitive_values():
    from app.pii import redact

    value = redact("email jane@example.test SSN 123-45-6789 account 123456789012")
    assert "jane@example.test" not in value
    assert "123-45-6789" not in value
    assert "123456789012" not in value
