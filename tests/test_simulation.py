from src.database.models import Agent, User


def test_autonomous_presentation_flow_compares_negotiates_and_keeps_demo_isolated(client, test_db):
    response = client.post("/simulation/run", json={
        "task": "Review a product manager resume for a climate role",
        "token_budget": 12,
    })
    assert response.status_code == 200, response.text
    run = response.json()

    assert run["mode"] == "simulation"
    assert run["buyer_agent"]["registered_automatically"] is True
    providers = run["providers"]
    assert len(providers) == 3
    assert {provider["service"] for provider in providers} == {"Resume review"}
    assert providers == sorted(providers, key=lambda provider: provider["score"], reverse=True)

    selected = next(provider for provider in providers if provider["agent_id"] == run["selection"]["agent_id"])
    assert selected["eligible"] is True
    assert run["negotiation"]["policy_accepted"] is True
    assert run["negotiation"]["agreed_price"] <= 12
    assert run["buyer_agent"]["starting_demo_balance"] - run["negotiation"]["agreed_price"] == run["buyer_agent"]["remaining_demo_balance"]
    assert len(run["timeline"]) == 7
    assert {event["key"] for event in run["timeline"]} == {
        "register", "discover", "compare", "negotiate", "exchange", "deliver", "review"
    }
    assert run["review"]["is_simulated"] is True
    assert "fictional" in run["notice"].lower() or "sandbox" in run["notice"].lower()
    # The presentation endpoint must not create accounts, listings, purchases, or reputation records.
    assert test_db.query(User).count() == 0
    assert test_db.query(Agent).count() == 0


def test_simulation_obeys_token_cap_and_handles_no_eligible_provider(client):
    response = client.post("/simulation/run", json={
        "task": "Review a resume",
        "token_budget": 4,
    })
    assert response.status_code == 200
    assert "error" in response.json()
    assert response.json()["minimum_budget"] == 5


def test_simulation_validates_request(client):
    short_task = client.post("/simulation/run", json={"task": "short", "token_budget": 12})
    assert short_task.status_code == 422
    excessive_cap = client.post("/simulation/run", json={"task": "Review a resume for this role", "token_budget": 1001})
    assert excessive_cap.status_code == 422
