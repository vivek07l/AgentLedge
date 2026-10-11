from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest


def account(client, is_provider=False):
    username = f"acct_{uuid4().hex[:10]}"
    password = "Safe-Test-Password-2026!"
    created = client.post("/users/register", json={
        "username": username, "email": f"{username}@example.com",
        "password": password, "is_developer": is_provider,
    })
    assert created.status_code == 200, created.text
    logged_in = client.post("/token", data={"username": username, "password": password})
    assert logged_in.status_code == 200, logged_in.text
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


def listing(client, headers, test_db, price=10, minimum=8):
    response = client.post("/agents/create", headers=headers, json={
        "name": "Resume Reviewer", "description": "Supported service",
        "category": "Career", "capabilities": "resume review",
        "price": price, "minimum_price": minimum,
    })
    assert response.status_code == 200, response.text
    from src.database.models import Agent
    stored = test_db.query(Agent).filter(Agent.id == response.json()["id"]).one()
    stored.implementation_key = "resume_reviewer"
    test_db.commit()
    return response.json()


def accepted_deal(client, buyer, service):
    response = client.post("/negotiations", headers=buyer, json={
        "agent_id": service["id"], "buyer_budget": 12, "initial_offer": 10,
    })
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    return response.json()


def test_negotiation_is_persistent_and_enforces_provider_floor_budget_and_round_limit(client, test_db):
    provider = account(client, is_provider=True)
    buyer = account(client)
    service = listing(client, provider, test_db)

    too_small = client.post("/negotiations", headers=buyer, json={
        "agent_id": service["id"], "buyer_budget": 7.99, "initial_offer": 5,
    })
    assert too_small.status_code == 422
    assert "minimum price" in too_small.json()["detail"]

    start = client.post("/negotiations", headers=buyer, json={
        "agent_id": service["id"], "buyer_budget": 10, "initial_offer": 1,
    })
    assert start.status_code == 200, start.text
    negotiation = start.json()
    assert negotiation["status"] == "awaiting_buyer"
    assert negotiation["offers"][-1]["actor_role"] == "provider"
    assert negotiation["offers"][-1]["amount"] >= 8
    accept = client.post(f"/negotiations/{negotiation['id']}/accept", headers=buyer)
    assert accept.status_code == 200
    assert accept.json()["agreed_price"] >= 8
    assert client.get(f"/negotiations/{negotiation['id']}", headers=provider).json() == accept.json()

    rounds = client.post("/negotiations", headers=buyer, json={
        "agent_id": service["id"], "buyer_budget": 10, "initial_offer": 1,
    }).json()
    for _ in range(5):
        response = client.post(f"/negotiations/{rounds['id']}/offers", headers=buyer, json={"amount": 1})
        assert response.status_code == 200, response.text
        rounds = response.json()
    assert rounds["round_count"] == 5
    assert rounds["status"] == "failed"


def test_successful_live_execution_settles_once_at_agreed_price_and_persists_history(client, test_db, monkeypatch):
    import src.main as main

    provider = account(client, is_provider=True)
    buyer = account(client)
    service = listing(client, provider, test_db, price=10, minimum=7)
    credits = client.post("/tokens/purchase", headers=buyer, json={"amount": 25})
    assert credits.status_code == 200
    deal = accepted_deal(client, buyer, service)
    calls = {"count": 0}

    async def live_result(*args, **kwargs):
        calls["count"] += 1
        return {"output_text": "A genuine test-provider result", "tokens_used": 11}

    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    monkeypatch.setattr(main, "call_builtin_agent", live_result)
    key = "same-operation-key"
    payload = {"input_text": "Review this resume", "negotiation_id": deal["id"]}
    result = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": key}, json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["output_text"] == "A genuine test-provider result"
    assert result.json()["charged_tokens"] == 10
    assert result.json()["settlement_status"] == "settled"
    assert result.json()["remaining_balance"] == 15

    retry = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": key}, json=payload)
    assert retry.status_code == 200, retry.text
    assert retry.json()["invocation_id"] == result.json()["invocation_id"]
    assert calls["count"] == 1
    changed_input = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": key}, json={
        "input_text": "a different task", "negotiation_id": deal["id"],
    })
    assert changed_input.status_code == 409
    assert client.get("/users/me", headers=buyer).json()["token_balance"] == 15
    assert client.get("/users/me", headers=provider).json()["token_balance"] == 10

    history = client.get("/users/me/invocations", headers=buyer)
    assert history.status_code == 200
    item = history.json()[0]
    assert item["id"] == result.json()["invocation_id"]
    assert item["execution_status"] == "succeeded"
    assert item["settlement_status"] == "settled"
    assert item["amount_charged"] == 10
    assert item["negotiation"]["id"] == deal["id"]
    assert item["transaction_id"]
    assert "A genuine test-provider result" in item["output_data"]
    provider_stats = client.get("/users/me/provider-stats", headers=provider)
    assert provider_stats.status_code == 200
    assert provider_stats.json()["settled_tokens_earned"] == 10
    analytics = client.get(f"/agents/{service['id']}/analytics", headers=provider)
    assert analytics.status_code == 200
    assert analytics.json()["time_series"][0]["succeeded"] == 1
    assert client.get(f"/agents/{service['id']}/analytics", headers=buyer).status_code == 404


def test_failed_execution_releases_reservation_and_persists_failure(client, test_db, monkeypatch):
    import src.main as main

    provider = account(client, is_provider=True)
    buyer = account(client)
    service = listing(client, provider, test_db, price=6, minimum=4)
    client.post("/tokens/purchase", headers=buyer, json={"amount": 10})
    deal = accepted_deal(client, buyer, service)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)

    async def failure(*args, **kwargs):
        raise RuntimeError("simulated provider outage")

    monkeypatch.setattr(main, "call_builtin_agent", failure)
    result = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": "insufficient-balance"}, json={
        "input_text": "Review", "negotiation_id": deal["id"], "idempotency_key": "failed-once",
    })
    assert result.status_code == 502
    assert client.get("/users/me", headers=buyer).json()["token_balance"] == 10
    history = client.get("/users/me/invocations", headers=buyer).json()
    assert history[0]["execution_status"] == "failed"
    assert history[0]["settlement_status"] == "released"
    assert history[0]["amount_charged"] == 0


def test_live_execution_with_insufficient_balance_does_not_call_provider(client, test_db, monkeypatch):
    import src.main as main

    provider = account(client, is_provider=True)
    buyer = account(client)
    service = listing(client, provider, test_db, price=6, minimum=4)
    deal = accepted_deal(client, buyer, service)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    called = {"value": False}

    async def live_result(*args, **kwargs):
        called["value"] = True
        return {"output_text": "must not run"}

    monkeypatch.setattr(main, "call_builtin_agent", live_result)
    result = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": "insufficient-balance"}, json={
        "input_text": "Review", "negotiation_id": deal["id"],
    })
    assert result.status_code == 402
    assert called["value"] is False


def test_settled_transfer_cannot_overdraw_buyer_or_duplicate_provider_credit(client, test_db, monkeypatch):
    import src.main as main

    provider = account(client, is_provider=True)
    buyer = account(client)
    service = listing(client, provider, test_db, price=6, minimum=4)
    client.post("/tokens/purchase", headers=buyer, json={"amount": 6})
    deal1 = accepted_deal(client, buyer, service)
    deal2 = accepted_deal(client, buyer, service)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)

    async def result(*args, **kwargs):
        return {"output_text": "completed", "tokens_used": 1}

    monkeypatch.setattr(main, "call_builtin_agent", result)
    first = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": "first-payment"}, json={
        "input_text": "one", "negotiation_id": deal1["id"],
    })
    assert first.status_code == 200, first.text
    second = client.post(f"/agents/invoke/{service['id']}", headers={**buyer, "Idempotency-Key": "second-payment"}, json={
        "input_text": "two", "negotiation_id": deal2["id"],
    })
    assert second.status_code == 402
    assert client.get("/users/me", headers=buyer).json()["token_balance"] == 0
    assert client.get("/users/me", headers=provider).json()["token_balance"] == 6


def test_negotiation_and_history_records_are_participant_scoped(client, test_db):
    provider = account(client, is_provider=True)
    buyer = account(client)
    outsider = account(client)
    service = listing(client, provider, test_db)
    deal = accepted_deal(client, buyer, service)
    hidden = client.get(f"/negotiations/{deal['id']}", headers=outsider)
    assert hidden.status_code == 403
    assert client.get("/users/me/invocations", headers=outsider).json() == []


def test_idempotency_also_deduplicates_free_labeled_demo_runs(client, test_db, monkeypatch):
    import src.main as main

    provider = account(client, is_provider=True)
    buyer = account(client)
    service = listing(client, provider, test_db, price=0, minimum=0)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: False)
    payload = {"input_text": "A local sample"}
    headers = {**buyer, "Idempotency-Key": "free-demo-retry"}
    first = client.post(f"/agents/invoke/{service['id']}", headers=headers, json=payload)
    second = client.post(f"/agents/invoke/{service['id']}", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["invocation_id"] == second.json()["invocation_id"]
    assert first.json()["demo_mode"] is True
    assert first.json()["execution_mode"] == "demo"
    assert first.json()["provider"] is None
    assert len(client.get("/users/me/invocations", headers=buyer).json()) == 1


def test_unmapped_listing_is_discovery_only_and_cannot_be_invoked(client):
    owner = account(client, is_provider=True)
    service = client.post("/agents/create", headers=owner, json={
        "name": "Unmapped Data Cleaner", "description": "An advertised service without an implementation",
        "category": "Data", "capabilities": "cleaning", "price": 0, "minimum_price": 0,
    })
    assert service.status_code == 200, service.text
    assert service.json()["execution_available"] is False
    result = client.post(f"/agents/invoke/{service.json()['id']}", headers=owner, json={"input_text": "clean this"})
    assert result.status_code == 409
    assert "no executable implementation" in result.json()["detail"]
    assert client.get("/users/me", headers=owner).json()["token_balance"] == 0


def test_gemini_provider_selection_requires_explicit_provider_and_model(monkeypatch):
    from types import SimpleNamespace
    import src.agents.providers as providers

    config = SimpleNamespace(
        AI_PROVIDER="gemini", AI_MODEL="gemini-test-model", OPENAI_MODEL="gpt-4.1-mini",
        GEMINI_API_KEY="test-gemini-key", OPENAI_API_KEY="",
    )
    monkeypatch.setattr(providers, "get_settings", lambda: config)
    assert providers.selected_provider() == "gemini"
    assert providers.selected_model() == "gemini-test-model"
    assert providers.has_provider_credentials() is True
    model_client = providers.create_model_client()
    assert str(model_client.base_url).startswith(providers.GEMINI_OPENAI_COMPATIBLE_BASE_URL)


def test_live_mode_without_provider_key_fails_instead_of_returning_demo(client, test_db, monkeypatch):
    import src.main as main

    monkeypatch.setattr(main.settings, "AI_MODE", "live")
    monkeypatch.setattr(main, "has_provider_credentials", lambda: False)
    monkeypatch.setattr(main, "selected_provider", lambda: "gemini")
    monkeypatch.setattr(main, "selected_model", lambda: "gemini-test-model")
    provider = account(client, is_provider=True)
    service = client.post("/agents/create", headers=provider, json={
        "name": "Resume Reviewer", "description": "A live mode configuration check",
        "category": "Career", "capabilities": "resume review", "price": 0,
    })
    assert service.status_code == 200, service.text
    from src.database.models import Agent
    test_db.query(Agent).filter(Agent.id == service.json()["id"]).one().implementation_key = "resume_reviewer"
    test_db.commit()

    status_response = client.get("/system/status")
    assert status_response.status_code == 200
    assert status_response.json()["ai_mode"] == "error"
    result = client.post(f"/agents/invoke/{service.json()['id']}", headers=provider, json={"input_text": "test"})
    assert result.status_code == 503
    assert "No demo response was substituted" in result.json()["detail"]
    assert client.get("/users/me/invocations", headers=provider).json() == []


def test_concurrent_reservations_cannot_spend_the_same_balance_twice(tmp_path):
    from src.database.models import Base, User
    from src.marketplace.settlement import reserve_buyer_tokens

    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent-ledger.sqlite3'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    with SessionLocal() as db:
        user = User(username="parallel-buyer", email="parallel@example.com", hashed_password="x", token_balance=6)
        db.add(user); db.commit(); user_id = user.id

    barrier = Barrier(2)

    def reserve_once():
        with SessionLocal() as db:
            barrier.wait()
            reserved = reserve_buyer_tokens(db, user_id, 6)
            db.commit()
            return reserved

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: reserve_once(), range(2)))
    assert sorted(outcomes) == [False, True]
    with SessionLocal() as db:
        assert db.query(User).filter(User.id == user_id).one().token_balance == 0
    engine.dispose()

