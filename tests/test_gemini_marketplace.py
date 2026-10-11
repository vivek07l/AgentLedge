from unittest.mock import AsyncMock
from uuid import uuid4

from src.database.models import Agent, User


def _account(client, test_db, *, admin=False, developer=False):
    username = f"gm_{uuid4().hex[:10]}"
    password = "Safe-Test-Password-2026!"
    created = client.post("/users/register", json={
        "username": username, "email": f"{username}@example.com", "password": password,
        "is_developer": developer,
    })
    assert created.status_code == 200, created.text
    account = test_db.query(User).filter(User.username == username).one()
    account.is_admin = admin
    test_db.commit()
    token = client.post("/token", data={"username": username, "password": password}).json()["access_token"]
    return account, {"Authorization": f"Bearer {token}"}


def _listing(client, headers, name="Study Planner"):
    result = client.post("/agents/create", headers=headers, json={
        "name": name, "description": f"Creates a plan for {name}.", "category": "Learning",
        "capabilities": "Planning; recommendations", "price": 0,
    })
    assert result.status_code == 200, result.text
    return result.json()["id"]


def _enable_payload():
    return {
        "implementation_key": "gemini_marketplace_service",
        "execution_instructions": "Create a realistic, actionable study plan based on the supplied details.",
        "expected_input": "Subject, available hours, deadline, and current skill level.",
        "input_schema_json": '{"type":"object","required":["subject","hours"],"properties":{"subject":{"type":"string"},"hours":{"type":"number"}}}',
        "output_format": "Return a weekly plan with short explanations.",
    }


def test_gemini_enable_disable_is_per_listing_and_admin_only(client, test_db, monkeypatch):
    import src.main as main

    _, owner_headers = _account(client, test_db, developer=True)
    admin, admin_headers = _account(client, test_db, admin=True)
    first_id = _listing(client, owner_headers, "Study Planner")
    second_id = _listing(client, owner_headers, "Resume Review")

    assert client.patch(f"/admin/agents/{first_id}", headers=owner_headers, json=_enable_payload()).status_code == 403
    enabled = client.patch(f"/admin/agents/{first_id}", headers=admin_headers, json=_enable_payload())
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["execution_available"] is False  # No live provider configured in this test.
    assert client.get(f"/agents/{second_id}").json()["execution_available"] is False

    monkeypatch.setattr(main.settings, "AI_MODE", "live")
    monkeypatch.setattr(main, "selected_provider", lambda: "gemini")
    monkeypatch.setattr(main, "selected_model", lambda: "gemini-test-model")
    monkeypatch.setattr(main, "has_provider_credentials", lambda: True)
    assert client.get(f"/agents/{first_id}").json()["execution_available"] is True
    assert client.get(f"/agents/{second_id}").json()["execution_available"] is False

    disabled = client.patch(f"/admin/agents/{first_id}", headers=admin_headers, json={"implementation_key": None})
    assert disabled.status_code == 200
    assert disabled.json()["execution_available"] is False
    assert client.get(f"/agents/{second_id}").json()["execution_available"] is False


def test_generic_gemini_listing_routes_its_own_instructions_and_validates_input(client, test_db, monkeypatch):
    import src.main as main

    _, owner_headers = _account(client, test_db, developer=True)
    _, admin_headers = _account(client, test_db, admin=True)
    listing_id = _listing(client, owner_headers)
    assert client.patch(f"/admin/agents/{listing_id}", headers=admin_headers, json=_enable_payload()).status_code == 200
    monkeypatch.setattr(main.settings, "AI_MODE", "live")
    monkeypatch.setattr(main, "selected_provider", lambda: "gemini")
    monkeypatch.setattr(main, "selected_model", lambda: "gemini-test-model")
    monkeypatch.setattr(main, "has_provider_credentials", lambda: True)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)

    run = AsyncMock(return_value={"output_text": "Plan: study algebra for one hour each day.", "tokens_used": 15})
    instance = main.AVAILABLE_AGENTS["gemini_marketplace_service"]
    original = instance.process_request
    instance.process_request = run
    try:
        invalid = client.post(f"/agents/invoke/{listing_id}", headers=owner_headers, json={"subject": "Algebra"})
        assert invalid.status_code == 422
        assert run.await_count == 0

        response = client.post(f"/agents/invoke/{listing_id}", headers=owner_headers, json={"subject": "Algebra", "hours": 5})
    finally:
        instance.process_request = original
    assert response.status_code == 200, response.text
    assert response.json()["output_text"].startswith("Plan:")
    assert response.json()["execution_mode"] == "live"
    call = run.await_args.kwargs
    assert call["instructions"] == _enable_payload()["execution_instructions"]
    assert call["input_data"] == {"subject": "Algebra", "hours": 5}


def test_gemini_execution_needs_valid_per_listing_configuration(client, test_db):
    _, owner_headers = _account(client, test_db, developer=True)
    _, admin_headers = _account(client, test_db, admin=True)
    listing_id = _listing(client, owner_headers)
    response = client.patch(f"/admin/agents/{listing_id}", headers=admin_headers, json={
        "implementation_key": "gemini_marketplace_service",
        "execution_instructions": "Do the task.",
    })
    assert response.status_code == 422
    listing = test_db.query(Agent).filter(Agent.id == listing_id).one()
    assert listing.implementation_key is None


def test_admin_created_listing_defaults_to_discovery_only(client, test_db):
    _, admin_headers = _account(client, test_db, admin=True)
    response = client.post("/admin/agents", headers=admin_headers, json={
        "name": "Checklist Builder", "description": "Build a checklist from supplied requirements.",
        "category": "Operations", "capabilities": "Checklist generation", "price": 0,
    })
    assert response.status_code == 200, response.text
    assert response.json()["implementation_key"] is None
    assert response.json()["execution_available"] is False
    listing = test_db.query(Agent).filter(Agent.id == response.json()["id"]).one()
    assert listing.execution_instructions is None
