from fastapi import FastAPI, Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, update, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from jose import jwt, JWTError
import json
from uuid import uuid4

from src.database.models import Base, User, Agent, AgentPurchase, AgentInvocation, AgentReview, Negotiation, NegotiationOffer, TokenTransaction
from src.database.bootstrap import upgrade_legacy_schema
from src.marketplace.discovery import discover_agents, reputation_for_agent
from src.marketplace.reviews import create_verified_review
from src.marketplace.simulation import run_marketplace_simulation
from src.marketplace.settlement import reserve_buyer_tokens
from src.marketplace.negotiation import (
    MAX_COUNTER_ROUNDS, accept_counter, buyer_offer, create_negotiation,
    floor_for, negotiation_payload, reject_negotiation,
)
from src.database.schemas import (
    UserCreate, UserResponse, 
    AgentCreate, AgentResponse,
    TokenResponse, TokenData,
    PurchaseCreate, AgentPurchaseResponse,
    InvocationCreate, InvocationResponse
)
from src.config import get_settings
from src.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    oauth2_scheme
)

from src.agents.resume_reviewer import ResumeReviewerAgent
from src.agents.code_reviewer import CodeReviewAgent
from src.agents.interview_prep import InterviewPrepAgent
from src.agents.writing_assistant import WritingAssistantAgent
from src.agents.technical_troubleshooter import TechnicalTroubleshooterAgent

from pydantic import BaseModel, Field
from openai import APIError
from src.agents.demo_responses import make_demo_response
from src.agents.providers import has_provider_credentials, selected_model, selected_provider

settings = get_settings()
app = FastAPI(title="AgentLedge")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # Set CORS_ORIGINS to the exact frontend origin(s) when hosted.
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
upgrade_legacy_schema(engine)
Base.metadata.create_all(bind=engine)

class SimulationRequest(BaseModel):
    task: str = Field(min_length=8, max_length=280)
    token_budget: int = Field(default=12, ge=1, le=1000)

class NegotiationCreateRequest(BaseModel):
    agent_id: int
    buyer_budget: float = Field(gt=0, le=100000)
    initial_offer: float = Field(gt=0, le=100000)

class NegotiationOfferRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)

class ProviderCounterRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)

def has_live_ai_key() -> bool:
    return settings.AI_MODE.strip().lower() == "live" and has_provider_credentials()

@app.get("/system/status")
async def system_status():
    return {
        "ai_mode": "live" if has_live_ai_key() else "demo",
        "provider": selected_provider(),
        "model": selected_model(),
    }

@app.post("/simulation/run")
async def simulate_marketplace_flow(request: SimulationRequest):
    """Run an isolated presentation scenario; never writes to account or trust tables."""
    return run_marketplace_simulation(request.task.strip(), request.token_budget)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user
async def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

async def get_optional_current_user(
    db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(db=db, token=token)
    except HTTPException:
        return None

# Compatibility name referenced by the project's existing test fixture.
get_current_active_user = get_current_user

class TokenPurchaseRequest(BaseModel):
    amount: float

class ReviewCreate(BaseModel):
    invocation_id: int
    rating: int
    review_text: Optional[str] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class UserAdminUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_developer: Optional[bool] = None

class AgentAdminUpdate(BaseModel):
    is_active: bool

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@app.post("/users/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing:
        if existing.username == user.username:
            raise HTTPException(status_code=409, detail="That username is already registered. Choose another username or sign in.")
        raise HTTPException(status_code=409, detail="That email is already registered. Sign in or use another email.")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_developer=user.is_developer,
        is_admin=False,
        token_balance=0.0,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.model_validate(db_user)

@app.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/admin/login", response_model=TokenResponse)
async def admin_login(credentials: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.username == credentials.username).first()
    if not admin or not admin.is_admin or not admin.is_active or not verify_password(credentials.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid admin username or password")
    token = create_access_token(
        data={"sub": admin.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}

@app.get("/admin/users")
async def admin_list_users(
    admin: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    return [{
        "id": user.id, "username": user.username, "email": user.email,
        "is_active": user.is_active, "is_developer": user.is_developer,
        "is_admin": user.is_admin,
    } for user in db.query(User).order_by(User.created_at.desc()).all()]

@app.patch("/admin/users/{user_id}")
async def admin_update_user(
    user_id: int, update: UserAdminUpdate, admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and update.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own admin account")
    if update.is_active is not None:
        target.is_active = update.is_active
    if update.is_developer is not None and not target.is_admin:
        target.is_developer = update.is_developer
    db.commit()
    return {"id": target.id, "is_active": target.is_active, "is_developer": target.is_developer}

@app.get("/admin/agents")
async def admin_list_agents(
    admin: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    return [{
        "id": agent.id, "name": agent.name, "category": agent.category,
        "developer_id": agent.developer_id, "is_active": agent.is_active,
    } for agent in db.query(Agent).order_by(Agent.created_at.desc()).all()]

@app.patch("/admin/agents/{agent_id}")
async def admin_update_agent(
    agent_id: int, update: AgentAdminUpdate, admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_active = update.is_active
    db.commit()
    return {"id": agent.id, "is_active": agent.is_active}

@app.post("/agents/create", response_model=AgentResponse)
async def create_agent(
    agent: AgentCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only developers can create agents"
        )
    if agent.minimum_price is not None and (agent.minimum_price < 0 or agent.minimum_price > agent.price):
        raise HTTPException(status_code=422, detail="Minimum acceptable price must be between zero and the listed price")
    
    db_agent = Agent(
        name=agent.name,
        description=agent.description,
        developer_id=current_user.id,
        price=agent.price,
        minimum_price=agent.minimum_price,
        category=agent.category,
        capabilities=agent.capabilities,
        is_active=True
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return AgentResponse.model_validate(db_agent)

@app.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int, update: AgentCreate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.developer_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Your listing was not found")
    for field in ("name", "description", "price", "minimum_price", "category", "capabilities"):
        setattr(agent, field, getattr(update, field))
    if agent.minimum_price is not None and (agent.minimum_price < 0 or agent.minimum_price > agent.price):
        raise HTTPException(status_code=422, detail="Minimum acceptable price must be between zero and the listed price")
    db.commit()
    db.refresh(agent)
    return AgentResponse.model_validate(agent)

@app.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.developer_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Your listing was not found")
    db.delete(agent)
    db.commit()

@app.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    query: str = Query(default="", max_length=120),
    category: str = Query(default="", max_length=80),
    sort: str = Query(default="relevance", pattern="^(relevance|rating|success_rate|price)$"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """List all available agents"""
    agents = discover_agents(db, query=query, category=category, sort=sort)
    
    # Get all purchased agents for the current user
    purchased_agent_ids = {
        purchase.agent_id for purchase in 
        db.query(AgentPurchase).filter(AgentPurchase.user_id == current_user.id).all()
    } if current_user else set()
    
    return [
        AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            price=agent.price,
            minimum_price=floor_for(agent),
            developer_id=agent.developer_id,
            is_active=agent.is_active,
            is_purchased=agent.id in purchased_agent_ids,
            created_at=agent.created_at,
            category=agent.category,
            capabilities=agent.capabilities,
            average_rating=agent.average_rating,
            review_count=agent.review_count,
            success_rate=agent.success_rate,
            completed_invocations=agent.completed_invocations,
        )
        for agent in agents
    ]

@app.get("/users/me/agents", response_model=List[AgentResponse])
async def list_my_agents(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Return all listings owned by the signed-in service provider, including drafts."""
    agents = db.query(Agent).filter(Agent.developer_id == current_user.id).order_by(Agent.created_at.desc()).all()
    return [AgentResponse.model_validate(agent).model_copy(update={
        "minimum_price": floor_for(agent), **(reputation_for_agent(db, agent.id) or {}),
    }) for agent in agents]

@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.is_active and not (current_user and (current_user.id == agent.developer_id or current_user.is_admin)):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if user has purchased this agent
    purchase = db.query(AgentPurchase).filter(
        AgentPurchase.user_id == current_user.id,
        AgentPurchase.agent_id == agent_id
    ).first() if current_user else None
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        price=agent.price,
        minimum_price=floor_for(agent),
        developer_id=agent.developer_id,
        is_active=agent.is_active,
        is_purchased=purchase is not None,
        created_at=agent.created_at,
        category=agent.category,
        capabilities=agent.capabilities,
        **(reputation_for_agent(db, agent_id) or {})
    )

@app.post("/agents/purchase", response_model=AgentPurchaseResponse)
async def purchase_agent(
    purchase: PurchaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Keep the legacy route explicit: access is no longer charged up front.
    # Buyers negotiate and settle only after a successful live execution.
    raise HTTPException(
        status_code=409,
        detail="Up-front purchases are retired. Start a negotiation at POST /negotiations, then execute the accepted service.",
    )

@app.post("/negotiations")
async def start_negotiation(
    request: NegotiationCreateRequest,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Service not found")
    if agent.minimum_price is not None and (agent.minimum_price < 0 or agent.minimum_price > agent.price):
        raise HTTPException(status_code=409, detail="This listing has an invalid provider minimum price")
    negotiation = create_negotiation(db, current_user, agent, request.buyer_budget, request.initial_offer)
    return negotiation_payload(negotiation)

@app.get("/negotiations/{negotiation_id}")
async def get_negotiation(
    negotiation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    if current_user.id not in (item.buyer_id, item.provider_id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You are not a participant in this negotiation")
    return negotiation_payload(item)

@app.post("/negotiations/{negotiation_id}/offers")
async def submit_buyer_offer(
    negotiation_id: int, request: NegotiationOfferRequest,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation_payload(buyer_offer(db, item, current_user, request.amount))

@app.post("/negotiations/{negotiation_id}/accept")
async def accept_negotiation_counter(
    negotiation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation_payload(accept_counter(db, item, current_user))

@app.post("/negotiations/{negotiation_id}/reject")
async def reject_negotiation_endpoint(
    negotiation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation_payload(reject_negotiation(db, item, current_user))

@app.get("/users/me/negotiations")
async def list_my_negotiations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(Negotiation).filter(
        (Negotiation.buyer_id == current_user.id) | (Negotiation.provider_id == current_user.id)
    ).order_by(Negotiation.created_at.desc()).all()
    return [negotiation_payload(item) for item in items]

async def call_builtin_agent(agent_key: str, agent_instance: Any, input_data: dict) -> dict:
    payload_key = {
        "resume_reviewer": "resume_review",
        "code_reviewer": "code_review",
        "interview_prep": "interview_prep",
        "writing_assistant": "writing_assistant",
        "technical_troubleshooter": "technical_troubleshooting",
    }[agent_key]
    payload = input_data.get(payload_key) or input_data
    generic_text = input_data.get("input_text", "")
    if agent_key == "code_reviewer":
        return await agent_instance.process_request(
            code=payload.get("code", generic_text),
            language=payload.get("language", "python"), context=payload.get("context"),
        )
    if agent_key == "resume_reviewer":
        return await agent_instance.process_request(
            resume_text=payload.get("resume_text", generic_text), context=payload.get("context"),
        )
    if agent_key == "interview_prep":
        return await agent_instance.process_request(
            topic=payload.get("topic", generic_text),
            experience_level=payload.get("experience_level", "entry"), context=payload.get("context"),
        )
    if agent_key == "writing_assistant":
        return await agent_instance.process_request(
            text=payload.get("text", generic_text),
            style=payload.get("style"), context=payload.get("context"),
        )
    return await agent_instance.process_request({
        **payload,
        "issue": payload.get("issue", payload.get("problem", generic_text)),
        "problem": payload.get("problem", payload.get("issue", generic_text)),
    })


@app.post("/agents/invoke/{agent_id}")
async def invoke_agent(
    agent_id: int,
    input_data: dict,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Paid marketplace use is authorized by a persisted agreement. The agreed
    # backend price, never a client-supplied amount, governs settlement.
    negotiation_id = input_data.pop("negotiation_id", None)
    body_idempotency_key = input_data.pop("idempotency_key", None)
    client_supplied_key = bool(idempotency_key or body_idempotency_key)
    request_key = (idempotency_key or body_idempotency_key or str(uuid4())).strip()
    persisted_input = json.dumps(input_data, sort_keys=True, separators=(",", ":"))
    if len(request_key) > 255:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be at most 255 characters")
    existing = db.query(AgentInvocation).filter(
        AgentInvocation.user_id == current_user.id,
        AgentInvocation.idempotency_key == request_key,
    ).first()
    if existing:
        if (existing.input_data != persisted_input or existing.agent_id != agent_id
                or existing.negotiation_id != negotiation_id):
            raise HTTPException(status_code=409, detail="This Idempotency-Key was already used with different input")
        if existing.status in ("succeeded", "demo"):
            stored = json.loads(existing.output_data or "{}")
            return {
                **stored, "output_text": stored.get("output_text", ""),
                "invocation_id": existing.id, "demo_mode": existing.status == "demo",
                "idempotency_key": request_key, "settlement_status": existing.token_transaction.status if existing.token_transaction else "not_charged",
                "charged_tokens": existing.token_transaction.amount if existing.token_transaction and existing.token_transaction.status == "settled" else 0,
                "agreed_price": existing.negotiation.agreed_price if existing.negotiation else 0,
                "remaining_balance": current_user.token_balance,
            }
        raise HTTPException(status_code=409, detail=f"This idempotency key already has execution status '{existing.status}'")
    if negotiation_id is not None:
        negotiation = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not negotiation or negotiation.agent_id != agent.id or negotiation.buyer_id != current_user.id:
            raise HTTPException(status_code=403, detail="An authorized negotiation for this service is required")
        if negotiation.status != "accepted" or negotiation.agreed_price is None:
            raise HTTPException(status_code=409, detail="The negotiation must be accepted before execution")
        if has_live_ai_key() and negotiation.agreed_price > 0 and not client_supplied_key:
            raise HTTPException(status_code=422, detail="Send a stable Idempotency-Key header for paid live executions")
    else:
        negotiation = None
        if agent.price and agent.price > 0 and agent.developer_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=402, detail="Negotiate and accept a price before invoking this paid service")
    
    # Get the agent instance from available agents
    agent_key = AGENT_NAME_TO_KEY.get(agent.name)
    
    if not agent_key:
        raise HTTPException(status_code=404, detail=f"No implementation mapping for agent: {agent.name}")
    
    agent_instance = AVAILABLE_AGENTS.get(agent_key)
    if not agent_instance:
        raise HTTPException(status_code=404, detail="Agent implementation not found")
    
    reserved_invocation = None
    reserved_transaction = None
    charge = float(negotiation.agreed_price) if negotiation else 0.0
    will_execute_live = has_live_ai_key()
    if will_execute_live and charge > 0:
        if not reserve_buyer_tokens(db, current_user.id, charge):
            db.rollback()
            raise HTTPException(status_code=402, detail="Insufficient token balance for the agreed price")
        reserved_invocation = AgentInvocation(
            user_id=current_user.id, agent_id=agent_id, negotiation_id=negotiation.id,
            idempotency_key=request_key, input_data=persisted_input,
            output_data=None, tokens_used=0, status="pending",
        )
        db.add(reserved_invocation)
        db.flush()
        reserved_transaction = TokenTransaction(
            user_id=current_user.id, invocation_id=reserved_invocation.id,
            provider_id=agent.developer_id,
            negotiation_id=negotiation.id, amount=charge, status="reserved",
            idempotency_key=request_key,
        )
        db.add(reserved_transaction)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.query(AgentInvocation).filter(
                AgentInvocation.user_id == current_user.id,
                AgentInvocation.idempotency_key == request_key,
            ).first()
            if existing and existing.status in ("succeeded", "demo"):
                if (existing.input_data != persisted_input or existing.agent_id != agent_id
                        or existing.negotiation_id != negotiation_id):
                    raise HTTPException(status_code=409, detail="This Idempotency-Key was already used with different input")
                stored = json.loads(existing.output_data or "{}")
                return {
                    **stored, "output_text": stored.get("output_text", ""),
                    "invocation_id": existing.id, "demo_mode": existing.status == "demo",
                    "idempotency_key": request_key,
                    "settlement_status": existing.token_transaction.status if existing.token_transaction else "not_charged",
                    "charged_tokens": existing.token_transaction.amount if existing.token_transaction and existing.token_transaction.status == "settled" else 0,
                    "agreed_price": existing.negotiation.agreed_price if existing.negotiation else 0,
                    "remaining_balance": current_user.token_balance,
                }
            raise HTTPException(status_code=409, detail="An execution with this idempotency key is already in progress")
        db.refresh(reserved_invocation)

    try:
        demo_mode = not has_live_ai_key()
        if demo_mode:
            result = make_demo_response(agent_key, input_data)
        else:
            try:
                result = await call_builtin_agent(agent_key, agent_instance, input_data)
            except APIError:
                # Failed live calls become an explicitly labeled free sample.
                demo_mode = True
                result = make_demo_response(agent_key, input_data)
        if result.get("status") == "error" or result.get("error"):
            raise RuntimeError("Agent returned an unsuccessful result")

        output_text = (
            result.get("output_text")
            or result.get("output")
            or result.get("troubleshooting_steps")
            or ""
        )
        token_usage = result.get("token_usage", {})
        tokens_used = result.get("tokens_used") or (
            token_usage.get("input_tokens", 0) + token_usage.get("output_tokens", 0)
        )
        
        # Record the invocation
        if reserved_invocation:
            db_invocation = reserved_invocation
            db_invocation.output_data = json.dumps({"output_text": output_text})
            db_invocation.tokens_used = tokens_used
            db_invocation.status = "demo" if demo_mode else "succeeded"
            if reserved_transaction:
                if demo_mode:
                    db.execute(update(User).where(User.id == current_user.id).values(token_balance=User.token_balance + charge))
                    reserved_transaction.status = "released"
                    reserved_transaction.settled_at = datetime.utcnow()
                else:
                    db.execute(update(User).where(User.id == agent.developer_id).values(token_balance=User.token_balance + charge))
                    reserved_transaction.status = "settled"
                    reserved_transaction.settled_at = datetime.utcnow()
        else:
            db_invocation = AgentInvocation(
                user_id=current_user.id, agent_id=agent_id,
                negotiation_id=negotiation.id if negotiation else None,
                idempotency_key=request_key,
                input_data=persisted_input, output_data=json.dumps({"output_text": output_text}),
                tokens_used=tokens_used, status="demo" if demo_mode else "succeeded",
            )
            db.add(db_invocation)
        db.commit()
        db.refresh(db_invocation)
        db.refresh(current_user)
        return {
            **result,
            "output_text": output_text,
            "output_data": output_text,
            "tokens_used": tokens_used,
            "invocation_id": db_invocation.id,
            "demo_mode": demo_mode,
            "demo_notice": "Sample response only; no AI model processed this request." if demo_mode else None,
            "agreed_price": charge if negotiation else 0,
            "charged_tokens": charge if (reserved_transaction and not demo_mode) else 0,
            "settlement_status": reserved_transaction.status if reserved_transaction else "not_charged",
            "remaining_balance": current_user.token_balance,
            "idempotency_key": request_key,
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        failed = reserved_invocation or AgentInvocation(
            user_id=current_user.id, agent_id=agent_id,
            negotiation_id=negotiation.id if negotiation else None,
            idempotency_key=request_key, input_data=persisted_input,
            output_data=None, tokens_used=0,
        )
        if failed not in db:
            db.add(failed)
        failed.status = "failed"
        failed.summary = "Live service execution failed"
        if reserved_transaction:
            db.execute(update(User).where(User.id == current_user.id).values(token_balance=User.token_balance + charge))
            reserved_transaction.status = "released"
            reserved_transaction.settled_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="The AI service could not complete this request. Check the API connection, API key, and OPENAI_MODEL setting.",
        )

@app.post("/agents/summarize")
async def summarize_conversation(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        input_text = request.get("input_text", "")
        output_text = request.get("output_text", "")
        
        # Extract meaningful content from input
        try:
            input_data = json.loads(input_text)
            if isinstance(input_data, dict):
                # For interview prep format
                if 'interview_prep' in input_data:
                    input_text = input_data['interview_prep'].get('topic', '')
                # For code review format
                elif 'code_review' in input_data:
                    input_text = f"Code review request: {input_data['code_review'].get('code', '')[:100]}"
                # For direct input
                elif 'input_text' in input_data:
                    input_text = input_data['input_text']
                elif 'topic' in input_data:
                    input_text = input_data['topic']
        except:
            pass
            
        # Extract meaningful content from output
        try:
            output_data = json.loads(output_text)
            if isinstance(output_data, dict):
                output_text = output_data.get('output_text', output_text)
        except:
            pass
            
        # Clean up the texts
        input_text = input_text.strip()
        output_text = output_text.strip()
        
        # Generate a clean summary
        if not input_text and not output_text:
            summary = "No content available"
        else:
            summary = ""
            if input_text:
                summary += input_text[:150]
                if len(input_text) > 150:
                    summary += "..."
            if output_text:
                if summary:
                    summary += "\nResponse: "
                summary += output_text[:200]
                if len(output_text) > 200:
                    summary += "..."
        
        return {
            "status": "success",
            "data": {
                "summary": summary
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/tokens/purchase")
async def purchase_tokens(
    request: TokenPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # In a real app, this would integrate with Stripe or another payment processor
        # For now, we'll just add the tokens directly
        if request.amount <= 0 or request.amount > 10000:
            raise HTTPException(status_code=400, detail="Demo credit amount must be between 1 and 10000")
        current_user.token_balance += request.amount
        db.commit()
        
        return {
            "status": "success",
            "new_balance": current_user.token_balance,
            "amount_added": request.amount
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@app.get("/users/me/provider-stats")
async def get_provider_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_developer:
        raise HTTPException(status_code=403, detail="Provider access required")
    settled = db.query(TokenTransaction).filter(
        TokenTransaction.provider_id == current_user.id,
        TokenTransaction.status == "settled",
    )
    return {
        "settled_tokens_earned": float(settled.with_entities(func.coalesce(func.sum(TokenTransaction.amount), 0)).scalar() or 0),
        "settled_transactions": settled.count(),
        "token_balance": current_user.token_balance,
        "active_listings": db.query(Agent).filter(Agent.developer_id == current_user.id, Agent.is_active.is_(True)).count(),
    }

@app.get("/users/me/invocations", response_model=List[Dict[str, Any]])
async def get_user_invocations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all invocations for the current user"""
    invocations = db.query(AgentInvocation).filter(
        AgentInvocation.user_id == current_user.id
    ).order_by(AgentInvocation.created_at.desc()).all()
    
    return [{
        "id": inv.id,
        "agent_id": inv.agent_id,
        "agent_name": inv.agent.name,
        "input_data": inv.input_data,
        "output_data": inv.output_data,
        "tokens_used": inv.tokens_used,
        "status": inv.status,
        "execution_status": inv.status,
        "negotiation_id": inv.negotiation_id,
        "negotiation": negotiation_payload(inv.negotiation) if inv.negotiation else None,
        "transaction_id": inv.token_transaction.id if inv.token_transaction else None,
        "amount_charged": inv.token_transaction.amount if inv.token_transaction and inv.token_transaction.status == "settled" else 0,
        "settlement_status": inv.token_transaction.status if inv.token_transaction else "not_charged",
        "created_at": inv.created_at.isoformat()
    } for inv in invocations]

@app.get("/agents/{agent_id}/reputation")
async def get_agent_reputation(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = reputation_for_agent(db, agent_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return summary

@app.get("/agents/{agent_id}/reviews")
async def list_agent_reviews(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [{
        "id": review.id,
        "invocation_id": review.invocation_id,
        "rating": review.rating,
        "review_text": review.review_text,
        "created_at": review.created_at.isoformat(),
    } for review in db.query(AgentReview).filter(
        AgentReview.agent_id == agent_id,
        AgentReview.moderation_status == "approved",
    ).order_by(AgentReview.created_at.desc()).all()]

@app.get("/agents/{agent_id}/analytics")
async def get_agent_analytics(
    agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or (agent.developer_id != current_user.id and not current_user.is_admin):
        raise HTTPException(status_code=404, detail="Your listing was not found")
    rows = db.query(AgentInvocation).filter(
        AgentInvocation.agent_id == agent_id,
        AgentInvocation.status.in_(["succeeded", "failed", "demo"]),
    ).order_by(AgentInvocation.created_at.asc()).all()
    daily: dict[str, dict[str, int]] = {}
    for invocation in rows:
        day = invocation.created_at.date().isoformat()
        counts = daily.setdefault(day, {"invocations": 0, "succeeded": 0, "failed": 0, "demo": 0})
        if invocation.status == "demo":
            counts["demo"] += 1
        else:
            counts["invocations"] += 1
            counts[invocation.status] += 1
    series = []
    for day, counts in sorted(daily.items()):
        total = counts["succeeded"] + counts["failed"]
        series.append({
            "timestamp": f"{day}T00:00:00",
            "invocations": counts["invocations"],
            "succeeded": counts["succeeded"],
            "failed": counts["failed"],
            "demo_invocations": counts["demo"],
            "success_rate": round(counts["succeeded"] * 100 / total, 1) if total else 0,
        })
    return {"id": agent.id, "name": agent.name, "time_series": series}

@app.post("/agents/{agent_id}/reviews", status_code=201)
async def create_agent_review(
    agent_id: int,
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        db_review = create_verified_review(
            db, current_user, agent_id, review.invocation_id, review.rating, review.review_text
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error))
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return {"id": db_review.id, "invocation_id": db_review.invocation_id, "rating": db_review.rating}

@app.get("/agents/invocations")
async def list_invocations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    invocations = (
        db.query(AgentInvocation)
        .join(AgentPurchase, AgentInvocation.purchase_id == AgentPurchase.id)
        .join(Agent, AgentPurchase.agent_id == Agent.id)
        .filter(AgentPurchase.user_id == current_user.id)
        .order_by(AgentInvocation.created_at.desc())
        .all()
    )
    
    return {
        "status": "success",
        "data": [{
            "id": invocation.id,
            "purchase_id": invocation.purchase_id,
            "agent_id": invocation.agent_id,
            "input_data": invocation.input_data,
            "output_data": invocation.output_data,
            "tokens_used": invocation.tokens_used,
            "created_at": invocation.created_at,
            "agent_name": invocation.agent.name
        } for invocation in invocations]
    }

# Pre-configured agents
AVAILABLE_AGENTS = {
    "resume_reviewer": ResumeReviewerAgent(),
    "code_reviewer": CodeReviewAgent(),
    "interview_prep": InterviewPrepAgent(),
    "writing_assistant": WritingAssistantAgent(),
    "technical_troubleshooter": TechnicalTroubleshooterAgent()
}

# Map agent display names to implementation keys
AGENT_NAME_TO_KEY = {
    "Interview Prep Assistant": "interview_prep",
    "Code Reviewer": "code_reviewer",
    "Resume Reviewer": "resume_reviewer",
    "Technical Troubleshooter": "technical_troubleshooter",
    "Writing Assistant": "writing_assistant"
}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
