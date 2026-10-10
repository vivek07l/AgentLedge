"""Persistent, deterministic negotiation rules; this module never calls an AI provider."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.database.models import Agent, Negotiation, NegotiationOffer, User

MAX_COUNTER_ROUNDS = 5


def _money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def floor_for(agent: Agent) -> float:
    # Existing listings get a conservative default floor; providers can set one explicitly.
    if agent.minimum_price is not None:
        return _money(agent.minimum_price)
    return _money(agent.price * 0.8)


def _offer(db: Session, negotiation: Negotiation, role: str, action: str,
           amount: float | None, actor_id: int | None = None) -> NegotiationOffer:
    offer = NegotiationOffer(
        negotiation_id=negotiation.id, actor_user_id=actor_id,
        actor_role=role, action=action, amount=amount,
    )
    db.add(offer)
    db.flush()
    return offer


def _provider_response(db: Session, negotiation: Negotiation, buyer_offer: float) -> None:
    agent = negotiation.agent
    floor = floor_for(agent)
    asking = _money(agent.price)
    if buyer_offer >= asking:
        negotiation.status = "accepted"
        negotiation.agreed_price = asking
        _offer(db, negotiation, "provider", "accepted", asking, agent.developer_id)
        return
    # A deterministic concession halfway between the buyer and list price, never below floor.
    counter = max(floor, _money((buyer_offer + asking) / 2))
    counter = min(counter, asking)
    _offer(db, negotiation, "provider", "counter", counter, agent.developer_id)
    negotiation.status = "awaiting_buyer"


def create_negotiation(db: Session, buyer: User, agent: Agent,
                       budget: float, initial_offer: float) -> Negotiation:
    if not agent.is_active:
        raise HTTPException(status_code=404, detail="This listing is not currently available")
    if agent.developer_id == buyer.id:
        raise HTTPException(status_code=400, detail="You cannot negotiate with your own listing")
    budget, initial_offer = _money(budget), _money(initial_offer)
    floor, asking = floor_for(agent), _money(agent.price)
    if budget <= 0 or initial_offer <= 0 or initial_offer > budget:
        raise HTTPException(status_code=422, detail="Offers must be positive and the initial offer cannot exceed your authorized budget")
    if budget < floor:
        raise HTTPException(status_code=422, detail=f"Your authorized budget is below this provider's minimum price ({floor} tokens)")
    negotiation = Negotiation(
        agent_id=agent.id, buyer_id=buyer.id, provider_id=agent.developer_id,
        buyer_budget=budget, status="open", round_count=0,
    )
    db.add(negotiation)
    db.flush()
    _offer(db, negotiation, "buyer", "initial", initial_offer, buyer.id)
    _provider_response(db, negotiation, initial_offer)
    db.commit()
    db.refresh(negotiation)
    return negotiation


def buyer_offer(db: Session, negotiation: Negotiation, buyer: User, amount: float) -> Negotiation:
    if negotiation.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="Only the buyer can submit a buyer offer")
    if negotiation.status != "awaiting_buyer":
        raise HTTPException(status_code=409, detail="This negotiation is not waiting for a buyer offer")
    amount = _money(amount)
    if amount <= 0 or amount > negotiation.buyer_budget:
        raise HTTPException(status_code=422, detail="Offer must be positive and within your authorized budget")
    if negotiation.round_count >= MAX_COUNTER_ROUNDS:
        negotiation.status = "failed"
        db.commit()
        raise HTTPException(status_code=409, detail="The five-round negotiation limit has been reached")
    negotiation.round_count += 1
    _offer(db, negotiation, "buyer", "offer", amount, buyer.id)
    floor = floor_for(negotiation.agent)
    latest_provider = next((o for o in reversed(negotiation.offers) if o.actor_role == "provider" and o.action == "counter"), None)
    if amount >= floor and latest_provider and amount >= latest_provider.amount:
        negotiation.status = "accepted"
        negotiation.agreed_price = _money(latest_provider.amount)
        _offer(db, negotiation, "provider", "accepted", negotiation.agreed_price, negotiation.provider_id)
    elif negotiation.round_count >= MAX_COUNTER_ROUNDS:
        negotiation.status = "failed"
        _offer(db, negotiation, "system", "round_limit", None)
    else:
        _provider_response(db, negotiation, amount)
    negotiation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(negotiation)
    return negotiation


def accept_counter(db: Session, negotiation: Negotiation, buyer: User) -> Negotiation:
    if negotiation.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="Only the buyer can accept this counter-offer")
    if negotiation.status != "awaiting_buyer":
        raise HTTPException(status_code=409, detail="There is no provider counter-offer to accept")
    counter = next((o for o in reversed(negotiation.offers) if o.actor_role == "provider" and o.action == "counter"), None)
    if not counter or counter.amount is None:
        raise HTTPException(status_code=409, detail="No provider counter-offer is available")
    if counter.amount > negotiation.buyer_budget:
        raise HTTPException(status_code=409, detail="Provider counter exceeds the authorized budget")
    if counter.amount < floor_for(negotiation.agent):
        raise HTTPException(status_code=409, detail="Provider counter is below its configured minimum")
    negotiation.status = "accepted"
    negotiation.agreed_price = _money(counter.amount)
    _offer(db, negotiation, "buyer", "accepted", negotiation.agreed_price, buyer.id)
    negotiation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(negotiation)
    return negotiation


def reject_negotiation(db: Session, negotiation: Negotiation, actor: User) -> Negotiation:
    if actor.id not in (negotiation.buyer_id, negotiation.provider_id):
        raise HTTPException(status_code=403, detail="You are not a participant in this negotiation")
    if negotiation.status not in ("open", "awaiting_buyer"):
        raise HTTPException(status_code=409, detail="This negotiation is already closed")
    role = "buyer" if actor.id == negotiation.buyer_id else "provider"
    negotiation.status = "rejected"
    _offer(db, negotiation, role, "rejected", None, actor.id)
    negotiation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(negotiation)
    return negotiation


def negotiation_payload(item: Negotiation) -> dict:
    return {
        "id": item.id, "agent_id": item.agent_id, "agent_name": item.agent.name,
        "buyer_id": item.buyer_id, "provider_id": item.provider_id,
        "buyer_budget": item.buyer_budget, "status": item.status,
        "agreed_price": item.agreed_price, "round_count": item.round_count,
        "max_rounds": MAX_COUNTER_ROUNDS, "created_at": item.created_at.isoformat(),
        "offers": [{"id": o.id, "actor_role": o.actor_role, "action": o.action,
                    "amount": o.amount, "created_at": o.created_at.isoformat()} for o in item.offers],
    }
