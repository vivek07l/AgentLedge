from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from src.auth.security import get_password_hash
from src.database.models import Agent, AgentInvocation, TokenTransaction, User


def _make_account(client, test_db, *, provider=False, admin=False):
    username = f"gemini_{uuid4().hex[:10]}"
    response = client.post("/users/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "Safe-Test-Password-2026!",
        "is_developer": provider,
    })
    assert response.status_code == 200, response.text
    user = test_db.query(User).filter(User.username == username).one()
    user.is_admin = admin
    test_db.commit()
    return user, {"Authorization": f"Bearer {client.post('/token', data={'username': username, 'password': 'Safe-Test-Password-2026!'}).json()['access_token']}"}


def _service(client, test_db, owner_headers, *, price=0):
    response = client.post("/agents/create", headers=owner_headers, json={
        "name": "Demo Meeting Summarizer",
        "description": "A sample listing for summarization",
        "category": "Productivity",
        "capabilities": "Meeting summaries",
        "price": price,
        "minimum_price": price,
    })
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _bind_summarizer(client, agent_id, admin_headers):
    return client.patch(f"/admin/agents/{agent_id}", headers=admin_headers, json={
        "is_active": True,
        "implementation_key": "gemini_text_summarizer",
        "name": "Meeting Summarizer",
        "description": "Summarizes user-provided meeting notes into key points and action items using live Gemini execution.",
        "category": "Productivity",
        "capabilities": "Faithful meeting summaries; decisions; action items",
    })


def _configure_gemini(monkeypatch):
    import src.main as main

    monkeypatch.setattr(main.settings, "AI_MODE", "live")
    monkeypatch.setattr(main, "selected_provider", lambda: "gemini")
    monkeypatch.setattr(main, "selected_model", lambda: "gemini-test-model")
    monkeypatch.setattr(main, "has_provider_credentials", lambda: True)
    return main


def test_admin_can_bind_only_supported_summarizer_and_availability_tracks_config(client, test_db, monkeypatch):
    import src.main as main

    owner, owner_headers = _make_account(client, test_db, provider=True)
    admin, admin_headers = _make_account(client, test_db, admin=True)
    agent_id = _service(client, test_db, owner_headers)

    denied = _bind_summarizer(client, agent_id, owner_headers)
    assert denied.status_code == 403
    configured = _bind_summarizer(client, agent_id, admin_headers)
    assert configured.status_code == 200, configured.text
    assert configured.json()["implementation_key"] == "gemini_text_summarizer"
    assert configured.json()["execution_available"] is False
    assert client.get(f"/agents/{agent_id}").json()["execution_available"] is False

    _configure_gemini(monkeypatch)
    assert client.get(f"/agents/{agent_id}").json()["execution_available"] is True
    unsupported = client.patch(f"/admin/agents/{agent_id}", headers=admin_headers, json={
        "implementation_key": "arbitrary_handler",
    })
    assert unsupported.status_code == 422
    assert test_db.query(Agent).filter(Agent.id == agent_id).one().implementation_key == "gemini_text_summarizer"


def test_missing_gemini_configuration_does_not_execute_or_create_invocation(client, test_db, monkeypatch):
    import src.main as main

    owner, owner_headers = _make_account(client, test_db, provider=True)
    _, admin_headers = _make_account(client, test_db, admin=True)
    agent_id = _service(client, test_db, owner_headers)
    assert _bind_summarizer(client, agent_id, admin_headers).status_code == 200
    monkeypatch.setattr(main, "_gemini_summarizer_is_configured", lambda: False)

    result = client.post(f"/agents/invoke/{agent_id}", headers=owner_headers, json={"input_text": "Summarize this"})
    assert result.status_code == 503
    assert "No tokens were charged" in result.json()["detail"]
    assert test_db.query(AgentInvocation).filter(AgentInvocation.agent_id == agent_id).count() == 0


def test_invalid_summarization_input_is_rejected_before_provider_call(client, test_db, monkeypatch):
    import src.main as main

    owner, owner_headers = _make_account(client, test_db, provider=True)
    _, admin_headers = _make_account(client, test_db, admin=True)
    agent_id = _service(client, test_db, owner_headers)
    assert _bind_summarizer(client, agent_id, admin_headers).status_code == 200
    _configure_gemini(monkeypatch)
    provider_call = AsyncMock()
    main.AVAILABLE_AGENTS["gemini_text_summarizer"].client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_call)),
    )

    for text in ("", "   ", "x" * 20001):
        result = client.post(f"/agents/invoke/{agent_id}", headers=owner_headers, json={"input_text": text})
        assert result.status_code == 422
    assert provider_call.await_count == 0


def test_live_gemini_result_is_persisted_as_success(client, test_db, monkeypatch):
    import src.main as main

    owner, owner_headers = _make_account(client, test_db, provider=True)
    _, admin_headers = _make_account(client, test_db, admin=True)
    agent_id = _service(client, test_db, owner_headers)
    assert _bind_summarizer(client, agent_id, admin_headers).status_code == 200
    _configure_gemini(monkeypatch)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    provider_call = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Summary: launch Tuesday. Action: send invite."))],
        usage=SimpleNamespace(total_tokens=24),
    ))
    summarizer = main.AVAILABLE_AGENTS["gemini_text_summarizer"]
    original_client, original_model = summarizer.client, summarizer.model
    summarizer.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=provider_call)))
    summarizer.model = "gemini-test-model"
    try:
        response = client.post(f"/agents/invoke/{agent_id}", headers=owner_headers, json={
            "input_text": "We decided on Tuesday. Alex will send the invite.",
        })
    finally:
        summarizer.client, summarizer.model = original_client, original_model
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["output_text"] == "Summary: launch Tuesday. Action: send invite."
    assert body["provider"] == "gemini"
    assert body["execution_mode"] == "live"
    assert body["demo_mode"] is False
    assert body["tokens_used"] == 24
    invocation = test_db.query(AgentInvocation).filter(AgentInvocation.id == body["invocation_id"]).one()
    assert invocation.status == "succeeded"
    provider_call.assert_awaited_once()


def test_provider_failure_releases_reserved_marketplace_tokens(client, test_db, monkeypatch):
    import src.main as main

    owner, owner_headers = _make_account(client, test_db, provider=True)
    buyer, buyer_headers = _make_account(client, test_db)
    _, admin_headers = _make_account(client, test_db, admin=True)
    agent_id = _service(client, test_db, owner_headers, price=6)
    assert _bind_summarizer(client, agent_id, admin_headers).status_code == 200
    _configure_gemini(monkeypatch)
    monkeypatch.setattr(main, "has_live_ai_key", lambda: True)
    assert client.post("/tokens/purchase", headers=buyer_headers, json={"amount": 10}).status_code == 200
    deal = client.post("/negotiations", headers=buyer_headers, json={
        "agent_id": agent_id, "buyer_budget": 6, "initial_offer": 6,
    })
    assert deal.status_code == 200, deal.text
    if deal.json()["status"] != "accepted":
        deal = client.post(f"/negotiations/{deal.json()['id']}/accept", headers=buyer_headers)
        assert deal.status_code == 200, deal.text

    async def fail_provider(*args, **kwargs):
        raise RuntimeError("provider outage; secret must not escape")

    monkeypatch.setattr(main, "call_builtin_agent", fail_provider)
    response = client.post(f"/agents/invoke/{agent_id}", headers={
        **buyer_headers, "Idempotency-Key": "gemini-provider-failure",
    }, json={"input_text": "Summarize meeting", "negotiation_id": deal.json()["id"]})
    assert response.status_code == 502
    assert "secret must not escape" not in response.text
    assert client.get("/users/me", headers=buyer_headers).json()["token_balance"] == 10
    invocation = test_db.query(AgentInvocation).filter(AgentInvocation.idempotency_key == "gemini-provider-failure").one()
    transaction = test_db.query(TokenTransaction).filter(TokenTransaction.invocation_id == invocation.id).one()
    assert invocation.status == "failed"
    assert transaction.status == "released"
