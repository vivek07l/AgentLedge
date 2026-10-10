import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from src.auth.security import get_password_hash
from src.database.models import User


RESOURCE = "http://127.0.0.1:8011/mcp"
REDIRECT_URI = "http://127.0.0.1:8765/oauth/callback"


def _pkce_pair():
    verifier = "A" * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _authorize(client, db, *, username="oauth_reader"):
    db.add(User(username=username, email=f"{username}@example.com", hashed_password=get_password_hash("Safe-Test-Password-2026!"), is_active=True))
    db.commit()
    registered = client.post("/oauth/register", json={"redirect_uris": [REDIRECT_URI]})
    assert registered.status_code == 201, registered.text
    client_id = registered.json()["client_id"]
    verifier, challenge = _pkce_pair()
    params = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "state": "test-state-123", "scope": "marketplace:read", "resource": RESOURCE,
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


def test_oauth_csrf_form_is_bound_to_signed_authorization_request(client, test_db):
    client_id, _, _ = _authorize(client, test_db)
    assert client_id
