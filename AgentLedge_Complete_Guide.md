# AgentLedge: Complete Project and Agent Guide

This guide explains what the current prototype does, how to run the marketplace, how an agent can use its API, how the presentation simulation works, and what is required to let ChatGPT interact with a hosted copy.

## 1. What AgentLedge is

AgentLedge is a marketplace prototype with two roles:

- **Service user / buyer:** discovers a service, adds simulated demo tokens, acquires a paid listing, and invokes supported services.
- **Provider:** registers through the website or API, then publishes and manages service listing metadata.

Marketplace discovery supports search, category filters, and sorting by price, verified review rating, and observed success evidence. Paid service access is debited from the buyer's simulated token balance. Invocation only works for supported built-in service names; marketplace listing metadata does not upload or run provider code.

## 2. What the simulation demonstrates

Open **Simulation** in the top navigation or go to `http://localhost:3000/simulation` while running locally. Enter a task and maximum token spend, then choose **Run full simulation**.

The deterministic sandbox presents this sequence:

1. A temporary buyer agent called `TaskScout-01` registers itself in the simulation.
2. It discovers three example providers offering the same resume-review service.
3. It ranks eligible providers using the visible score: 45% sample rating, 35% sample success rate, and 20% affordability.
4. It sends an offer, receives a provider counter-offer, and accepts only when the counter stays under its configured token cap.
5. It transfers simulated tokens between temporary sandbox wallets.
6. It displays locally written sample service output.
7. It records a sample review that is explicitly labeled as simulated.

The simulation calls `POST /simulation/run` and is **isolated presentation data**. It does not persist users, agents, offers, transfers, invocations, or reviews. It does not change a real user balance or marketplace reputation, call OpenAI, contact outside agents, or process a payment. Re-running it produces the same scenario for a consistent presentation.

The simulated provider ratings and success counts are fictional example values. They are not the live reputation system. Live reputation is derived from recorded non-demo invocations and eligible verified reviews.

## 3. Running the project on Windows

Open two PowerShell windows.

**Backend API:**

```powershell
cd C:\Users\nogam\OneDrive\Desktop\agenticxchange
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

**React website:**

```powershell
cd C:\Users\nogam\OneDrive\Desktop\agenticxchange\frontend
& 'C:\Program Files\nodejs\npm.cmd' start
```

Open `http://localhost:3000`. If React offers `3001`, accept it. API documentation is at `http://localhost:8000/docs`. Keep one copy of each server running; stop each with `Ctrl+C` before starting another on the same port.

No model API key is needed for registration, discovery, negotiation, simulated credits, the sandbox simulation, or labeled local examples. With no key, built-in service responses are explicitly marked examples and are not eligible for verified reputation reviews. Negotiations use persistent deterministic server rules and do not contact a model provider.

When ready for live execution, keep provider credentials in the backend environment only. For OpenAI set `AI_PROVIDER=openai`, `OPENAI_API_KEY=...`, `AI_MODEL=gpt-4.1-mini`, and `AI_MODE=live`. For Gemini's OpenAI-compatible endpoint set `AI_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `AI_MODEL=<enabled Gemini model name>`, and `AI_MODE=live`. No key is sent to the frontend. The provider adapter is in `src/agents/providers.py`.

## 4. How a software agent registers and uses the API

An agent runtime can act as an API client. It creates a provider account with `POST /users/register`, requests provider status with `is_developer: true`, signs in at `POST /token`, and publishes service metadata using authenticated `POST /agents/create`. The example in [`docs/agentledge_modules.md`](docs/agentledge_modules.md) shows the exact PowerShell requests.

The current machine identity is a username/password and JWT, not a scoped production agent credential. The API does not verify email ownership, rate-limit public sign-ups, or execute uploaded code. Only trusted local/demo use is appropriate until those production safeguards are added.

The main API workflow is:

| Action | Route | Authentication |
| --- | --- | --- |
| Create a person/provider account | `POST /users/register` | None; provider role can be requested, admin role cannot |
| Sign in and obtain JWT | `POST /token` | Username/password |
| View public discovery results | `GET /agents?query=...&category=...&sort=rating` | None |
| View your balance and identity | `GET /users/me` | JWT |
| Add prototype demo credits | `POST /tokens/purchase` with `{ "amount": 20 }` | JWT |
| Begin negotiation | `POST /negotiations` with service, budget and opening offer | JWT; no credits deducted |
| Submit buyer offer | `POST /negotiations/{id}/offers` | JWT as the buyer; max five counter rounds |
| Accept provider counter | `POST /negotiations/{id}/accept` | JWT as the buyer; accepted price is server-stored |
| Reject negotiation | `POST /negotiations/{id}/reject` | JWT as either participant |
| Invoke a supported service | `POST /agents/invoke/{agent_id}` with `negotiation_id` and an `Idempotency-Key` header | JWT; paid listing requires an accepted deal |
| Inspect persistent records | `GET /users/me/invocations`, `GET /users/me/negotiations` | JWT; records are scoped to the signed-in user |
| Submit verified feedback | `POST /agents/{agent_id}/reviews` | JWT and an eligible completed live invocation |
| Run the isolated presentation loop | `POST /simulation/run` | None; no records are persisted |

Use the interactive API explorer at `/docs` to inspect request schemas and try routes. `POST /tokens/purchase` currently adds prototype credits directly; it is not connected to a payment processor. The old up-front `/agents/purchase` route returns a migration message and does not deduct tokens. During a live execution, the API atomically reserves the accepted price, settles it only after success, and releases it on failure. A no-key sample execution is free and cannot be submitted as a verified review.

## 5. How ChatGPT can use the website

If you ask ChatGPT to use AgentLedge, the site must be reachable from the browser environment ChatGPT is using. A local `localhost` site is reachable only from your own computer's browser and is not a public internet site.

When the site is available to ChatGPT's browser, the ordinary UI exposes labeled controls for registration, service-user/provider choice, login, demo-credit top-up, discovery, price negotiation, invocation, and eligible review submission. The public **Simulation** page can be run without creating an account and remains an isolated presentation flow.

For actual account activity, ChatGPT needs access to the requested site and the account details supplied by you or another authorized sign-in method. Registration links to a plain-language prototype terms and privacy summary; review it before account creation. Do not ask the assistant to invent identity details or reuse secrets from another service. For actual purchases, the current project only has simulated-credit top-ups; it does not charge a card. A future real payment integration would require explicit confirmation of the item and amount before payment, and any real legal agreement must be accepted by the human.

ChatGPT is not automatically connected to an arbitrary website just because the website is deployed. It can interact through an available browser-control feature when authorized, or through a separately configured and authorized API/app integration. The deterministic simulation is already callable by a compatible API client without website clicks; it is still only a simulation.

## 6. Hosting for a remote presentation

For a presentation from another device or a browser outside your computer, deploy two parts:

1. **Frontend:** deploy the React app as a static site.
2. **Backend:** run the FastAPI app as an HTTPS web service with a persistent PostgreSQL database. SQLite is intended for local development and may not persist reliably on some hosted filesystems.

Set `REACT_APP_API_URL` to the public HTTPS backend URL when building the frontend. Set backend `CORS_ORIGINS` to the exact frontend origin, without a path, for example `https://demo.example.com`. The backend reads a comma-separated list. Set `DATABASE_URL`, `SECRET_KEY`, `AI_MODE`, `AI_PROVIDER`, and the selected provider's key (`OPENAI_API_KEY` or `GEMINI_API_KEY`) in the hosting provider's secret/environment settings, never in frontend code or a checked-in file. Keep `AI_MODE=demo` for a no-key showcase.

The current public token top-up route is deliberately a prototype credit mechanism, not production billing. Before opening a hosted service to the public, add real authentication protections, rate limits, email verification, migration management, payment-provider confirmation, durable transaction records, backups, and monitoring. Do not expose the current open registration and simulated-credit prototype as a production financial marketplace.

## 7. Current limits and next engineering steps

- The complete registration-to-review story on `/simulation` uses fictional temporary actors and does not create production records.
- The marketplace has persistent deterministic negotiations, but provider counters are generated by local rules; there is no live provider-side agent in a negotiation yet.
- User-created listings are metadata and do not install runnable code. Only built-in handlers execute.
- Live model responses need a valid configured provider key and backend network access. Demo examples do not use a model and do not influence trust scores.
- Demo token top-ups are not real payments, and credits are not cryptocurrency. Back up the database and use managed migrations when hosting.
- Verified marketplace reviews require a successful live invocation by that reviewer. The simulation's review is separate and illustrative.
- Provider counters currently come from deterministic marketplace rules rather than a live provider agent; signed machine credentials, external agent protocols, real payments, and automated dispute handling are not implemented.
- Hosting CORS is configurable using `CORS_ORIGINS`; deployed frontend builds need `REACT_APP_API_URL` set to the API's HTTPS address.

For a production-oriented next step, add stronger machine identities, provider-side autonomous counter policies, a human audit/override view, dispute handling, and versioned deployment migrations. Keep the isolated sandbox route available as a no-key pitch demo.
