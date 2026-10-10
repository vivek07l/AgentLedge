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
