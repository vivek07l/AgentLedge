import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from src.auth.security import get_password_hash
from src.database.models import Agent, User


RESOURCE = "http://127.0.0.1:8011/mcp"
REDIRECT_URI = "http://127.0.0.1:8765/oauth/callback"


def _pkce_pair():
    verifier = "A" * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _authorize(client, db, *, username="oauth_reader", scope="marketplace:read"):
    db.add(User(username=username, email=f"{username}@example.com", hashed_password=get_password_hash("Safe-Test-Password-2026!"), is_active=True))
    db.commit()
    registered = client.post("/oauth/register", json={"redirect_uris": [REDIRECT_URI]})
    assert registered.status_code == 201, registered.text
    client_id = registered.json()["client_id"]
    verifier, challenge = _pkce_pair()
    params = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "state": "test-state-123", "scope": scope, "resource": RESOURCE,
        "code_challenge": challenge, "code_challenge_method": "S256",
    }
    login = client.get("/oauth/authorize", params=params)
    assert login.status_code == 200
    form = {**params, "created_at": __import__("re").search(r'name="created_at" value="([^"]+)', login.text).group(1),
            "csrf": client.cookies["agentledge_oauth_csrf"], "username": username,
            "password": "Safe-Test-Password-2026!"}
    approved = client.post("/oauth/authorize", data=form, follow_redirects=False)
    assert approved.status_code == 303, approved.text
    callback = parse_qs(urlparse(approved.headers["location"]).query)
    assert callback["state"] == ["test-state-123"]
    return client_id, verifier, callback["code"][0]


def _approve_action(client, oauth_headers, website_headers, action, payload):
    pending = client.post("/mcp/action-approvals", headers=oauth_headers, json={"action": action, "payload": payload})
    assert pending.status_code == 200, pending.text
    approval_id = pending.json()["approval_id"]
    decision = client.post(f"/users/me/action-approvals/{approval_id}", headers=website_headers, json={"decision": "approve"})
    assert decision.status_code == 200, decision.text
    return {"X-User-Approval": approval_id}


def test_oauth_pkce_exchange_is_per_user_scoped_and_read_only(client, test_db):
    client_id, verifier, code = _authorize(client, test_db)
    wrong = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT_URI, "client_id": client_id, "code_verifier": "B" * 64, "resource": RESOURCE})
    assert wrong.status_code == 400
    wrong_resource = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT_URI, "client_id": client_id, "code_verifier": verifier, "resource": "https://wrong.example/mcp"})
    assert wrong_resource.status_code == 400
    exchanged = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT_URI, "client_id": client_id, "code_verifier": verifier, "resource": RESOURCE})
    assert exchanged.status_code == 200, exchanged.text
    data = exchanged.json()
    assert data["scope"] == "marketplace:read"
    assert data["expires_in"] == 900
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    assert client.get("/agents", headers=headers).status_code == 200
    assert client.get("/marketplace/categories", headers=headers).status_code == 200
    assert client.post("/tokens/purchase", headers=headers, json={"amount": 10}).status_code == 403
    assert client.get("/users/me", headers=headers).status_code == 403
    introspection = client.post("/oauth/introspect", headers=headers)
    assert introspection.status_code == 200
    claims = introspection.json()
    assert claims["active"] is True
    assert claims["iss"] == "http://127.0.0.1:8000"
    assert claims["aud"] == RESOURCE
    assert claims["sub"] == str(test_db.query(User).filter_by(username="oauth_reader").one().id)
    replay = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT_URI, "client_id": client_id, "code_verifier": verifier, "resource": RESOURCE})
    assert replay.status_code == 400


def test_oauth_registration_rejects_untrusted_redirects(client):
    response = client.post("/oauth/register", json={"redirect_uris": ["http://evil.example/callback"]})
    assert response.status_code == 400


def test_oauth_authorize_accepts_canonical_live_mcp_resource_and_rejects_legacy_host(client, test_db, monkeypatch):
    import src.main as main

    canonical_resource = "https://agentsledge-mcp.onrender.com/mcp"
    legacy_resource = "https://agentmesh-mcp.onrender.com/mcp"
    monkeypatch.setattr(main.settings, "AGENTMESH_MCP_RESOURCE_URL", canonical_resource)
    db_user = User(username="oauth_hostname_regression", email="oauth_hostname_regression@example.com",
                   hashed_password=get_password_hash("Safe-Test-Password-2026!"), is_active=True)
    test_db.add(db_user)
    test_db.commit()
    client_id = client.post("/oauth/register", json={"redirect_uris": [REDIRECT_URI]}).json()["client_id"]
    _, challenge = _pkce_pair()
    request = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "state": "hostname-regression", "scope": "marketplace:read",
        "code_challenge": challenge, "code_challenge_method": "S256",
    }

    accepted = client.get("/oauth/authorize", params={**request, "resource": canonical_resource})
    assert accepted.status_code == 200, accepted.text
    assert "AgentsLedge" in accepted.text
    rejected = client.get("/oauth/authorize", params={**request, "resource": legacy_resource})
    assert rejected.status_code == 400
    assert "supported marketplace scopes" in rejected.json()["detail"]


def test_oauth_authorize_rejects_wrong_resource_and_scope(client, test_db):
    db_user = User(username="oauth_reader", email="oauth_reader@example.com", hashed_password=get_password_hash("x"), is_active=True)
    test_db.add(db_user)
    test_db.commit()
    client_id = client.post("/oauth/register", json={"redirect_uris": [REDIRECT_URI]}).json()["client_id"]
    _, challenge = _pkce_pair()
    base = {"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
            "state": "state", "scope": "marketplace:read", "code_challenge": challenge,
            "code_challenge_method": "S256"}
    assert client.get("/oauth/authorize", params={**base, "resource": "https://another.example/mcp"}).status_code == 400
    assert client.get("/oauth/authorize", params={**base, "resource": RESOURCE, "scope": "marketplace:write"}).status_code == 400
    assert client.get("/oauth/authorize", params={**base, "resource": RESOURCE, "scope": "marketplace:admin"}).status_code == 400


def test_oauth_consent_page_describes_read_and_write_permissions(client):
    registered = client.post("/oauth/register", json={"redirect_uris": [REDIRECT_URI]})
    client_id = registered.json()["client_id"]
    _, challenge = _pkce_pair()
    base = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "state": "consent-page-test", "resource": RESOURCE,
        "code_challenge": challenge, "code_challenge_method": "S256",
    }

    read_page = client.get("/oauth/authorize", params={**base, "scope": "marketplace:read"})
    assert read_page.status_code == 200
    read_text = read_page.text.lower()
    for permission in (
        "search and compare public marketplace listings",
        "view service details, reputation and reviews",
        "view your own negotiation status and invocation results",
    ):
        assert permission in read_text
    assert "accept or reject negotiations" not in read_text
    assert "spending marketplace tokens" not in read_text

    write_page = client.get(
        "/oauth/authorize",
        params={**base, "scope": "marketplace:read marketplace:write"},
    )
    assert write_page.status_code == 200
    write_text = write_page.text.lower()
    for permission in (
        "create negotiations and submit offers",
        "accept or reject negotiations",
        "invoke services, potentially spending marketplace tokens",
        "submit reviews for eligible completed executions",
    ):
        assert permission in write_text


def test_oauth_write_actions_need_a_matching_one_time_website_approval(client, test_db):
    oauth_client_id, verifier, code = _authorize(
        client, test_db, username="approval_buyer", scope="marketplace:read marketplace:write",
    )
    exchange = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
        "client_id": oauth_client_id, "code_verifier": verifier, "resource": RESOURCE,
    })
    assert exchange.status_code == 200, exchange.text
    oauth_headers = {"Authorization": f"Bearer {exchange.json()['access_token']}"}

    provider = client.post("/users/register", json={
        "username": "approval_provider", "email": "approval_provider@example.com",
        "password": "Safe-Test-Password-2026!", "is_developer": True,
    })
    assert provider.status_code == 200, provider.text
    provider_token = client.post("/token", data={
        "username": "approval_provider", "password": "Safe-Test-Password-2026!",
    }).json()["access_token"]
    listing = client.post("/agents/create", headers={"Authorization": f"Bearer {provider_token}"}, json={
        "name": "Approval Test Service", "description": "Test the human approval gate",
        "category": "Testing", "capabilities": "approval", "price": 10, "minimum_price": 8,
    })
    assert listing.status_code == 200, listing.text

    start_payload = {"agent_id": listing.json()["id"], "buyer_budget": 10, "initial_offer": 8}
    pending = client.post("/mcp/action-approvals", headers=oauth_headers, json={
        "action": "start_negotiation", "payload": start_payload,
    })
    assert pending.status_code == 200, pending.text
    approval_id = pending.json()["approval_id"]
    assert pending.json()["status"] == "pending"
    assert client.post("/negotiations", headers=oauth_headers, json=start_payload).status_code == 403
    assert client.get("/users/me/action-approvals", headers=oauth_headers).status_code == 403

    website_token = client.post("/token", data={
        "username": "approval_buyer", "password": "Safe-Test-Password-2026!",
    }).json()["access_token"]
    website_headers = {"Authorization": f"Bearer {website_token}"}
    listed = client.get("/users/me/action-approvals", headers=website_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["payload"]["initial_offer"] == 8
    assert listed.json()[0]["payload"]["service_name"] == "Approval Test Service"

    approved = client.post(f"/users/me/action-approvals/{approval_id}", headers=website_headers, json={"decision": "approve"})
    assert approved.status_code == 200
    changed = client.post("/negotiations", headers={**oauth_headers, "X-User-Approval": approval_id}, json={
        **start_payload, "initial_offer": 9,
    })
    assert changed.status_code == 409
    created = client.post("/negotiations", headers={**oauth_headers, "X-User-Approval": approval_id}, json=start_payload)
    assert created.status_code == 200, created.text
    assert created.json()["buyer_budget"] == 10
    replay = client.post("/negotiations", headers={**oauth_headers, "X-User-Approval": approval_id}, json=start_payload)
    assert replay.status_code == 403


def test_oauth_scope_consent_persists_read_write_and_mcp_writes_are_independently_authorized(client, test_db, monkeypatch):
    import src.main as main

    metadata = client.get("/.well-known/oauth-authorization-server").json()
    assert metadata["scopes_supported"] == ["marketplace:read", "marketplace:write"]
    read_client_id, read_verifier, read_code = _authorize(client, test_db, username="read_only")
    read_token = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": read_code,
        "redirect_uri": REDIRECT_URI, "client_id": read_client_id, "code_verifier": read_verifier, "resource": RESOURCE}).json()["access_token"]
    read_headers = {"Authorization": f"Bearer {read_token}"}
    assert client.get("/agents", headers=read_headers).status_code == 200
    assert client.post("/negotiations", headers=read_headers, json={"agent_id": 1, "buyer_budget": 10, "initial_offer": 5}).status_code == 403

    client_id, verifier, code = _authorize(client, test_db, username="write_user", scope="marketplace:read marketplace:write")
    token_response = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT_URI, "client_id": client_id, "code_verifier": verifier, "resource": RESOURCE})
    assert token_response.status_code == 200, token_response.text
    assert token_response.json()["scope"] == "marketplace:read marketplace:write"
    write_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    provider = client.post("/users/register", json={"username": "write_provider", "email": "write_provider@example.com",
        "password": "Safe-Test-Password-2026!", "is_developer": True})
    assert provider.status_code == 200
    provider_login = client.post("/token", data={"username": "write_provider", "password": "Safe-Test-Password-2026!"}).json()
    listing = client.post("/agents/create", headers={"Authorization": f"Bearer {provider_login['access_token']}"}, json={
        "name": "Resume Reviewer", "description": "OAuth workflow listing", "category": "Career",
        "capabilities": "resume review", "price": 10, "minimum_price": 8,
    })
    assert listing.status_code == 200, listing.text
    service = listing.json()
    test_db.query(Agent).filter(Agent.id == service["id"]).one().implementation_key = "resume_reviewer"
    test_db.commit()
    # Token purchase is intentionally outside the MCP OAuth allowlist.
    assert client.post("/tokens/purchase", headers=write_headers, json={"amount": 20}).status_code == 403
    # Use a normal website session to provision demo funds; MCP cannot do this.
    user_login = client.post("/token", data={"username": "write_user", "password": "Safe-Test-Password-2026!"}).json()
    website_headers = {"Authorization": f"Bearer {user_login['access_token']}"}
    assert client.post("/tokens/purchase", headers=website_headers, json={"amount": 20}).status_code == 200

    start_payload = {"agent_id": service["id"], "buyer_budget": 12, "initial_offer": 1}
    start_approval = _approve_action(client, write_headers, website_headers, "start_negotiation", start_payload)
    started = client.post("/negotiations", headers={**write_headers, **start_approval}, json=start_payload)
    assert started.status_code == 200, started.text
    negotiation = started.json()
    assert negotiation["status"] == "awaiting_buyer"
    assert client.get(f"/negotiations/{negotiation['id']}", headers=write_headers).status_code == 200
    assert client.post(f"/negotiations/{negotiation['id']}/accept", headers=read_headers).status_code == 403
    accept_approval = _approve_action(client, write_headers, website_headers, "accept_negotiation", {
        "negotiation_id": negotiation["id"],
    })
    accepted = client.post(f"/negotiations/{negotiation['id']}/accept", headers={**write_headers, **accept_approval})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    async def live_result(*args, **kwargs):
        return {"output_text": "Persisted provider result", "tokens_used": 4}
    monkeypatch.setattr(main, "call_builtin_agent", live_result)
    invoke_input = {"input_text": "Review my resume"}
    invoke_key = "oauth-write-run-1"
    invoke_approval = _approve_action(client, write_headers, website_headers, "invoke_service", {
        "agent_id": service["id"], "negotiation_id": negotiation["id"],
        "input_data": invoke_input, "idempotency_key": invoke_key,
    })
    invoked = client.post(f"/agents/invoke/{service['id']}", headers={**write_headers, **invoke_approval, "Idempotency-Key": invoke_key}, json={
        **invoke_input, "negotiation_id": negotiation["id"],
    })
    assert invoked.status_code == 200, invoked.text
    assert invoked.json()["execution_mode"] == "live"
    assert invoked.json()["provider"] == main.selected_provider()
    invocation_id = invoked.json()["invocation_id"]
    stored_result = client.get(f"/users/me/invocations/{invocation_id}", headers=write_headers)
    assert stored_result.status_code == 200, stored_result.text
    assert stored_result.json()["result"]["output_text"] == "Persisted provider result"
    outsider_client, outsider_verifier, outsider_code = _authorize(client, test_db, username="write_outsider", scope="marketplace:read marketplace:write")
    outsider_token = client.post("/oauth/token", data={"grant_type": "authorization_code", "code": outsider_code,
        "redirect_uri": REDIRECT_URI, "client_id": outsider_client, "code_verifier": outsider_verifier, "resource": RESOURCE}).json()["access_token"]
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    assert client.get(f"/negotiations/{negotiation['id']}", headers=outsider_headers).status_code == 403
    assert client.get(f"/users/me/invocations/{invocation_id}", headers=outsider_headers).status_code == 404
    review_payload = {"agent_id": service["id"], "invocation_id": invocation_id, "rating": 5, "review_text": "Clear and helpful"}
    review_approval = _approve_action(client, write_headers, website_headers, "submit_review", review_payload)
    review = client.post(f"/agents/{service['id']}/reviews", headers={**write_headers, **review_approval}, json={
        "invocation_id": invocation_id, "rating": 5, "review_text": "Clear and helpful",
    })
    assert review.status_code == 201, review.text
    duplicate_review_approval = client.post("/mcp/action-approvals", headers=write_headers, json={
        "action": "submit_review", "payload": review_payload,
    })
    assert duplicate_review_approval.status_code == 409


def test_oauth_csrf_form_is_bound_to_signed_authorization_request(client, test_db):
    client_id, _, _ = _authorize(client, test_db)
    assert client_id
