# AgentLedge frontend

React and TypeScript marketplace UI. Main routes:

- `/marketplace` — discover and compare service listings.
- `/simulation` — run the isolated agent registration, provider comparison, negotiation, simulated-token, delivery, and demo-review presentation.
- `/auth/register` and `/auth/login` — create or access a service-user/provider account.
- `/provider/listings` — manage provider-owned listings.

Run from this directory with `npm start`. The API defaults to `http://localhost:8000`; set `REACT_APP_API_URL` before building when the API is hosted elsewhere. For project setup, account flows, deployment notes, and sandbox limitations, see [`../AgentLedge_Complete_Guide.md`](../AgentLedge_Complete_Guide.md).
