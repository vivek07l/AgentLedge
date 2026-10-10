# AgentsLedge — Final Setup Guide

## Product naming

| Name | Scope |
|---|---|
| **AgentsLedge** | Visible product name (marketplace website, UI, documentation) |
| **AgentMesh** | MCP integration layer (`agentmesh-mcp/`) |

Repository folders, Python packages, and internal modules are **not** renamed.

---

## Prerequisites

- Python 3.10+ (backend tested with 3.11; MCP adapter tested with 3.13)
- Node.js 18+ and npm
- Git

---

## 1 — Backend (AgentsLedge API)

### Environment variables

Copy `.env.example` to `.env` and set:

```env
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=sqlite:///./agentledge.db          # or postgresql+psycopg2://user:pass@host/db
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# Optional — enables live LLM invocations
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# OAuth / MCP — must match the deployed MCP adapter URL exactly
AGENTMESH_MCP_RESOURCE_URL=http://127.0.0.1:8011/mcp
CORS_ORIGINS=http://localhost:3000
```

### Install and start

```powershell
cd agenticxchange
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Seed the database on first run
.\.venv\Scripts\python.exe -m src.database.bootstrap

# Start the API server (port 8000)
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --port 8000
```

### Run backend tests

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_temp -q
```

---

## 2 — Frontend (AgentsLedge UI)

The React frontend calls `http://localhost:8000` by default. Override with:

```env
REACT_APP_API_URL=https://your-api-host.example.com
```

### Start (development)

```powershell
cd agenticxchange\frontend
npm install
npm start
```

Opens at `http://localhost:3000`.

### Production build

```powershell
npm run build
```

Outputs a static bundle to `frontend/build/`. Serve with any static host or:

```powershell
npx serve -s build
```

---

## 3 — MCP Adapter (AgentMesh)

### Environment variables

```powershell
$env:AGENTLEDGE_API_BASE_URL   = "http://127.0.0.1:8000"      # Backend URL
$env:AGENTLEDGE_OAUTH_ISSUER   = "http://127.0.0.1:8000"      # Must match backend SECRET_KEY issuer
$env:AGENTMESH_MCP_PUBLIC_URL  = "http://127.0.0.1:8011/mcp"  # Public MCP endpoint (matches backend AGENTMESH_MCP_RESOURCE_URL)
$env:AGENTMESH_MCP_TRANSPORT   = "streamable-http"             # or "stdio" for MCP Inspector
$env:AGENTMESH_MCP_HOST        = "127.0.0.1"
$env:AGENTMESH_MCP_PORT        = "8011"
```

### Install and start

```powershell
cd agentmesh-mcp
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install --upgrade pip
.\.venv313\Scripts\python.exe -m pip install -e ".[test]"

# Start Streamable HTTP (requires backend running on port 8000)
.\.venv313\Scripts\python.exe -m agentmesh_mcp.server
```

### Run MCP tests

```powershell
.\.venv313\Scripts\python.exe -m pytest --basetemp=.pytest_temp -q
```

### Stdio (MCP Inspector only)

```powershell
$env:AGENTMESH_MCP_TRANSPORT = "stdio"
.\.venv313\Scripts\python.exe -m agentmesh_mcp.server
```

---

## 4 — Implemented MCP transport and endpoint

**Transport:** Streamable HTTP (MCP SDK `>=2.0.0`)

**Endpoint (local):** `http://127.0.0.1:8011/mcp`

**Authentication:** OAuth 2.0 Authorization Code with PKCE S256.

The MCP SDK validates each bearer token by introspecting it at:

```
POST http://127.0.0.1:8000/oauth/introspect
Authorization: Bearer <user-token>
```

Required claims:
- `active: true`
- `iss` == `AGENTLEDGE_OAUTH_ISSUER`
- `aud` == `AGENTMESH_MCP_PUBLIC_URL`
- `scope` contains `marketplace:read`
- `exp` in the future

### MCP tools (all read-only)

| Tool | Description |
|---|---|
| `discover_services` | Search listings by query, category, sort, price, rating, success rate |
| `compare_providers` | Compare live listing + reputation data with filters |
| `list_service_categories` | List categories from active listings |

---

## 5 — Configuring an external MCP client

### Local MCP Inspector

```powershell
npx @modelcontextprotocol/inspector .\.venv313\Scripts\python.exe -m agentmesh_mcp.server
```

Set transport to `stdio` in `AGENTMESH_MCP_TRANSPORT` or pass the script directly.

### Gemini / ChatGPT (remote — requires public HTTPS)

External MCP clients require:

1. **HTTPS endpoint** for `AGENTMESH_MCP_PUBLIC_URL` (e.g. `https://mcp.yourdomain.com/mcp`)
2. **HTTPS backend** for `AGENTLEDGE_API_BASE_URL` and `AGENTLEDGE_OAUTH_ISSUER`
3. Registered OAuth client via `POST /oauth/register` with your redirect URI
4. Backend `CORS_ORIGINS` set to the exact frontend HTTPS origin

The OAuth authorization flow:
```
1. Client → GET /oauth/authorize (with code_challenge, scope=marketplace:read, resource=<mcp-url>)
2. User signs in at AgentsLedge, approves consent
3. AgentsLedge → redirect with ?code=
4. Client → POST /oauth/token (with code_verifier)
5. AgentsLedge → { access_token, expires_in: 900, scope: "marketplace:read" }
6. Client → MCP tool call with Authorization: Bearer <access_token>
7. MCP SDK → POST /oauth/introspect → validates claims → permits tool execution
```

**No external connection has been tested** — local server is not publicly reachable. The implementation is complete; HTTPS hosting and a registered client are the remaining blockers.

---

## 6 — Authentication requirements

| Feature | Implementation |
|---|---|
| User login/registration | Username + bcrypt password, JWT access token (HS256), 60-minute expiry |
| Protected endpoints | Bearer JWT verified on every request; user identity isolated |
| OAuth PKCE | S256 code challenge, 10-minute code TTL, 15-minute token TTL, per-user audience |
| Rate limiting | Per-process SlowAPI rate limiter (baseline; use shared edge limiter for multi-worker) |
| Admin access | Separate `is_admin` flag, `AdminRoute` guard in frontend |
| Provider access | `is_provider` flag, `ProviderRoute` guard in frontend |

---

## 7 — Verified test results

| Suite | Command | Result |
|---|---|---|
| Backend | `.venv\Scripts\python.exe -m pytest --basetemp=.pytest_temp -q` | **45 passed** |
| MCP adapter | `.venv313\Scripts\python.exe -m pytest --basetemp=.pytest_temp -q` | **12 passed** |
| Frontend build | `npm run build` (in `frontend/`) | **Compiled successfully — 0 warnings** |
| Frontend test runner | `npm test` | Stalls on Windows OneDrive (Jest file-crawler issue); use `npm run build` as the verification baseline |

---

## 8 — Deployment Configuration (Render Blueprints)

Render blueprint specifications (`render.yaml`) have been generated in both repositories:

1. **`agenticxchange/render.yaml`**:
   - `agentsledge-backend`: Python 3.11 web service, `uvicorn src.main:app`, `/health` check.
   - `agentsledge-frontend`: Static site, `npm run build`, publish `./frontend/build`, SPA rewrite `/*` -> `/index.html`.
   - `agentsledge-db`: Managed PostgreSQL instance for persistent storage.

2. **`agentmesh-mcp/render.yaml`**:
   - `agentmesh-mcp`: Python web service running Streamable HTTP on port 10000, configured to connect to the backend's public HTTPS URL.

---

## 9 — Remaining external blockers

| Blocker | What is needed |
|---|---|
| Live OAuth / MCP external test | Public HTTPS domain, DNS, TLS certificate, deployed instances |
| ChatGPT native MCP | OpenAI Business/Enterprise plan or developer mode with OAuth PKCE |
| ChatGPT Custom GPT Actions | OpenAPI HTTP gateway wrapping the MCP JSON-RPC interface |
| Live LLM invocations | `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in backend `.env` |
| Production database | Set `DATABASE_URL` to a managed Postgres instance (automated in `render.yaml`) |
| Alembic migrations (if using Postgres) | Run `alembic upgrade head` before starting backend |

