# AgentsLedge OAuth and AgentMesh MCP setup

This guide covers the read-only AgentMesh connection to AgentsLedge. It does not deploy either service.

## What the connection allows

AgentMesh exposes three read-only tools: `discover_services`, `list_service_categories`, and `compare_providers`. Each call is authenticated for the person who approved the connection. The adapter validates the opaque access token through the AgentsLedge OAuth introspection endpoint, checks issuer, expiry, the `marketplace:read` scope, and the exact MCP audience, then forwards that same bearer token to the backend. AgentsLedge stores only hashes of access tokens and single-use authorization codes. Access tokens last 15 minutes; the client can revoke one sooner.

The authorization flow uses OAuth Authorization Code with PKCE S256, dynamic client registration, an exact registered redirect URI, a signed CSRF cookie, and an explicit sign-in/consent page. Existing username/password login at `POST /token` and its JWTs are unchanged. OAuth tokens can only call read-only listing endpoints. Negotiations, purchases, invocation, token changes, user history, and reviews remain unavailable through MCP.

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

Use the backend `.env.example` and adapter `.env.example` as templates. Never commit `.env` files, passwords, access tokens, or generated secrets.

## Local setup and test flow

1. Start the backend with its local environment and keep it running on port 8000.
2. Register a regular member account through the app or `POST /users/register`.
3. In `agentmesh-mcp`, create/install its Python environment and install the package with its test extra.
4. Set the three adapter variables above to the local URLs. The backend defaults already match those local values.
5. Run adapter transport locally with Streamable HTTP. A client first reads the MCP protected-resource metadata, follows the authorization server URL, registers a public OAuth client, opens the AgentsLedge sign-in/consent page, receives a PKCE authorization code, and exchanges it for a 15-minute token.
6. Call `discover_services`, `list_service_categories`, or `compare_providers`. The adapter validates and forwards the user's token on every tool call.
7. Revoke with `POST /oauth/revoke` using the issued `token` and its `client_id`, or wait for expiry.

For local stdio/Inspector work, no HTTP bearer header is available; it is a local process boundary. Remote Streamable HTTP requires the SDK auth middleware and token verifier and rejects missing, expired, wrong-issuer, wrong-audience, or wrong-scope tokens.

## Hosting preparation (not performed)

Host the FastAPI API and MCP adapter as separate services, with a public HTTPS address for each. The UI can be a static host. Set:

- backend `OAUTH_ISSUER` to the API's canonical HTTPS origin;
- backend `AGENTMESH_MCP_RESOURCE_URL` and adapter `AGENTMESH_MCP_PUBLIC_URL` to the same canonical MCP URL (including `/mcp`);
- adapter `AGENTLEDGE_OAUTH_ISSUER` and `AGENTLEDGE_API_BASE_URL` to the backend HTTPS origin;
- backend `CORS_ORIGINS` to the frontend's exact HTTPS origin;
- `SECRET_KEY` from the host's secret manager and `DATABASE_URL` to persistent managed storage.

Run the schema migration with `alembic upgrade head` before starting the backend. Terminate TLS at the host/reverse proxy; do not publish the MCP listener over plain HTTP. Keep registration, authorization, token, introspection, and revoke routes on the API origin. Use a shared edge rate limiter in front of OAuth routes for multi-worker deployments; the included limiter is process-local and is only a baseline. Configure backups, access logs that omit credentials, health checks, and monitoring. Verify the metadata issuer exactly matches the canonical public origin through the HTTPS proxy before registering a client.

## Compatibility and limits

OpenAI's current documentation says ChatGPT custom MCP connections support OAuth and DCR/CIMD options, and supports Streamable HTTP. This project implements DCR with public clients; it does not implement CIMD. OpenAI's public Go-plan documentation does not explicitly guarantee that a user on ChatGPT Go can add and use a custom remote MCP server. Plan, workspace, role, surface, and feature rollout affect availability, so Go compatibility is **not established**; verify in the Plugins/Apps controls visible in the actual account. The current tools are search and comparison only; no marketplace writes are exposed.

The included OAuth authorization server is project code, not a reviewed identity provider. Before a public production release, obtain a security review and add account recovery and email verification, a durable shared rate-limit store, operational monitoring, and formal key rotation/retention procedures. Do not treat successful local tests as proof of production security or ChatGPT Go availability.
