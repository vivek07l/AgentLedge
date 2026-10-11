from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from src.database.bootstrap import upgrade_legacy_schema


def test_populated_legacy_user_table_requires_reviewed_migration_without_changes():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL)"
        ))
        connection.execute(text("INSERT INTO users (username) VALUES ('existing-member')"))

    with pytest.raises(RuntimeError, match="Automatic schema bootstrap is disabled"):
        upgrade_legacy_schema(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert columns == {"id", "username"}
    with engine.connect() as connection:
        row = connection.execute(text("SELECT username FROM users WHERE id = 1")).one()
    assert row.username == "existing-member"
    engine.dispose()


def test_provider_can_register_and_manage_own_listing(client):
    suffix = uuid4().hex[:10]
    username = f"provider_{suffix}"
    email = f"provider_{suffix}@example.com"
    password = "Safe-Test-Password-2026!"

    response = client.post("/users/register", json={
        "username": username,
        "email": email,
        "password": password,
        "is_developer": True,
        "is_admin": True,
    })
    assert response.status_code == 200, response.text
    assert response.json()["is_developer"] is True
    assert response.json()["is_admin"] is False

    login = client.post("/token", data={"username": username, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    listing = {
        "name": f"Provider smoke {suffix}",
        "description": "Temporary provider onboarding test",
        "category": "Testing",
        "capabilities": "test listing",
        "price": 1,
    }
    created = client.post("/agents/create", json=listing, headers=headers)
    assert created.status_code == 200, created.text
    agent_id = created.json()["id"]
    try:
        listing["name"] += " edited"
        updated = client.put(f"/agents/{agent_id}", json=listing, headers=headers)
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == listing["name"]
        assert any(item["id"] == agent_id for item in client.get("/agents").json())
        assert any(item["id"] == agent_id for item in client.get("/users/me/agents", headers=headers).json())
    finally:
        deleted = client.delete(f"/agents/{agent_id}", headers=headers)
        assert deleted.status_code == 204, deleted.text


def test_duplicate_username_and_email_return_actionable_errors(client):
    suffix = uuid4().hex[:10]
    body = {
        "username": f"member_{suffix}",
        "email": f"member_{suffix}@example.com",
        "password": "Safe-Test-Password-2026!",
    }
    assert client.post("/users/register", json=body).status_code == 200

    duplicate_username = client.post("/users/register", json={
        **body, "email": f"other_{suffix}@example.com",
    })
    assert duplicate_username.status_code == 409
    assert "username" in duplicate_username.json()["detail"].lower()

    duplicate_email = client.post("/users/register", json={
        **body, "username": f"other_{suffix}",
    })
    assert duplicate_email.status_code == 409
    assert "email" in duplicate_email.json()["detail"].lower()


@pytest.mark.parametrize(
    "display_name,key,payload,expected_kwargs,result",
    [
        ("Code Reviewer", "code_reviewer", {"code_review": {"code": "print(1)", "language": "python"}}, {"code": "print(1)", "language": "python", "context": None}, {"output_text": "mock output", "tokens_used": 3}),
        ("Resume Reviewer", "resume_reviewer", {"resume_review": {"resume_text": "resume"}}, {"resume_text": "resume", "context": None}, {"output_text": "mock output", "tokens_used": 3}),
        ("Interview Prep Assistant", "interview_prep", {"interview_prep": {"topic": "engineer"}}, {"topic": "engineer", "experience_level": "entry", "context": None}, {"output_text": "mock output", "tokens_used": 3}),
        ("Writing Assistant", "writing_assistant", {"writing_assistant": {"text": "hello"}}, {"text": "hello", "style": None, "context": None}, {"output_text": "mock output", "tokens_used": 3}),
        ("Technical Troubleshooter", "technical_troubleshooter", {"technical_troubleshooting": {"problem": "won't start"}}, {"problem": "won't start", "issue": "won't start"}, {"troubleshooting_steps": "mock output", "token_usage": {"input_tokens": 1, "output_tokens": 2}, "cost": 0}),
    ],
)
def test_builtin_invocation_adapts_form_payloads(
    client, test_db, monkeypatch, display_name, key, payload, expected_kwargs, result
):
    from src.database.models import User, Agent
    from src.main import AVAILABLE_AGENTS
    from src.auth.security import get_password_hash, create_access_token

    suffix = uuid4().hex[:10]
    user = User(
        username=f"agent_{suffix}", email=f"agent_{suffix}@example.com",
        hashed_password=get_password_hash("Safe-Test-Password-2026!"),
        is_developer=True, is_admin=False, token_balance=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    agent = Agent(
        name=display_name, description="Invocation adapter test", category="Testing",
        capabilities="test", developer_id=user.id, price=0, is_active=True,
        implementation_key=key,
    )
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)

    token = create_access_token({"sub": user.username})
    import src.main as main_module
    monkeypatch.setattr(main_module, "has_live_ai_key", lambda: True)
    mock_handler = AsyncMock(return_value=result)
    original = AVAILABLE_AGENTS[key].process_request
    AVAILABLE_AGENTS[key].process_request = mock_handler
    try:
        response = client.post(
            f"/agents/invoke/{agent.id}",
            json={"agent_type": display_name, **payload},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["output_text"] == "mock output"
        assert response.json()["invocation_id"]
        mock_handler.assert_awaited_once_with(**expected_kwargs) if key != "technical_troubleshooter" else mock_handler.assert_awaited_once_with(expected_kwargs)
    finally:
        AVAILABLE_AGENTS[key].process_request = original
        from src.database.models import AgentInvocation
        test_db.query(AgentInvocation).filter(AgentInvocation.agent_id == agent.id).delete()
        test_db.delete(agent)
        test_db.delete(user)
        test_db.commit()


def test_no_api_key_returns_labeled_demo_and_does_not_score_reputation(client, test_db, monkeypatch):
    from src.database.models import User, Agent, AgentInvocation
    from src.main import has_live_ai_key
    from src.auth.security import get_password_hash, create_access_token
    import src.main as main_module

    monkeypatch.setattr(main_module, "has_live_ai_key", lambda: False)
    suffix = uuid4().hex[:10]
    user = User(
        username=f"demo_{suffix}", email=f"demo_{suffix}@example.com",
        hashed_password=get_password_hash("Safe-Test-Password-2026!"),
        is_developer=True, is_admin=False, token_balance=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    agent = Agent(name="Code Reviewer", description="demo", category="Testing", capabilities="code", developer_id=user.id, price=0, implementation_key="code_reviewer")
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)
    token = create_access_token({"sub": user.username})

    response = client.post(
        f"/agents/invoke/{agent.id}",
        json={"agent_type": "Code Reviewer", "code_review": {"code": "print(1)"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["demo_mode"] is True
    assert "Demo" in response.json()["output_text"]
    invocation = test_db.query(AgentInvocation).filter(AgentInvocation.id == response.json()["invocation_id"]).one()
    assert invocation.status == "demo"
    listing = next(item for item in client.get("/agents").json() if item["id"] == agent.id)
    assert listing["completed_invocations"] == 0 and listing["success_rate"] is None
    assert has_live_ai_key() is False


def test_discovery_search_category_and_rating_sort(client, test_db):
    """Search and ranking should expose matching providers and computed review evidence."""
    from src.database.models import User, Agent, AgentReview
    from src.auth.security import get_password_hash

    suffix = uuid4().hex[:10]
    provider = User(
        username=f"discover_{suffix}", email=f"discover_{suffix}@example.com",
        hashed_password=get_password_hash("Safe-Test-Password-2026!"),
        is_developer=True, is_admin=False, token_balance=0,
    )
    reviewer = User(
        username=f"reviewer_{suffix}", email=f"reviewer_{suffix}@example.com",
        hashed_password=get_password_hash("Safe-Test-Password-2026!"),
        is_developer=False, is_admin=False, token_balance=0,
    )
    test_db.add_all([provider, reviewer])
    test_db.commit()
    low = Agent(name=f"Search Low {suffix}", description="low rated writing", category="Writing", capabilities="copy", developer_id=provider.id, price=1)
    high = Agent(name=f"Search High {suffix}", description="high rated writing", category="Writing", capabilities="copy", developer_id=provider.id, price=2)
    unrelated = Agent(name=f"Unrelated {suffix}", description="other", category="Code", capabilities="review", developer_id=provider.id, price=0)
    test_db.add_all([low, high, unrelated])
    test_db.commit()
    test_db.add_all([
        AgentReview(agent_id=low.id, reviewer_user_id=reviewer.id, invocation_id=900001, rating=2, moderation_status="approved"),
        AgentReview(agent_id=high.id, reviewer_user_id=reviewer.id, invocation_id=900002, rating=5, moderation_status="approved"),
    ])
    test_db.commit()
    try:
        searched = client.get(f"/agents?query=high&category=Writing")
        assert searched.status_code == 200, searched.text
        assert [item["id"] for item in searched.json()] == [high.id]

        ranked = client.get("/agents?category=Writing&sort=rating")
        assert ranked.status_code == 200, ranked.text
        assert [item["id"] for item in ranked.json()] == [high.id, low.id]
        assert ranked.json()[0]["average_rating"] == 5
        assert ranked.json()[0]["review_count"] == 1
    finally:
        test_db.query(AgentReview).filter(AgentReview.agent_id.in_([low.id, high.id])).delete(synchronize_session=False)
        test_db.query(Agent).filter(Agent.id.in_([low.id, high.id, unrelated.id])).delete(synchronize_session=False)
        test_db.delete(reviewer)
        test_db.delete(provider)
        test_db.commit()


def test_verified_review_requires_successful_own_invocation_and_blocks_duplicates(client, test_db, monkeypatch):
    from src.database.models import User, Agent, AgentInvocation, AgentReview
    from src.auth.security import get_password_hash, create_access_token
    import src.main as main_module

    suffix = uuid4().hex[:10]
    provider = User(username=f"owner_{suffix}", email=f"owner_{suffix}@example.com", hashed_password=get_password_hash("Safe-Test-Password-2026!"), is_developer=True, is_admin=False, token_balance=0)
    consumer = User(username=f"consumer_{suffix}", email=f"consumer_{suffix}@example.com", hashed_password=get_password_hash("Safe-Test-Password-2026!"), is_developer=False, is_admin=False, token_balance=0)
    test_db.add_all([provider, consumer])
    test_db.commit()
    agent = Agent(name="Resume Reviewer", description="review", category="Career", capabilities="resume", developer_id=provider.id, price=0, implementation_key="resume_reviewer")
    test_db.add(agent)
    test_db.commit()
    test_db.refresh(agent)
    invocation = AgentInvocation(user_id=consumer.id, agent_id=agent.id, input_data="{}", output_data='{"output_text":"sample"}', status="succeeded")
    test_db.add(invocation)
    test_db.commit()
    test_db.refresh(invocation)
    token = create_access_token({"sub": consumer.username})
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(main_module, "has_live_ai_key", lambda: False)

    demo = client.post(f"/agents/invoke/{agent.id}", json={"agent_type": "Resume Reviewer", "resume_review": {"resume_text": "resume"}}, headers=headers)
    assert demo.status_code == 200, demo.text
    assert demo.json()["demo_mode"] is True
    review = client.post(f"/agents/{agent.id}/reviews", json={"invocation_id": invocation.id, "rating": 5, "review_text": "good"}, headers=headers)
    assert review.status_code == 201, review.text
    duplicate = client.post(f"/agents/{agent.id}/reviews", json={"invocation_id": invocation.id, "rating": 4}, headers=headers)
    assert duplicate.status_code == 409, duplicate.text

    reputation = client.get(f"/agents/{agent.id}/reputation", headers=headers)
    assert reputation.status_code == 200, reputation.text
    assert reputation.json()["average_rating"] == 5
    assert reputation.json()["completed_invocations"] == 1
    assert reputation.json()["success_rate"] == 100
    listed = next(item for item in client.get("/agents?sort=rating").json() if item["id"] == agent.id)
    assert listed["review_count"] == 1

    try:
        # A demo invocation must not be reviewable as real evidence.
        demo_invocation_id = demo.json()["invocation_id"]
        invalid = client.post(f"/agents/{agent.id}/reviews", json={"invocation_id": demo_invocation_id, "rating": 5}, headers=headers)
        assert invalid.status_code == 403
    finally:
        test_db.query(AgentReview).filter(AgentReview.agent_id == agent.id).delete()
        test_db.query(AgentInvocation).filter(AgentInvocation.agent_id == agent.id).delete()
        test_db.delete(agent)
        test_db.delete(consumer)
        test_db.delete(provider)
        test_db.commit()


def test_legacy_offer_collection_is_not_a_marketplace_endpoint(client):
    response = client.get("/offers")
    assert response.status_code == 404
