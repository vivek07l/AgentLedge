"""Atomic internal-credit reservation helpers."""
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.database.models import User


def reserve_buyer_tokens(db: Session, user_id: int, amount: float) -> bool:
    """Subtract only if the balance still covers the entire reservation.

    The conditional UPDATE is the serialization point for concurrent purchases.
    Caller commits the reservation with its invocation/ledger rows.
    """
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.token_balance >= amount)
        .values(token_balance=User.token_balance - amount)
    )
    return result.rowcount == 1
