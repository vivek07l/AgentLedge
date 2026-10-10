"""Deterministic, explicitly simulated agent-to-agent marketplace walkthrough."""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class DemoProvider:
    agent_id: str
    name: str
    provider: str
    service: str
    description: str
    price: int
    rating: float
    completed_runs: int
    success_rate: int
    response_time: str


DEMO_PROVIDERS = (
    DemoProvider("demo-resume-01", "ResumePilot", "Northstar Agents", "Resume review", "ATS fit, impact bullets, and a prioritized edit plan.", 8, 4.9, 128, 98, "~18 sec"),
    DemoProvider("demo-resume-02", "CV Compass", "Paperplane AI", "Resume review", "Recruiter-style feedback with role-specific suggestions.", 7, 4.7, 84, 96, "~22 sec"),
    DemoProvider("demo-resume-03", "CareerLens", "BrightPath Labs", "Resume review", "Clear, concise edits for early-career applications.", 5, 4.4, 42, 93, "~15 sec"),
)


def run_marketplace_simulation(task: str, token_budget: int) -> dict:
    """Return a repeatable walkthrough without changing accounts, balances, or trust data."""
    eligible = [provider for provider in DEMO_PROVIDERS if provider.price <= token_budget]
    if not eligible:
        return {
            "mode": "simulation",
            "notice": "Sandbox only. No external agents, payment, or reputation records were changed.",
            "error": f"No demo provider fits the {token_budget}-token maximum. Increase the budget to at least 5 tokens.",
            "minimum_budget": 5,
        }

    # Transparent selection: 45% rating, 35% success evidence, 20% price fit.
    def selection_score(provider: DemoProvider) -> float:
        affordability = (token_budget - provider.price) / token_budget
        return round(provider.rating / 5 * 45 + provider.success_rate / 100 * 35 + affordability * 20, 2)

    ranked = sorted(eligible, key=selection_score, reverse=True)
    chosen = ranked[0]
    buyer_offer = max(1, min(chosen.price - 2, token_budget))
    agreed_price = chosen.price if buyer_offer < chosen.price else buyer_offer
    if agreed_price > token_budget:
        # A real policy would ask its owner before exceeding its configured cap.
        return {
            "mode": "simulation",
            "notice": "Sandbox only. No external agents, payment, or reputation records were changed.",
            "error": "The selected provider's counter-offer is above your budget. Raise the cap and retry.",
            "minimum_budget": chosen.price,
        }

    compare = [
        {**asdict(provider), "score": selection_score(provider), "eligible": True}
        for provider in ranked
    ] + [
        {**asdict(provider), "score": selection_score(provider), "eligible": False}
        for provider in DEMO_PROVIDERS if provider.price > token_budget
    ]
    timeline = [
        {"step": 1, "key": "register", "title": "Buyer agent registers", "status": "complete", "detail": "TaskScout-01 creates a temporary simulation identity and publishes its request policy. No account is created."},
        {"step": 2, "key": "discover", "title": "Services discovered", "status": "complete", "detail": f"The agent searches for “{task}” and finds {len(DEMO_PROVIDERS)} resume-review providers with comparable listings."},
        {"step": 3, "key": "compare", "title": "Providers compared", "status": "complete", "detail": "Candidates are ranked using the visible formula: 45% sample rating, 35% sample success rate, and 20% budget fit. Sample metrics are simulated."},
        {"step": 4, "key": "negotiate", "title": "Agents negotiate", "status": "complete", "detail": f"TaskScout offers {buyer_offer} tokens. {chosen.name} counters at {chosen.price}. The buyer policy accepts because {agreed_price} is within its {token_budget}-token limit."},
        {"step": 5, "key": "exchange", "title": "Simulated token exchange", "status": "complete", "detail": f"{agreed_price} sandbox tokens move from the buyer's demo wallet to {chosen.provider}. No real balance or payment account changes."},
        {"step": 6, "key": "deliver", "title": "Service delivered", "status": "complete", "detail": "A sample resume-review result is generated locally for the presentation; no external model or provider agent ran."},
        {"step": 7, "key": "review", "title": "Demo review recorded", "status": "complete", "detail": "TaskScout leaves a 5-star simulation review. It is kept out of live reviews and reputation scores."},
    ]
    return {
        "mode": "simulation",
        "notice": "Sandbox simulation: no accounts, real token balances, external agents, payments, or live reputation records were changed.",
        "policy": {"maximum_tokens": token_budget, "automatic_acceptance": "accept provider counter-offers at or below the configured cap"},
        "buyer_agent": {"id": "buyer-taskscout-demo-01", "name": "TaskScout-01", "role": "service-seeking agent", "registered_automatically": True, "starting_demo_balance": 24, "remaining_demo_balance": 24 - agreed_price},
        "task": task,
        "providers": compare,
        "selection": {"agent_id": chosen.agent_id, "name": chosen.name, "provider": chosen.provider, "score": selection_score(chosen), "reason": f"Highest weighted score among providers within the {token_budget}-token cap; balances reputation evidence and price fit."},
        "negotiation": {"buyer_offer": buyer_offer, "provider_counter": chosen.price, "agreed_price": agreed_price, "currency": "sandbox tokens", "policy_accepted": True},
        "delivery": {"title": "Resume review sample", "summary": "Demo feedback: strengthen measurable outcomes, tailor the opening summary to the target role, and keep each bullet focused on one result. This is illustrative content, not a real resume analysis."},
        "review": {"rating": 5, "text": "The demo flow was clear and the service matched the request.", "is_simulated": True},
        "timeline": timeline,
    }
