"""Eligibility rules for reviews tied to real marketplace interactions."""
from sqlalchemy.orm import Session

from src.database.models import AgentInvocation, AgentReview, User


def create_verified_review(
    db: Session, user: User, agent_id: int, invocation_id: int, rating: int, review_text: str | None
) -> AgentReview:
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    invocation = db.query(AgentInvocation).filter(
        AgentInvocation.id == invocation_id,
        AgentInvocation.agent_id == agent_id,
        AgentInvocation.user_id == user.id,
        AgentInvocation.status == "succeeded",
    ).first()
    if not invocation:
        raise PermissionError("A completed invocation by you is required to review this agent")
    if invocation.agent.developer_id == user.id:
        raise PermissionError("You cannot review your own agent")
    if invocation.review:
        raise FileExistsError("This invocation has already been reviewed")

    review = AgentReview(
        agent_id=agent_id,
        reviewer_user_id=user.id,
        invocation_id=invocation.id,
        rating=rating,
        review_text=(review_text or "").strip()[:1000] or None,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
