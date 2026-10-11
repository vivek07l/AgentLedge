from uuid import uuid4

from fastapi import status


def provider_headers(client):
    suffix = uuid4().hex[:10]
    username = f"provider_{suffix}"
    password = "Safe-Test-Password-2026!"
    registered = client.post("/users/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "is_developer": True,
    })
    assert registered.status_code == 200, registered.text
    login = client.post("/token", data={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_provider_can_create_listing(client):
    headers = provider_headers(client)
    response = client.post("/agents/create", headers=headers, json={
        "name": "Test Agent",
        "description": "A test agent",
        "category": "Testing",
        "capabilities": "test",
        "price": 1,
    })
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["name"] == "Test Agent"
    assert response.json()["price"] == 1


def test_provider_can_discover_own_listing(client):
    headers = provider_headers(client)
    created = client.post("/agents/create", headers=headers, json={
        "name": "Discoverable Test Agent",
        "description": "A test agent",
        "category": "Testing",
        "capabilities": "test",
        "price": 1,
    })
    assert created.status_code == 200, created.text
    agent_id = created.json()["id"]
    assert any(item["id"] == agent_id for item in client.get("/agents").json())
    assert any(item["id"] == agent_id for item in client.get("/users/me/agents", headers=headers).json())


def test_no_key_invocation_returns_labeled_demo(client, test_db, monkeypatch):
    from src.main import AGENT_NAME_TO_KEY
    import src.main as main_module

    headers = provider_headers(client)
    created = client.post("/agents/create", headers=headers, json={
        "name": "Resume Reviewer",
        "description": "A resume review agent",
        "category": "Career",
        "capabilities": "resume review",
        "price": 0,
    })
    assert created.status_code == 200, created.text
    from src.database.models import Agent
    test_db.query(Agent).filter(Agent.id == created.json()["id"]).one().implementation_key = "resume_reviewer"
    test_db.commit()
    monkeypatch.setattr(main_module, "has_live_ai_key", lambda: False)

    response = client.post(
        f"/agents/invoke/{created.json()['id']}",
        headers=headers,
        json={"agent_type": "Resume Reviewer", "resume_review": {"resume_text": "Test resume"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["demo_mode"] is True
    assert "Demo" in response.json()["output_text"]
    assert response.json()["demo_notice"]
    assert AGENT_NAME_TO_KEY["Resume Reviewer"] == "resume_reviewer"


def test_legacy_upfront_purchase_is_replaced_by_negotiation(client):
    provider = provider_headers(client)
    listing = client.post("/agents/create", headers=provider, json={
        "name": "Paid Test Agent",
        "description": "A test agent",
        "category": "Testing",
        "capabilities": "test",
        "price": 5,
    })
    assert listing.status_code == 200, listing.text

    consumer = provider_headers(client)
    response = client.post("/agents/purchase", headers=consumer, json={"agent_id": listing.json()["id"]})
    assert response.status_code == 409
    assert "POST /negotiations" in response.json()["detail"]


def test_member_can_add_demo_tokens_purchase_service_and_invoke_it(client, test_db, monkeypatch):
    import src.main as main_module

    provider = provider_headers(client)
    listing = client.post("/agents/create", headers=provider, json={
        "name": "Resume Reviewer",
        "description": "A paid resume-review service",
        "category": "Career",
        "capabilities": "resume review",
        "price": 5,
    })
    assert listing.status_code == 200, listing.text
    from src.database.models import Agent
    test_db.query(Agent).filter(Agent.id == listing.json()["id"]).one().implementation_key = "resume_reviewer"
    test_db.commit()

    suffix = uuid4().hex[:10]
    username = f"buyer_{suffix}"
    password = "Safe-Test-Password-2026!"
    register = client.post("/users/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
    })
    assert register.status_code == 200, register.text
    login = client.post("/token", data={"username": username, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    agent_id = listing.json()["id"]

    monkeypatch.setattr(main_module, "has_live_ai_key", lambda: False)
    blocked = client.post(f"/agents/invoke/{agent_id}", headers=headers, json={"input_text": "Review my resume"})
    assert blocked.status_code == 402

    credits = client.post("/tokens/purchase", headers=headers, json={"amount": 10})
    assert credits.status_code == 200, credits.text
    assert credits.json()["new_balance"] == 10

    negotiated = client.post("/negotiations", headers=headers, json={
        "agent_id": agent_id, "buyer_budget": 8, "initial_offer": 5,
    })
    assert negotiated.status_code == 200, negotiated.text
    assert negotiated.json()["status"] == "accepted"
    assert client.get("/users/me", headers=headers).json()["token_balance"] == 10

    invocation = client.post(f"/agents/invoke/{agent_id}", headers=headers, json={
        "input_text": "Review my resume", "negotiation_id": negotiated.json()["id"],
    })
    assert invocation.status_code == 200, invocation.text
    assert invocation.json()["demo_mode"] is True
    assert invocation.json()["charged_tokens"] == 0
    assert invocation.json()["remaining_balance"] == 10
    history = client.get("/users/me/invocations", headers=headers).json()
    assert history[0]["negotiation_id"] == negotiated.json()["id"]
    assert history[0]["settlement_status"] == "not_charged"
    review = client.post(f"/agents/{agent_id}/reviews", headers=headers, json={
        "invocation_id": invocation.json()["invocation_id"], "rating": 5,
    })
    assert review.status_code == 403
