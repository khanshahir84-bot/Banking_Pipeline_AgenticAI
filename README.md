# Banking Agentic Chat

A production-oriented reference implementation of the supplied banking workflow diagram. It provides a secure FastAPI chat boundary, deterministic coordinator/specialist agents, MCP-style domain tool servers, session history, PII redaction, authorization, structured observability, and a **third-party OpenAI-compatible LLM** response layer. There is deliberately no self-hosted LLM integration.

> **Important:** This is a reference service. Replace the demonstration MCP data adapters and HS256 development identity verifier with bank-approved, mTLS-protected core-banking and OIDC/JWKS integrations before production.

## Architecture mapping

| Diagram component | Implementation | Responsibility |
|---|---|---|
| User interface/API | `app/main.py` | `/v1/chat`, correlation IDs, request validation, authenticated session boundary. |
| Bank identity provider / Authorization | `app/security.py` | Validates bearer JWT and checks the minimum intent scope before any tool call. |
| PII Redaction | `app/pii.py` | Redacts SSNs, account-like numbers, and emails before history, logs, and LLM prompts. |
| Coordinator Agent | `app/agents/coordinator.py` | Classifies deterministically, selects a fixed agent, applies scope gates, and synthesizes tool output. |
| Accounts / Transaction / Service Agents | `app/agents/specialists.py` | One focused dispatcher per banking domain. |
| MCP Servers | `app/mcp/servers.py` | Explicit typed tools: balance, transaction, statement, address, cheque book, and KYC. |
| Third-party LLM | `app/llm.py` | Calls an externally hosted OpenAI-compatible `/chat/completions` endpoint only. |
| Session Store | `app/store.py` | SQLite conversation history/shared state; mount `/data` in Docker. |
| Observability & evaluation | `app/observability.py`, `app/main.py` | JSON logs include `trace_id`, intent, server/tool, durations, and failures for evaluation pipelines. |

## Agent workflow and debugging

1. Middleware creates or accepts `X-Trace-Id`; use it to find every workflow hop in JSON logs.
2. The API verifies the IdP token then redacts the input **before** persisting or prompting.
3. The coordinator only recognizes allow-listed intents. It checks an intent-specific OAuth scope, then invokes one specialist.
4. Specialists invoke a named MCP tool. The LLM cannot choose tools or arguments, reducing prompt-injection blast radius.
5. A third-party LLM converts the already-approved, redacted tool result into customer language. If it is unavailable, the workflow returns a safe completion fallback and logs `llm_synthesis_failed`.
6. `workflow_started`, `agent_tool_call`, `workflow_completed`, timing, and HTTP events make diagnosis easy. Do not log raw tokens, request bodies, or tool secrets.

### Scope map

| Intent | Required scope | MCP tool |
|---|---|---|
| Balance | `accounts:read` | `balance_enquiry` |
| Transactions / statements | `transactions:read` | `transaction_details` / `statement_request` |
| Address, cheque book, KYC | `service:write` | respective service tool |

## Configure and run

```bash
cp .env.example .env
# Set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, and a strong JWT_SECRET.
pip install -r requirements.txt
uvicorn app.main:app --reload
# Equivalent direct module form (do not use a non-existent `app.py`):
python -m app.main
```

The LLM provider must expose OpenAI-compatible `POST /chat/completions`. The application does not make an LLM call without `LLM_API_KEY`; this enables safe local workflow tests only.

Create a **development-only** token:

```bash
python -c 'import jwt; print(jwt.encode({"sub":"customer-42","scope":"accounts:read transactions:read service:write"}, "change-me-before-production", algorithm="HS256"))'
```

Call the API:

```bash
curl -X POST http://localhost:8000/v1/chat \
 -H 'Authorization: Bearer <TOKEN>' -H 'Content-Type: application/json' \
 -d '{"session_id":"demo-1","message":"What is my balance?"}'
```

## Docker

```bash
cp .env.example .env  # set real provider credentials and JWT_SECRET
docker compose up --build
```

`docker-compose.yml` persists session data in the `banking-data` volume. Deploy behind TLS/API gateway, use a secrets manager (not `.env`), configure IdP issuer/audience/JWKS validation, mTLS plus least-privilege service credentials to MCP/back-end APIs, encrypted database storage, retention policies, rate limits, approval/step-up flows for mutating actions, and immutable audit exports.

## Test

```bash
pytest -q
```

## Security review fixes applied

This implementation now additionally binds every session ID to the authenticated subject, records a minimal workflow audit trail, validates session-ID format, returns a trace ID with HTTP errors, and redacts generated LLM text before returning or storing it. The API deliberately does **not** place a raw message or conversation history in application logs.

For a bank deployment, set `AUTH_MODE=jwks`, `JWT_ISSUER`, `JWT_AUDIENCE`, and `JWT_JWKS_URL`; the service will validate the JWT signature using the IdP key and enforce issuer/audience claims. `AUTH_MODE=development` is only for the local HS256 token command above. Set `LLM_REQUIRED=true` so a missing third-party provider credential fails safely rather than selecting the demonstration text fallback.

The browser page at `/` is a dependency-free, same-origin demo chat UI. It is not an identity UI: production users should authenticate through the bank's existing OIDC front end/BFF, which forwards a short-lived bearer token. Do not persist tokens in browser storage.

### MCP integration contract

The three domain servers expose explicit tool metadata (name, description, required scope) and typed results. This provides a direct contract for replacing the in-process demonstrators with a bank's MCP transport adapter. Preserve the coordinator-owned authorization and specialist-to-one-server ownership when moving those implementations behind mTLS. Mutating service tools intentionally begin confirmation or secure-upload workflows; they do not make irreversible changes based solely on free text.

### Audit and incident triage

Use the response `trace_id` or `X-Trace-Id` header to correlate JSON events. The session store contains redacted user/assistant messages and the `workflow_audit` table stores trace ID, user ID, intent, tool, and completion state—never an access token or raw prompt. Query audit data only through approved support tooling with appropriate customer-data controls.

## Demonstration database

A seeded SQLite database has been created at `/data/banking_chat.db` in this environment. It has 10 demonstration customers and accounts, plus **50 transaction records** (five per account); the development token's `customer-42` is included. The Accounts and Transactions MCP servers now query this data rather than returning hard-coded records.

To create the same idempotent demonstration dataset on another host, run:

```bash
python scripts/seed_database.py --database /data/banking_chat.db
```

Use `--reset` only to deliberately replace the demonstration banking tables. The Docker command runs this seeder before Uvicorn and does not overwrite an existing dataset. These values are synthetic and must never be treated as production banking data.
