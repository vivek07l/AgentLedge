from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_developer = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    token_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    agents = relationship("Agent", back_populates="developer")
    purchases = relationship("AgentPurchase", back_populates="user")
    invocations = relationship("AgentInvocation", back_populates="user")
    negotiations_as_buyer = relationship("Negotiation", back_populates="buyer", foreign_keys="Negotiation.buyer_id")
    negotiations_as_provider = relationship("Negotiation", back_populates="provider", foreign_keys="Negotiation.provider_id")
    token_transactions = relationship("TokenTransaction", back_populates="user", foreign_keys="TokenTransaction.user_id")
    oauth_authorizations = relationship("OAuthAuthorizationCode", back_populates="user", cascade="all, delete-orphan")
    oauth_tokens = relationship("OAuthAccessToken", back_populates="user", cascade="all, delete-orphan")


class OAuthClient(Base):
    """OAuth clients created through dynamic client registration."""
    __tablename__ = "oauth_clients"

    client_id = Column(String, primary_key=True)
    redirect_uris_json = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OAuthAuthorizationCode(Base):
    """Single-use, hashed authorization codes bound to PKCE and one user."""
    __tablename__ = "oauth_authorization_codes"

    code_hash = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("oauth_clients.client_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    redirect_uri = Column(String, nullable=False)
    code_challenge = Column(String, nullable=False)
    code_challenge_method = Column(String, nullable=False, default="S256")
    scopes = Column(String, nullable=False, default="marketplace:read")
    audience = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="oauth_authorizations")


class OAuthAccessToken(Base):
    """Hashed opaque OAuth bearer tokens with server-side expiry/revocation."""
    __tablename__ = "oauth_access_tokens"

    token_hash = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("oauth_clients.client_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scopes = Column(String, nullable=False)
    audience = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="oauth_tokens")


class OAuthActionApproval(Base):
    """One-time user approval for a specific AgentMesh write action."""
    __tablename__ = "oauth_action_approvals"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending", server_default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    consumed_at = Column(DateTime, nullable=True)

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    category = Column(String, default="General", nullable=False)
    capabilities = Column(String, default="", nullable=False)
    implementation_key = Column(String, nullable=True)
    execution_instructions = Column(Text, nullable=True)
    expected_input = Column(Text, nullable=True)
    input_schema_json = Column(Text, nullable=True)
    output_format = Column(String, nullable=True)
    developer_id = Column(Integer, ForeignKey("users.id"))
    price = Column(Float)
    minimum_price = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    developer = relationship("User", back_populates="agents")
    purchases = relationship("AgentPurchase", back_populates="agent")
    invocations = relationship("AgentInvocation", back_populates="agent")
    reviews = relationship("AgentReview", back_populates="agent")

class AgentPurchase(Base):
    __tablename__ = "agent_purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    purchase_price = Column(Float)
    # Retained for compatibility with the legacy purchase migration/schema.
    tokens_remaining = Column(Float, nullable=False, default=0.0, server_default="0.0")
    purchase_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="purchases")
    agent = relationship("Agent", back_populates="purchases")
    invocations = relationship("AgentInvocation", back_populates="purchase")

class AgentInvocation(Base):
    __tablename__ = "agent_invocations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    purchase_id = Column(Integer, ForeignKey("agent_purchases.id"))
    input_data = Column(String)
    output_data = Column(String)
    tokens_used = Column(Integer, default=0)
    summary = Column(String, nullable=True)
    status = Column(String, default="succeeded", nullable=False)
    negotiation_id = Column(Integer, ForeignKey("negotiations.id"), nullable=True, index=True)
    idempotency_key = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="invocations")
    agent = relationship("Agent", back_populates="invocations")
    purchase = relationship("AgentPurchase", back_populates="invocations")
    review = relationship("AgentReview", back_populates="invocation", uselist=False)
    negotiation = relationship("Negotiation", back_populates="invocations")
    token_transaction = relationship("TokenTransaction", back_populates="invocation", uselist=False)


class Negotiation(Base):
    __tablename__ = "negotiations"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    buyer_budget = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="open")
    agreed_price = Column(Float, nullable=True)
    round_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    agent = relationship("Agent")
    buyer = relationship("User", back_populates="negotiations_as_buyer", foreign_keys=[buyer_id])
    provider = relationship("User", back_populates="negotiations_as_provider", foreign_keys=[provider_id])
    offers = relationship("NegotiationOffer", back_populates="negotiation", cascade="all, delete-orphan", order_by="NegotiationOffer.created_at")
    invocations = relationship("AgentInvocation", back_populates="negotiation")


class NegotiationOffer(Base):
    __tablename__ = "negotiation_offers"

    id = Column(Integer, primary_key=True, index=True)
    negotiation_id = Column(Integer, ForeignKey("negotiations.id"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    negotiation = relationship("Negotiation", back_populates="offers")
    actor = relationship("User")


class TokenTransaction(Base):
    __tablename__ = "token_transactions"
    __table_args__ = (UniqueConstraint("invocation_id", name="uq_token_transaction_invocation"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    invocation_id = Column(Integer, ForeignKey("agent_invocations.id"), nullable=True)
    negotiation_id = Column(Integer, ForeignKey("negotiations.id"), nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    settled_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="token_transactions", foreign_keys=[user_id])
    provider = relationship("User", foreign_keys=[provider_id])
    invocation = relationship("AgentInvocation", back_populates="token_transaction", uselist=False)
    negotiation = relationship("Negotiation")

class AgentReview(Base):
    __tablename__ = "agent_reviews"
    __table_args__ = (UniqueConstraint("invocation_id", name="uq_agent_review_invocation"),)

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invocation_id = Column(Integer, ForeignKey("agent_invocations.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(String, nullable=True)
    moderation_status = Column(String, default="approved", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    agent = relationship("Agent", back_populates="reviews")
    reviewer = relationship("User")
    invocation = relationship("AgentInvocation", back_populates="review")
