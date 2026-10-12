# AgentsLedge OAuth and AgentMesh MCP setup

This guide covers per-user OAuth for the read and write AgentMesh tools. It does not deploy either service.

## What the connection allows

Read tools require `marketplace:read`. Negotiation, invocation, and review tools require `marketplace:read marketplace:write`. Each call is authenticated for the person who approved the connection. The adapter validates the opaque access token through the AgentsLedge OAuth introspection endpoint, checks issuer, expiry, supported scopes, and the exact MCP audience, then forwards that same bearer token to the backend. Backend route authorization repeats the scope check and derives user identity from the token, not caller input. AgentsLedge stores only hashes of access tokens and single-use authorization codes. Access tokens last 15 minutes; the client can revoke one sooner.

The authorization flow uses OAuth Authorization Code with PKCE S256, dynamic client registration, an exact registered redirect URI, a signed CSRF cookie, and an explicit sign-in/consent page. The consent screen displays whether the client requests read-only or read/write access. Existing username/password login at `POST /token` and its JWTs are unchanged. OAuth callers cannot purchase tokens, change balances, access admin operations, or read another user's private records. The write tools call only existing negotiation, invocation, and verified-review routes.

By default, AgentMesh write tools create a pending action approval. The account owner signs in to AgentsLedge and approves that exact action at `/approvals`; the MCP caller then repeats it with its one-time `approval_id`. An owner may instead explicitly enable autonomous execution in **Profile → Autonomous execution**, configure an allowlist and conservative limits, and authorize eligible operations through the saved account policy. In that mode no pending approval is created for policy-approved actions. The policy can be read but not changed through OAuth. The backend still checks scope, user identity, service allowlist, budget, balance, negotiation state, ownership, idempotency, and settlement. Manual approval remains the default for accounts without an enabled policy. Tool descriptions are not the security control.

`invoke_service_agent` requires an accepted negotiation for paid listings and a stable idempotency key. Existing backend logic reserves tokens, settles only after successful live execution, releases the reservation on failure, and returns stored results for safe retries. Demo responses are labeled and are not reviewable. A live provider error returns a 502 and is not replaced with a demo result; if `AI_MODE=live` but the selected provider key is missing, invocation returns a 503 before reservation and never falls back to demo.

Marketplace listings are discoverable even when they do not have a supported implementation. The API includes `execution_available`; unsupported listings are shown as discovery-only, and invocation rejects them before any token reservation. The built-in handlers remain the supported executable implementations.

## Required settings

Set these in the backend deployment's secret/environment settings. The example values below are local-only; replace both public URLs with the final HTTPS origins before connecting a remote client.

| Backend variable | Local example | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | generate a long random secret | Signs existing login JWTs and the short-lived OAuth CSRF request cookie. Keep private. |
| `DATABASE_URL` | `sqlite:///./agentmesh.sqlite3` | Persistent user, listing, OAuth client, authorization code, and token records. For hosted use, select persistent managed storage. |
| `OAUTH_ISSUER` | `https://api.example.com` | Exact public HTTPS origin for OAuth discovery, authorization, token, introspection, and revocation endpoints. No trailing slash. |
| `AGENTMESH_MCP_RESOURCE_URL` | `https://mcp.example.com/mcp` | Exact MCP resource/audience URL; must match the adapter setting byte-for-byte. |
| `OAUTH_RATE_LIMIT_PER_MINUTE` | `20` | Per-process limit for each OAuth endpoint, grouped by client IP. |
| `CORS_ORIGINS` | your exact frontend origin | Exact browser UI origins; do not use `*` with credentials. |

The adapter needs:

| Adapter variable | Local example | Purpose |
| --- | --- | --- |
| `AGENTLEDGE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend API origin used for real marketplace calls. |
| `AGENTLEDGE_OAUTH_ISSUER` | `http://127.0.0.1:8000` | Must equal backend `OAUTH_ISSUER`; adapter appends `/oauth/introspect`. |
| `AGENTMESH_MCP_PUBLIC_URL` | `http://127.0.0.1:8011/mcp` | Must equal backend `AGENTMESH_MCP_RESOURCE_URL` exactly. |
| `AGENTLEDGE_API_TIMEOUT_SECONDS` | `10` | Backend request timeout. |
| `AGENTMESH_MCP_TRANSPORT` | `stdio` | Use `streamable-http` only behind HTTPS for remote access. |
| `AGENTMESH_MCP_PORT` | `8011` | Local MCP HTTP port when using Streamable HTTP. |

Gemini runs in the backend through Google's documented OpenAI-compatible endpoint, not in the adapter. Set `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, a Gemini-supported `AI_MODEL`, and `AI_MODE=live`. Never put the key in frontend or adapter configuration. A configured key alone leaves the application in demo mode. Set `AI_MODEL` explicitly for Gemini; the backend does not fall back to the OpenAI model name. The `gemini_text_summarizer` implementation is limited to the listing explicitly bound to it by an administrator and is only reported executable when these live settings are present.

Use the backend `.env.example` and adapter `.env.example` as templates. Never commit `.env` files, passwords, access tokens, or generated secrets.

## Local setup and test flow

1. Start the backend with its local environment and keep it running on port 8000.
2. Register a regular member account through the app or `POST /users/register`.
3. In `agentmesh-mcp`, create/install its Python environment and install the package with its test extra.
4. Set the three adapter variables above to the local URLs. The backend defaults already match those local values.
5. Run adapter transport locally with Streamable HTTP. A client first reads the MCP protected-resource metadata, follows the authorization server URL, registers a public OAuth client, opens the AgentsLedge sign-in/consent page, receives a PKCE authorization code, and exchanges it for a 15-minute token.
6. Call read tools to discover, compare, and inspect services. For writes, the OAuth consent must grant both read and write scopes.
7. Existing accounts start with autonomous mode disabled. To opt in, the account owner opens **Profile → Autonomous execution**, enables it, and configures budgets, allowed categories/listings, daily negotiation limit, execution retry limit, and optional automatic reviews. At least one category or listing must be allowed. The OAuth client cannot edit these settings.
8. With autonomous mode disabled, a write tool without `approval_id` queues an approval; approve the exact action at `/approvals`, then repeat with its one-time ID. With autonomous mode enabled, use `complete_marketplace_workflow` to discover, compare, negotiate, execute, and retrieve a result within the policy; the same backend policy gate protects the individual tools. Reuse the same idempotency key for retries.
9. Revoke with `POST /oauth/revoke` using the issued `token` and its `client_id`, or wait for expiry.

For local stdio/Inspector work, no HTTP bearer header is available; it is a local process boundary. Remote Streamable HTTP requires the SDK auth middleware and token verifier and rejects missing, expired, wrong-issuer, wrong-audience, or wrong-scope tokens.

## Hosting preparation (not performed)

Host the FastAPI API and MCP adapter as separate services, with a public HTTPS address for each. The UI can be a static host. Set:

- backend `OAUTH_ISSUER` to the API's canonical HTTPS origin;
- backend `AGENTMESH_MCP_RESOURCE_URL` and adapter `AGENTMESH_MCP_PUBLIC_URL` to the same canonical MCP URL (including `/mcp`);
- adapter `AGENTLEDGE_OAUTH_ISSUER` and `AGENTLEDGE_API_BASE_URL` to the backend HTTPS origin;
- backend `CORS_ORIGINS` to the frontend's exact HTTPS origin;
- `SECRET_KEY` from the host's secret manager and `DATABASE_URL` to persistent managed storage.

The current feature branch has one Alembic head, `8a72d421c550`, directly after `72dc3f911a2e`. It adds the `autonomous_execution_policies` table and does not alter existing rows. On the stated database at `72dc3f911a2e`, verify the target database, revision and schema, confirm a recoverable backup, then apply `alembic upgrade head`. Fresh databases receive the table through the full migration chain. A populated, unversioned legacy database must follow the existing schema-verifying adoption path; never stamp it at head or run initial migrations blindly. Test migration scenarios on disposable databases first. Never reset or recreate production tables. Terminate TLS at the host/reverse proxy; do not publish the MCP listener over plain HTTP. Keep registration, authorization, token, introspection, and revoke routes on the API origin. Use a shared edge rate limiter in front of OAuth routes for multi-worker deployments; the included limiter is process-local and is only a baseline. Configure backups, access logs that omit credentials, health checks, and monitoring. Verify the metadata issuer exactly matches the canonical public origin through the HTTPS proxy before registering a client.

## Compatibility and limits

OpenAI's current documentation says ChatGPT custom MCP connections support OAuth and DCR/CIMD options, and supports Streamable HTTP. This project implements DCR with public clients; it does not implement CIMD. OpenAI's public Go-plan documentation does not explicitly guarantee that a user on ChatGPT Go can add and use a custom remote MCP server. Plan, workspace, role, surface, and feature rollout affect availability, so Go compatibility is **not established**; verify in the Plugins/Apps controls visible in the actual account.

The included OAuth authorization server is project code, not a reviewed identity provider. Before enabling write scopes on a public production endpoint, obtain a security review and add account recovery and email verification, a durable shared rate-limit store, operational monitoring, and formal key rotation/retention procedures. Do not change Render settings or deploy as part of this code change. Do not treat successful local tests as proof of production security or ChatGPT Go availability.
