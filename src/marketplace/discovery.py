"""Marketplace discovery queries and trust summaries."""
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from src.database.models import Agent, AgentInvocation, AgentReview


def discover_agents(db: Session, query: str = "", category: str = "", sort: str = "relevance"):
    agents_query = db.query(Agent).filter(Agent.is_active.is_(True))
    if query:
        term = f"%{query.strip()}%"
        agents_query = agents_query.filter(
            Agent.name.ilike(term) | Agent.description.ilike(term) | Agent.capabilities.ilike(term)
        )
    if category:
        agents_query = agents_query.filter(Agent.category.ilike(category.strip()))

    agents = agents_query.all()
    stats = {}
    for agent_id, avg_rating, review_count in db.query(
        AgentReview.agent_id, func.avg(AgentReview.rating), func.count(AgentReview.id)
    ).filter(AgentReview.moderation_status == "approved").group_by(AgentReview.agent_id):
        stats[agent_id] = {"average_rating": float(avg_rating), "review_count": review_count}

    usage = {}
    for agent_id, completed, succeeded in db.query(
        AgentInvocation.agent_id,
        func.count(AgentInvocation.id),
        func.sum(case((AgentInvocation.status == "succeeded", 1), else_=0)),
    ).filter(AgentInvocation.status.in_(["succeeded", "failed"])).group_by(AgentInvocation.agent_id):
        usage[agent_id] = (completed or 0, succeeded or 0)

    for agent in agents:
        rating = stats.get(agent.id, {})
        completed, succeeded = usage.get(agent.id, (0, 0))
        agent.average_rating = rating.get("average_rating")
        agent.review_count = rating.get("review_count", 0)
        agent.completed_invocations = completed
        agent.success_rate = round((succeeded / completed) * 100, 1) if completed else None

    if sort == "rating":
        agents.sort(key=lambda a: (a.average_rating or 0, a.review_count), reverse=True)
    elif sort == "success_rate":
        agents.sort(key=lambda a: (a.success_rate or 0, a.completed_invocations), reverse=True)
    elif sort == "price":
        agents.sort(key=lambda a: a.price or 0)
    return agents


def reputation_for_agent(db: Session, agent_id: int):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return None
    reviews = db.query(AgentReview).filter(
        AgentReview.agent_id == agent_id, AgentReview.moderation_status == "approved"
    ).all()
    completed = db.query(AgentInvocation).filter(
        AgentInvocation.agent_id == agent_id,
        AgentInvocation.status.in_(["succeeded", "failed"]),
    ).count()
    succeeded = db.query(AgentInvocation).filter(
        AgentInvocation.agent_id == agent_id, AgentInvocation.status == "succeeded"
    ).count()
    return {
        "agent_id": agent_id,
        "average_rating": round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else None,
        "review_count": len(reviews),
        "completed_invocations": completed,
        "success_rate": round(succeeded * 100 / completed, 1) if completed else None,
    }
