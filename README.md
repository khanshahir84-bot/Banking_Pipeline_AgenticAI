# Banking Agentic Chat

A production-oriented reference implementation of the supplied banking workflow diagram. It provides a secure FastAPI chat boundary, deterministic coordinator/specialist agents, MCP-style domain tool servers, session history, PII redaction, authorization, structured observability, and a **third-party OpenAI-compatible LLM** response layer. There is deliberately no self-hosted LLM integration.

> **Important:** This is a reference service. Replace the demonstration MCP data adapters and HS256 development identity verifier with bank-approved, mTLS-protected core-banking and OIDC/JWKS integrations before production.

## Architecture mapping

| Diagram component | Implementation | Responsibility |
|---|---|---|
| User interface/API | `app/main.py` | `/v1/chat`, correlation IDs, request validation, authenticated session boundary. |
| Bank identity provider / Authorization | `app/security.py` | Validates bearer JWT and checks the minimum intent scope before any tool call. |
| Guardrails | `app/guardrails/` | Modular input PII redaction, prompt-injection, scope, and content-safety controls; plus output groundedness, content safety, and response validation. |
| Coordinator Agent | `app/agents/coordinator.py` | Classifies deterministically, selects a fixed agent, applies scope gates, and synthesizes tool output. |
| Accounts / Transaction / Service Agents | `app/agents/specialists.py` | One focused dispatcher per banking domain. |
| MCP Servers | `app/mcp/servers.py` | Explicit typed tools: balance, transaction, statement, address, cheque book, and KYC. |
| Third-party LLM | `app/llm.py` | Calls an externally hosted OpenAI-compatible `/chat/completions` endpoint only. |
| Session Store | `app/store.py` | SQLite conversation history/shared state; mount `/data` in Docker. |
| Observability & evaluation | `app/observability.py`, `app/main.py` | JSON logs include `trace_id`, intent, server/tool, durations, and failures for evaluation pipelines. |

## Agent workflow and debugging

1. Middleware creates or accepts `X-Trace-Id`; use it to find every workflow hop in JSON logs.
2. The API verifies the IdP token, then runs **input guardrails before persistence or prompting**. They redact SSNs, card/account-like values, emails, phones, and IBANs; block prompt-injection and unsafe requests; require an allow-listed banking intent; and enforce the corresponding OAuth scope.
3. The coordinator repeats the intent-scope authorization as defense in depth, then invokes one fixed specialist. Specialists invoke a named MCP tool; the LLM cannot choose tools or arguments.
4. The LLM receives only redacted, approved tool output. **Output guardrails** validate response shape (no links, secret requests, control characters, or PII), reject unsafe content, and check financial/status claims against approved tool data. A rejected or unavailable model response is replaced with a deterministic rendering of that same approved data.
5. `input_guardrails_passed`, `guardrail_blocked`, `llm_output_replaced`, `workflow_started`, `agent_tool_call`, `workflow_completed`, timing, and HTTP events make diagnosis easy. Events contain decision names/categories—not raw prompts, tokens, or secrets.

### Scope map

| Intent | Required scope | MCP tool |
|---|---|---|
| Balance | `accounts:read` | `balance_enquiry` |
| Transactions / statements | `transactions:read` | `transaction_details` / `statement_request` |
| Address, cheque book, KYC | `service:write` | respective service tool |

## Configure and run

```bash
cp ".env copy.example" .env
# Set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, a strong JWT_SECRET, and DEVELOPER_TOKEN.
pip install -r requirements.txt
uvicorn app.main:app --reload
# Equivalent direct module form (do not use a non-existent `app.py`):
python -m app.main
```

The LLM provider must expose OpenAI-compatible `POST /chat/completions`. The application does not make an LLM call without `LLM_API_KEY`; this enables safe local workflow tests only.

### Authentication configuration

For the development browser UI, set all three of the following values in `.env`:

```dotenv
AUTH_MODE=development
JWT_SECRET=<a-long-random-development-secret>
DEVELOPER_TOKEN=<an-HS256-JWT-signed-with-JWT_SECRET>
```

`DEVELOPER_TOKEN` must contain a JWT `sub` claim and the scopes needed by the
demo prompts: `accounts:read transactions:read service:write`. Create a
**development-only** token with the same value configured as `JWT_SECRET`, then
copy its complete output into `DEVELOPER_TOKEN` in `.env`:

```bash
python -c 'import jwt; print(jwt.encode({"sub":"customer-42","scope":"accounts:read transactions:read service:write"}, "change-me-before-production", algorithm="HS256"))'
```

The browser UI uses this server-side configuration, so the token is never
rendered in the page or sent from the browser. Direct API callers can still send
their own bearer token in the `Authorization` header.

For production, do **not** use `AUTH_MODE=development` or `DEVELOPER_TOKEN`.
Use `AUTH_MODE=jwks` and set all of `JWT_ISSUER`, `JWT_AUDIENCE`, and
`JWT_JWKS_URL` to the bank identity provider's values. The application validates
the issuer, audience, and RS256/ES256 JWT signature in that mode.

Call the API:

```bash
curl -X POST http://localhost:8000/v1/chat \
 -H 'Authorization: Bearer <TOKEN>' -H 'Content-Type: application/json' \
 -d '{"session_id":"demo-1","message":"What is my balance?"}'
```

## Docker

```bash
cp ".env copy.example" .env  # set real provider credentials and JWT_SECRET
docker compose up --build
```

`docker-compose.yml` persists session data in the `banking-data` volume. Deploy behind TLS/API gateway, use a secrets manager (not `.env`), configure IdP issuer/audience/JWKS validation, mTLS plus least-privilege service credentials to MCP/back-end APIs, encrypted database storage, retention policies, rate limits, approval/step-up flows for mutating actions, and immutable audit exports.

## Test

```bash
pytest -q
```

## Guardrail policy and traceability

Guardrails are deterministic, testable modules rather than a model prompt. `InputGuardrails` returns a sanitized message and non-sensitive findings; rejected input is not saved to session history or sent to a specialist/LLM. `OutputGuardrails` receives both the candidate response and the MCP-approved data, and validates every response path, including the deterministic fallback. Trace logs record the guardrail stage, reason, and rule categories, while `workflow_audit` records a non-sensitive blocked outcome.

The policy is intentionally conservative: unsupported requests are rejected at the banking boundary, and a caller missing an intent scope receives an authorization-safe denial. Prompt-injection rules target system/developer/tool boundary manipulation rather than ordinary banking wording. The content-safety policy is not a substitute for a bank’s wider fraud, AML, emergency, or human-escalation program; extend the rule sets and response procedures under the bank’s governance process.

## Security review fixes applied

This implementation now additionally binds every session ID to the authenticated subject, records a minimal workflow audit trail, validates session-ID format, returns a trace ID with HTTP errors, and redacts generated LLM text before returning or storing it. The API deliberately does **not** place a raw message or conversation history in application logs.

For a bank deployment, set `AUTH_MODE=jwks`, `JWT_ISSUER`, `JWT_AUDIENCE`, and `JWT_JWKS_URL`; the service will validate the JWT signature using the IdP key and enforce issuer/audience claims. `AUTH_MODE=development` is only for the local HS256 token command above. Set `LLM_REQUIRED=true` so a missing third-party provider credential fails safely rather than selecting the demonstration text fallback.

The browser page at `/` is a dependency-free, same-origin demo chat UI. In development it uses the server-side `DEVELOPER_TOKEN`; the token is not placed in the page or browser storage. It is not a production identity UI: production users should authenticate through the bank's existing OIDC front end/BFF, which forwards a short-lived bearer token.

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
