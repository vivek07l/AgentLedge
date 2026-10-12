from src.database.models import Agent, AgentReview, AutonomousExecutionPolicy, OAuthActionApproval, User
from src.auth.security import get_password_hash
from tests.test_oauth_mcp import REDIRECT_URI, RESOURCE, _authorize
import pytest


@pytest.fixture(autouse=True)
def reset_test_oauth_rate_limiter():
    import src.main as main
    main._oauth_rate_events.clear()
    yield
    main._oauth_rate_events.clear()


def _oauth(client, db, username):
    client_id, verifier, code = _authorize(
        client, db, username=username, scope="marketplace:read marketplace:write",
    )
    result = client.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
        "client_id": client_id, "code_verifier": verifier, "resource": RESOURCE,
    })
    assert result.status_code == 200, result.text
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def _website_login(client, username):
    result = client.post("/token", data={"username": username, "password": "Safe-Test-Password-2026!"})
    assert result.status_code == 200, result.text
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def _provider_listing(client, db, name="Policy Test Gemini", price=8):
    provider = client.post("/users/register", json={
        "username": "policy_provider", "email": "policy_provider@example.com",
        "password": "Safe-Test-Password-2026!", "is_developer": True,
    })
    assert provider.status_code == 200, provider.text
    provider_headers = _website_login(client, "policy_provider")
    listing = client.post("/agents/create", headers=provider_headers, json={
        "name": name, "description": "Gemini policy integration test listing",
        "category": "Productivity", "capabilities": "summarization", "price": price,
        "minimum_price": 3,
    })
    assert listing.status_code == 200, listing.text
    row = db.query(Agent).filter(Agent.id == listing.json()["id"]).one()
    row.implementation_key = "gemini_text_summarizer"
    db.commit()
    return row.id


def _enable_policy(client, website_headers, *, allowed_categories=None, allowed_listing_ids=None, **overrides):
    policy = {
        "enabled": True, "max_task_budget": 8, "max_offer_price": 8, "max_daily_spend": 8,
        "allowed_categories": allowed_categories or [], "allowed_listing_ids": allowed_listing_ids or [],
        "max_negotiation_attempts": 2, "max_execution_retries": 0, "auto_review": False,
    }
    policy.update(overrides)
    return client.patch("/users/me/autonomous-policy", headers=website_headers, json=policy)


def test_policy_defaults_disabled_and_requires_explicit_allowlist(client, test_db):
    oauth = _oauth(client, test_db, "policy_defaults")
    website = _website_login(client, "policy_defaults")
    defaults = client.get("/users/me/autonomous-policy", headers=oauth)
    assert defaults.status_code == 200, defaults.text
    assert defaults.json()["enabled"] is False
    assert client.patch("/users/me/autonomous-policy", headers=website, json={"enabled": True}).status_code == 422
    user_id = test_db.query(User).filter_by(username="policy_defaults").one().id
    assert test_db.query(AutonomousExecutionPolicy).filter_by(user_id=user_id).count() == 0


def test_manual_approval_remains_pending_until_owner_enables_policy(client, test_db):
    oauth = _oauth(client, test_db, "policy_transition_buyer")
    website = _website_login(client, "policy_transition_buyer")
    agent_id = _provider_listing(client, test_db)
    funded = client.post("/tokens/purchase", headers=website, json={"amount": 20})
    assert funded.status_code == 200, funded.text
    payload = {"agent_id": agent_id, "buyer_budget": 8, "initial_offer": 3}

    pending = client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "start_negotiation", "payload": payload,
    })
    assert pending.status_code == 200 and pending.json()["status"] == "pending"
    website_pending = client.get("/users/me/action-approvals", headers=website)
    assert website_pending.status_code == 200 and len(website_pending.json()) == 1

    enabled = _enable_policy(client, website, allowed_categories=["Productivity"])
    assert enabled.status_code == 200, enabled.text
    assert client.get("/users/me/action-approvals", headers=website).json() == []
    approval = test_db.query(OAuthActionApproval).filter_by(id=pending.json()["approval_id"]).one()
    assert approval.status == "cancelled"

    # The policy authorizes the exact next action without creating another
    # pending approval, while authentication and policy checks remain active.
    authorized = client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "start_negotiation", "payload": payload,
    })
    assert authorized.status_code == 200 and authorized.json()["autonomous_authorized"] is True
    assert test_db.query(OAuthActionApproval).count() == 1


def test_autonomous_gemini_flow_uses_policy_limits_settlement_and_evidence_review(client, test_db, monkeypatch):
    import src.main as main

    oauth = _oauth(client, test_db, "policy_buyer")
    website = _website_login(client, "policy_buyer")
    agent_id = _provider_listing(client, test_db)
    funded = client.post("/tokens/purchase", headers=website, json={"amount": 20})
    assert funded.status_code == 200, funded.text
    configured = _enable_policy(client, website, allowed_categories=["Productivity"], auto_review=True,
                                max_execution_retries=1)
    assert configured.status_code == 200, configured.text

    service_policy = client.get("/users/me/autonomous-policy", headers=oauth)
    assert service_policy.status_code == 200 and service_policy.json()["enabled"] is True
    balance = client.get("/users/me/marketplace-balance", headers=oauth)
    assert balance.status_code == 200 and balance.json()["token_balance"] == 20

    start_payload = {"agent_id": agent_id, "buyer_budget": 8, "initial_offer": 6}
    authorized = client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "start_negotiation", "payload": start_payload,
    })
    assert authorized.status_code == 200, authorized.text
    assert authorized.json()["autonomous_authorized"] is True
    assert test_db.query(OAuthActionApproval).count() == 0
    started = client.post("/negotiations", headers=oauth, json=start_payload)
    assert started.status_code == 200, started.text
    negotiation = started.json()
    assert negotiation["status"] == "awaiting_buyer"
    counter = next(item["amount"] for item in reversed(negotiation["offers"]) if item["actor_role"] == "provider" and item["action"] == "counter")
    assert counter <= 8
    accepted_gate = client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "accept_negotiation", "payload": {"negotiation_id": negotiation["id"]},
    })
    assert accepted_gate.status_code == 200 and accepted_gate.json()["autonomous_authorized"] is True
    accepted = client.post(f"/negotiations/{negotiation['id']}/accept", headers=oauth)
    assert accepted.status_code == 200 and accepted.json()["status"] == "accepted"
    price = accepted.json()["agreed_price"]

    monkeypatch.setattr(main, "_gemini_summarizer_is_configured", lambda: True)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    monkeypatch.setattr(main, "selected_provider", lambda: "gemini")
    monkeypatch.setattr(main, "selected_model", lambda: "gemini-test-model")
    calls = []
    async def gemini(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("Transient mocked Gemini failure")
        return {"output_text": "Decisions: release Friday only if both bugs are resolved. Action: test both bugs.", "tokens_used": 19}
    monkeypatch.setattr(main, "call_builtin_agent", gemini)
    invocation_payload = {
        "agent_id": agent_id, "negotiation_id": negotiation["id"],
        "input_data": {"input_text": "Notes to summarize"}, "idempotency_key": "policy-flow-exactly-once",
    }
    invocation_gate = client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "invoke_service", "payload": invocation_payload,
    })
    assert invocation_gate.status_code == 200 and invocation_gate.json()["autonomous_authorized"] is True
    response = client.post(f"/agents/invoke/{agent_id}", headers={**oauth, "Idempotency-Key": invocation_payload["idempotency_key"]}, json={
        "input_text": "Notes to summarize", "negotiation_id": negotiation["id"],
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["provider"] == "gemini" and result["execution_mode"] == "live"
    assert result["charged_tokens"] == price and result["settlement_status"] == "settled"
    assert "both bugs" in result["output_text"]
    assert result["automatic_review"]["rating"] == 5
    assert calls == [1, 1]
    assert test_db.query(AgentReview).filter_by(invocation_id=result["invocation_id"]).one().review_text.startswith("Automated execution review:")
    from src.database.models import TokenTransaction
    transactions = test_db.query(TokenTransaction).filter_by(invocation_id=result["invocation_id"]).all()
    assert len(transactions) == 1 and transactions[0].status == "settled"
    assert test_db.query(AgentReview).filter_by(invocation_id=result["invocation_id"]).count() == 1
    assert test_db.query(OAuthActionApproval).count() == 0
    replay = client.post(f"/agents/invoke/{agent_id}", headers={**oauth, "Idempotency-Key": invocation_payload["idempotency_key"]}, json={
        "input_text": "Notes to summarize", "negotiation_id": negotiation["id"],
    })
    assert replay.status_code == 200 and replay.json()["invocation_id"] == result["invocation_id"]
    assert calls == [1, 1]


def test_autonomous_policy_rejects_price_over_cap_and_unauthorized_user(client, test_db, monkeypatch):
    import src.main as main
    monkeypatch.setattr(main, "_gemini_summarizer_is_configured", lambda: True)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    buyer_oauth = _oauth(client, test_db, "policy_cap_buyer")
    buyer_website = _website_login(client, "policy_cap_buyer")
    agent_id = _provider_listing(client, test_db, name="Policy Cap Service", price=8)
    assert client.post("/tokens/purchase", headers=buyer_website, json={"amount": 30}).status_code == 200
    assert _enable_policy(client, buyer_website, allowed_listing_ids=[agent_id], max_task_budget=8,
                          max_offer_price=6, max_daily_spend=12).status_code == 200
    start = {"agent_id": agent_id, "buyer_budget": 8, "initial_offer": 6}
    started = client.post("/negotiations", headers=buyer_oauth, json=start)
    assert started.status_code == 403
    assert "limit" in started.json()["detail"]
    assert test_db.query(AgentReview).count() == 0

    outsider = _oauth(client, test_db, "policy_cap_outsider")
    assert client.get("/users/me/autonomous-policy", headers=outsider).json()["enabled"] is False
    allowed_start = client.post("/negotiations", headers=buyer_oauth, json={
        "agent_id": agent_id, "buyer_budget": 6, "initial_offer": 4,
    })
    assert allowed_start.status_code == 200, allowed_start.text
    negotiation_id = allowed_start.json()["id"]
    accept_gate = client.post("/mcp/action-approvals", headers=buyer_oauth, json={
        "action": "accept_negotiation", "payload": {"negotiation_id": negotiation_id},
    })
    assert accept_gate.status_code == 200, accept_gate.text
    assert client.post(f"/negotiations/{negotiation_id}/accept", headers=buyer_oauth).status_code == 200
    denied = client.post(f"/agents/invoke/{agent_id}", headers=outsider, json={
        "input_text": "Unauthorized attempt", "negotiation_id": negotiation_id,
    })
    assert denied.status_code == 403
    assert "authorized negotiation" in denied.json()["detail"].lower()


def test_autonomous_policy_stops_without_balance_or_unbacked_funding(client, test_db):
    oauth = _oauth(client, test_db, "policy_empty_balance")
    website = _website_login(client, "policy_empty_balance")
    agent_id = _provider_listing(client, test_db, name="No Funds Service", price=6)
    configured = _enable_policy(client, website, allowed_listing_ids=[agent_id], max_task_budget=6,
                                max_offer_price=6, max_daily_spend=6)
    assert configured.status_code == 200, configured.text
    attempt = client.post("/negotiations", headers=oauth, json={
        "agent_id": agent_id, "buyer_budget": 6, "initial_offer": 5,
    })
    assert attempt.status_code == 402, attempt.text
    assert client.get("/users/me/marketplace-balance", headers=oauth).json()["token_balance"] == 0
    assert test_db.query(OAuthActionApproval).count() == 0
    from src.database.models import Negotiation
    assert test_db.query(Negotiation).filter_by(agent_id=agent_id).count() == 0


def test_daily_spend_limit_blocks_invocation_before_token_reservation(client, test_db, monkeypatch):
    import src.main as main
    from src.database.models import AgentInvocation, TokenTransaction

    oauth = _oauth(client, test_db, "policy_daily_buyer")
    website = _website_login(client, "policy_daily_buyer")
    agent_id = _provider_listing(client, test_db, name="Daily Cap Service", price=8)
    assert client.post("/tokens/purchase", headers=website, json={"amount": 20}).status_code == 200
    # Create the accepted agreement while the account is in its existing manual mode.
    negotiation = client.post("/negotiations", headers=website, json={
        "agent_id": agent_id, "buyer_budget": 8, "initial_offer": 6,
    })
    assert negotiation.status_code == 200, negotiation.text
    negotiation_id = negotiation.json()["id"]
    assert client.post(f"/negotiations/{negotiation_id}/accept", headers=website).json()["status"] == "accepted"
    price = test_db.query(__import__("src.database.models", fromlist=["Negotiation"]).Negotiation).filter_by(id=negotiation_id).one().agreed_price
    configured = _enable_policy(client, website, allowed_listing_ids=[agent_id], max_task_budget=8,
                                max_offer_price=8, max_daily_spend=price - 1)
    assert configured.status_code == 200, configured.text
    monkeypatch.setattr(main, "_gemini_summarizer_is_configured", lambda: True)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    denied = client.post("/agents/invoke/" + str(agent_id), headers={**oauth, "Idempotency-Key": "daily-cap-run"}, json={
        "input_text": "Daily cap test", "negotiation_id": negotiation_id,
    })
    assert denied.status_code == 403
    assert "daily autonomous spending limit" in denied.json()["detail"]
    assert client.get("/users/me/marketplace-balance", headers=oauth).json()["token_balance"] == 20
    assert test_db.query(AgentInvocation).filter_by(negotiation_id=negotiation_id).count() == 0
    assert test_db.query(TokenTransaction).filter_by(negotiation_id=negotiation_id).count() == 0


def test_autonomous_provider_failure_releases_tokens_and_does_not_review(client, test_db, monkeypatch):
    import src.main as main
    from src.database.models import AgentInvocation, TokenTransaction, Negotiation

    oauth = _oauth(client, test_db, "policy_failed_buyer")
    website = _website_login(client, "policy_failed_buyer")
    agent_id = _provider_listing(client, test_db, name="Failing Gemini Service", price=4)
    assert client.post("/tokens/purchase", headers=website, json={"amount": 10}).status_code == 200
    configured = _enable_policy(client, website, allowed_listing_ids=[agent_id], max_task_budget=4,
                                max_offer_price=4, max_daily_spend=4, max_execution_retries=0,
                                auto_review=True)
    assert configured.status_code == 200, configured.text
    start_payload = {"agent_id": agent_id, "buyer_budget": 4, "initial_offer": 4}
    assert client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "start_negotiation", "payload": start_payload,
    }).json()["autonomous_authorized"] is True
    deal = client.post("/negotiations", headers=oauth, json=start_payload)
    assert deal.status_code == 200 and deal.json()["status"] == "accepted"
    negotiation_id = deal.json()["id"]
    monkeypatch.setattr(main, "_gemini_summarizer_is_configured", lambda: True)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    monkeypatch.setattr(main, "selected_provider", lambda: "gemini")
    async def provider_failure(*args, **kwargs):
        raise RuntimeError("mocked Gemini outage")
    monkeypatch.setattr(main, "call_builtin_agent", provider_failure)
    invocation_payload = {"agent_id": agent_id, "negotiation_id": negotiation_id,
                          "input_data": {"input_text": "Please summarize"}, "idempotency_key": "failure-run"}
    assert client.post("/mcp/action-approvals", headers=oauth, json={
        "action": "invoke_service", "payload": invocation_payload,
    }).json()["autonomous_authorized"] is True
    before = client.get("/users/me/marketplace-balance", headers=oauth).json()["token_balance"]
    failed = client.post(f"/agents/invoke/{agent_id}", headers={**oauth, "Idempotency-Key": "failure-run"}, json={
        "input_text": "Please summarize", "negotiation_id": negotiation_id,
    })
    assert failed.status_code == 502
    assert client.get("/users/me/marketplace-balance", headers=oauth).json()["token_balance"] == before
    invocation = test_db.query(AgentInvocation).filter_by(idempotency_key="failure-run").one()
    assert invocation.status == "failed" and invocation.review is None
    transaction = test_db.query(TokenTransaction).filter_by(invocation_id=invocation.id).one()
    assert transaction.status == "released"
