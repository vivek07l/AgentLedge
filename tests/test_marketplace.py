from uuid import uuid4


def register_member(client, *, provider=False):
    username = f"member_{uuid4().hex[:10]}"
    password = "Safe-Test-Password-2026!"
    response = client.post("/users/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "is_developer": provider,
    })
    assert response.status_code == 200, response.text
    login = client.post("/token", data={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_purchase_simulated_credits(client):
    headers = register_member(client)
    response = client.post("/tokens/purchase", headers=headers, json={"amount": 100})
    assert response.status_code == 200, response.text
    assert response.json()["amount_added"] == 100
    assert response.json()["new_balance"] == 100


def test_get_current_user_and_token_balance(client):
    headers = register_member(client)
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["token_balance"], (int, float))


def test_get_invocation_history(client):
    headers = register_member(client)
    response = client.get("/users/me/invocations", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []


def test_provider_earnings_are_not_claimed_as_implemented(client):
    headers = register_member(client, provider=True)
    response = client.get("/marketplace/developer-earnings", headers=headers)
    assert response.status_code == 404


def test_discovery_filters_ranks_paginates_and_returns_live_categories(client, test_db):
    headers = register_member(client, provider=True)
    listings = [
        {"name": "Resume Review Pro", "description": "CV specialist", "category": "Career", "capabilities": "resume, ATS", "price": 9},
        {"name": "Writing Helper", "description": "Resume text and cover letters", "category": "Writing", "capabilities": "editing", "price": 3},
        {"name": "Inactive Finder", "description": "resume review", "category": "Career", "capabilities": "review", "price": 1},
    ]
    created = []
    for index, item in enumerate(listings):
        response = client.post("/agents/create", headers=headers, json=item)
        assert response.status_code == 200, response.text
        created.append(response.json())
        if index == 2:
            # A provider account cannot impersonate an administrator.
            assert client.patch(f"/admin/agents/{created[-1]['id']}", headers=headers, json={"is_active": False}).status_code == 403

    # Search relevance favors the listing name over a description-only match.
    results = client.get("/agents", params={"query": "resume", "sort": "relevance", "limit": 1, "offset": 0})
    assert results.status_code == 200
    assert results.headers.get("X-Total-Count") is not None
    assert results.json()[0]["id"] == created[0]["id"]
    cheap = client.get("/agents", params={"max_price": 4, "category": "Writing", "limit": 10})
    assert [item["id"] for item in cheap.json()] == [created[1]["id"]]
    page = client.get("/agents", params={"sort": "price", "limit": 1, "offset": 1})
    assert page.json()[0]["id"] == created[1]["id"]
    desc_page = client.get("/agents", params={"sort": "price_desc", "limit": 1})
    assert desc_page.status_code == 200
    assert desc_page.json()[0]["id"] == created[0]["id"]
    assert client.get("/marketplace/categories").json() == ["Career", "Writing"]

    from src.database.models import AgentInvocation, AgentReview, User
    provider_user = test_db.query(User).filter(User.is_developer.is_(True)).one()
    invocation = AgentInvocation(user_id=provider_user.id, agent_id=created[0]["id"],
        input_data="sample", output_data="sample", status="succeeded")
    test_db.add(invocation)
    test_db.commit()
    test_db.add(AgentReview(agent_id=created[0]["id"], reviewer_user_id=provider_user.id,
        invocation_id=invocation.id, rating=5, moderation_status="approved"))
    test_db.commit()
    trusted = client.get("/agents", params={"minimum_rating": 4.9, "minimum_success_rate": 99})
    assert [item["id"] for item in trusted.json()] == [created[0]["id"]]
    assert trusted.json()[0]["average_rating"] == 5
    assert trusted.json()[0]["success_rate"] == 100
