from fastapi import FastAPI, Depends, HTTPException, status, Query, Header, Request, Form, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, update, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Literal
from jose import jwt, JWTError
import json
from uuid import uuid4
import base64
import hashlib
import hmac
import secrets
import re
import html
import time
from collections import defaultdict, deque
from threading import Lock
import asyncio
from urllib.parse import urlencode
import math

from src.database.models import User, Agent, AgentPurchase, AgentInvocation, AgentReview, Negotiation, NegotiationOffer, TokenTransaction, OAuthClient, OAuthAuthorizationCode, OAuthAccessToken, OAuthActionApproval, AutonomousExecutionPolicy
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
from src.agents.gemini_text_summarizer import GeminiTextSummarizerAgent
from src.agents.gemini_marketplace import GeminiMarketplaceAgent

from pydantic import BaseModel, Field
from src.agents.demo_responses import make_demo_response
from src.agents.providers import has_provider_credentials, selected_model, selected_provider

settings = get_settings()
app = FastAPI(title="AgentsLedge")


def _utcnow() -> datetime:
    """Return a naive UTC datetime suitable for SQLite/PostgreSQL columns without timezone.

    SQLite stores DATETIME columns as naive strings; comparing with a timezone-aware
    datetime raises TypeError. This helper returns UTC time as a naive datetime consistent
    with the stored column values.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)



# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # Set CORS_ORIGINS to the exact frontend origin(s) when hosted.
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_oauth_rate_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_oauth_rate_lock = Lock()


@app.middleware("http")
async def limit_oauth_endpoint_attempts(request: Request, call_next):
    if request.url.path in {"/oauth/register", "/oauth/authorize", "/oauth/token", "/oauth/revoke"}:
        source_ip = request.client.host if request.client else "unknown"
        key = (source_ip, request.url.path)
        now = time.monotonic()
        with _oauth_rate_lock:
            events = _oauth_rate_events[key]
            while events and events[0] <= now - 60:
                events.popleft()
            if len(events) >= max(1, settings.OAUTH_RATE_LIMIT_PER_MINUTE):
                return JSONResponse(status_code=429, content={"detail": "Too many authorization requests. Please wait and retry."}, headers={"Retry-After": "60"})
            events.append(now)
    return await call_next(request)


# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

OAUTH_SCOPES = {"marketplace:read", "marketplace:write"}
OAUTH_READ_SCOPE = "marketplace:read"
OAUTH_WRITE_SCOPE = "marketplace:write"
OAUTH_CODE_TTL_SECONDS = 300
OAUTH_TOKEN_TTL_SECONDS = 900


def _oauth_issuer(request: Request) -> str:
    configured = getattr(settings, "OAUTH_ISSUER", "").strip().rstrip("/")
    return configured or str(request.base_url).rstrip("/")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalise_oauth_scopes(value: str) -> str | None:
    requested = value.split()
    if not requested or len(set(requested)) != len(requested) or not set(requested).issubset(OAUTH_SCOPES):
        return None
    if OAUTH_READ_SCOPE not in requested:
        return None
    return " ".join(scope for scope in (OAUTH_READ_SCOPE, OAUTH_WRITE_SCOPE) if scope in requested)


def _pkce_matches(verifier: str, challenge: str) -> bool:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    actual = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(actual, challenge)


def _oauth_form_html(params: dict[str, str], csrf: str, error: str = "") -> str:
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(name, quote=True)}" value="{html.escape(value, quote=True)}">'
        for name, value in params.items()
    )
    message = f'<p role="alert">{html.escape(error)}</p>' if error else ""
    has_write_access = OAUTH_WRITE_SCOPE in params.get("scope", "").split()
    write_permissions = """<h2>Marketplace write</h2><ul>
<li>Create negotiations and submit offers.</li>
<li>Accept or reject negotiations.</li>
<li>Invoke services, potentially spending marketplace tokens.</li>
<li>Submit reviews for eligible completed executions.</li>
</ul>""" if has_write_access else ""
    permission_intro = """<p>This MCP client is requesting the following permissions:</p>
<h2>Marketplace read</h2><ul>
<li>Search and compare public marketplace listings.</li>
<li>View service details, reputation and reviews.</li>
<li>View your own negotiation status and invocation results.</li>
</ul>"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Connect to AgentsLedge</title><style>body{{font:16px system-ui;background:#f4f0e8;color:#211d17;margin:0;padding:8vh 16px}}main{{max-width:520px;margin:auto;background:#fff;padding:32px;border:2px solid #211d17;box-shadow:8px 8px #e5b547}}h1{{font-size:28px}}p{{line-height:1.55}}h2{{font-size:18px;margin:20px 0 8px}}ul{{padding-left:22px;line-height:1.55}}label{{display:block;margin:16px 0 6px}}input{{box-sizing:border-box;width:100%;padding:12px;border:1px solid #777;font:inherit}}button{{margin-top:22px;padding:12px 18px;border:2px solid #211d17;background:#e5b547;font:700 16px system-ui;cursor:pointer}}small{{display:block;margin-top:16px;color:#555}}</style></head><body><main><p>AGENTSLEDGE · SECURE CONNECTION</p><h1>Connect your marketplace account</h1>{permission_intro}{write_permissions}{message}<form method="post" action="/oauth/authorize">{hidden}<input type="hidden" name="csrf" value="{csrf}"><label for="username">Username</label><input id="username" name="username" autocomplete="username" required><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required><button type="submit">Sign in and approve this access</button></form><small>Access expires after 15 minutes. Tokens are linked to your account and expire automatically; clients may revoke them sooner.</small></main></body></html>"""


def _oauth_request_cookie(request_data: dict[str, str]) -> str:
    payload = json.dumps(request_data, separators=(",", ":"), sort_keys=True).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(settings.SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).digest()
    return encoded + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


def _decode_oauth_request_cookie(value: str) -> dict[str, str] | None:
    try:
        encoded, signature = value.split(".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            return None
        payload = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        result = json.loads(payload)
        return result if isinstance(result, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _valid_oauth_redirect_uri(uri: str) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(uri)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata(request: Request):
    issuer = _oauth_issuer(request)
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "introspection_endpoint": f"{issuer}/oauth/introspect",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": ["none"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": sorted(OAUTH_SCOPES),
        "authorization_response_iss_parameter_supported": True,
        "resource_parameter_supported": True,
        "client_id_metadata_document_supported": False,
    }


@app.post("/oauth/register", status_code=201)
async def oauth_register_client(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    redirect_uris = body.get("redirect_uris") if isinstance(body, dict) else None
    if not isinstance(redirect_uris, list) or not redirect_uris or len(redirect_uris) > 20:
        raise HTTPException(status_code=400, detail="redirect_uris must be a non-empty list")
    if any(not isinstance(uri, str) or len(uri) > 2048 or not _valid_oauth_redirect_uri(uri) for uri in redirect_uris):
        raise HTTPException(status_code=400, detail="Redirect URIs must use HTTPS, except loopback HTTP for local clients")
    if len(set(redirect_uris)) != len(redirect_uris):
        raise HTTPException(status_code=400, detail="redirect_uris must not contain duplicates")
    client_id = secrets.token_urlsafe(24)
    db.add(OAuthClient(client_id=client_id, redirect_uris_json=json.dumps(redirect_uris)))
    db.commit()
    return {"client_id": client_id, "client_id_issued_at": int(_utcnow().timestamp()), "redirect_uris": redirect_uris, "token_endpoint_auth_method": "none", "grant_types": ["authorization_code"], "response_types": ["code"]}


@app.get("/oauth/authorize", response_class=HTMLResponse)
async def oauth_authorize_page(
    request: Request,
    response_type: str = Query(...), client_id: str = Query(...), redirect_uri: str = Query(...),
    state: str = Query(..., min_length=1, max_length=512), scope: str = Query("marketplace:read"),
    resource: str = Query(...),
    code_challenge: str = Query(..., min_length=43, max_length=128),
    code_challenge_method: str = Query(...), db: Session = Depends(get_db),
):
    client = db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
    if response_type != "code" or not client or redirect_uri not in json.loads(client.redirect_uris_json):
        raise HTTPException(status_code=400, detail="Invalid OAuth client or redirect URI")
    granted_scopes = _normalise_oauth_scopes(scope)
    if not granted_scopes or resource != settings.AGENTMESH_MCP_RESOURCE_URL or code_challenge_method != "S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", code_challenge):
        raise HTTPException(status_code=400, detail="Only PKCE S256 and supported marketplace scopes are accepted")
    if not state or len(state) > 512:
        raise HTTPException(status_code=400, detail="A valid state value is required")
    params = {"response_type": response_type, "client_id": client_id, "redirect_uri": redirect_uri, "state": state, "scope": granted_scopes, "resource": resource, "code_challenge": code_challenge, "code_challenge_method": code_challenge_method, "created_at": str(int(_utcnow().timestamp()))}
    csrf = secrets.token_urlsafe(24)
    html = _oauth_form_html(params, csrf)
    response = HTMLResponse(html)
    response.set_cookie("agentledge_oauth_csrf", csrf, max_age=600, httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/oauth/authorize")
    response.set_cookie("agentledge_oauth_request", _oauth_request_cookie(params), max_age=600, httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/oauth/authorize")
    return response


@app.post("/oauth/authorize")
async def oauth_authorize_submit(
    request: Request,
    csrf: str = Form(...), username: str = Form(...), password: str = Form(...),
    response_type: str = Form(...), client_id: str = Form(...), redirect_uri: str = Form(...),
    state: str = Form(...), scope: str = Form(...), code_challenge: str = Form(...),
    code_challenge_method: str = Form(...), resource: str = Form(...), created_at: str = Form(...),
    db: Session = Depends(get_db),
):
    signed_request = _decode_oauth_request_cookie(request.cookies.get("agentledge_oauth_request", ""))
    cookie_csrf = request.cookies.get("agentledge_oauth_csrf", "")
    fields = {"response_type": response_type, "client_id": client_id, "redirect_uri": redirect_uri, "state": state, "scope": scope, "resource": resource, "code_challenge": code_challenge, "code_challenge_method": code_challenge_method, "created_at": created_at}
    if not signed_request or not hmac.compare_digest(csrf, cookie_csrf) or any(signed_request.get(key) != value for key, value in fields.items()):
        raise HTTPException(status_code=400, detail="OAuth authorization request expired or failed CSRF validation")
    try:
        created = int(created_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid authorization request")
    if created > int(_utcnow().timestamp()) or int(_utcnow().timestamp()) - created > 600:
        raise HTTPException(status_code=400, detail="OAuth authorization request expired")
    granted_scopes = _normalise_oauth_scopes(scope)
    if not granted_scopes or granted_scopes != signed_request.get("scope"):
        raise HTTPException(status_code=400, detail="The requested OAuth permissions changed; restart authorization")
    client = db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
    user = db.query(User).filter(User.username == username).first()
    if not client or redirect_uri not in json.loads(client.redirect_uris_json) or not user or not user.is_active or not verify_password(password, user.hashed_password):
        return HTMLResponse(_oauth_form_html(signed_request, csrf, "Sign-in failed. Check your account details and try again."), status_code=401)
    raw_code = secrets.token_urlsafe(32)
    db.add(OAuthAuthorizationCode(code_hash=_token_hash(raw_code), client_id=client_id, user_id=user.id, redirect_uri=redirect_uri, code_challenge=code_challenge, code_challenge_method="S256", scopes=granted_scopes, audience=resource, expires_at=_utcnow() + timedelta(seconds=OAUTH_CODE_TTL_SECONDS)))
    db.commit()
    target = redirect_uri + ("&" if "?" in redirect_uri else "?") + urlencode({"code": raw_code, "state": state, "iss": _oauth_issuer(request)})
    response = RedirectResponse(target, status_code=303)
    response.delete_cookie("agentledge_oauth_csrf", path="/oauth/authorize")
    response.delete_cookie("agentledge_oauth_request", path="/oauth/authorize")
    return response


@app.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(...), code: str = Form(...), redirect_uri: str = Form(...),
    client_id: str = Form(...), code_verifier: str = Form(...), resource: str = Form(...),
    db: Session = Depends(get_db),
):
    if grant_type != "authorization_code" or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", code_verifier):
        raise HTTPException(status_code=400, detail="Invalid authorization code grant")
    stored = db.query(OAuthAuthorizationCode).filter(OAuthAuthorizationCode.code_hash == _token_hash(code)).first()
    if (not stored or stored.client_id != client_id or stored.redirect_uri != redirect_uri
            or resource != stored.audience or stored.expires_at <= _utcnow()
            or not _pkce_matches(code_verifier, stored.code_challenge)):
        raise HTTPException(status_code=400, detail="Authorization code is invalid, expired, or does not match PKCE")
    if stored.code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Unsupported code challenge method")
    client = db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
    user = db.query(User).filter(User.id == stored.user_id, User.is_active.is_(True)).first()
    if not client or not user:
        raise HTTPException(status_code=400, detail="Authorization is no longer valid")
    access_token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(seconds=OAUTH_TOKEN_TTL_SECONDS)
    granted_scopes = _normalise_oauth_scopes(stored.scopes)
    if not granted_scopes:
        raise HTTPException(status_code=400, detail="Authorization contains unsupported permissions")
    deleted = db.query(OAuthAuthorizationCode).filter(
        OAuthAuthorizationCode.code_hash == stored.code_hash
    ).delete(synchronize_session=False)
    if deleted != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Authorization code has already been exchanged")
    db.add(OAuthAccessToken(token_hash=_token_hash(access_token), client_id=client_id, user_id=user.id, scopes=granted_scopes, audience=stored.audience, expires_at=expires_at))
    db.commit()
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": OAUTH_TOKEN_TTL_SECONDS, "scope": granted_scopes}


@app.post("/oauth/introspect")
async def oauth_introspect(request: Request, db: Session = Depends(get_db)):
    token = request.headers.get("authorization", "").partition(" ")[2]
    stored = db.query(OAuthAccessToken).filter(OAuthAccessToken.token_hash == _token_hash(token)).first()
    token_scopes = set(stored.scopes.split()) if stored else set()
    if (not stored or stored.revoked_at is not None or stored.expires_at <= _utcnow()
            or not token_scopes.issubset(OAUTH_SCOPES) or OAUTH_READ_SCOPE not in token_scopes
            or stored.audience != settings.AGENTMESH_MCP_RESOURCE_URL):
        return {"active": False}
    user = db.query(User).filter(User.id == stored.user_id, User.is_active.is_(True)).first()
    if user is None:
        return {"active": False}
    return {"active": True, "sub": str(user.id), "client_id": stored.client_id, "scope": stored.scopes, "exp": int(stored.expires_at.timestamp()), "iss": _oauth_issuer(request), "aud": stored.audience, "resource": stored.audience}


@app.post("/oauth/revoke")
async def oauth_revoke(token: str = Form(...), client_id: str = Form(...), db: Session = Depends(get_db)):
    """Revoke a token issued to the named public client; unknown tokens also succeed."""
    stored = db.query(OAuthAccessToken).filter(OAuthAccessToken.token_hash == _token_hash(token), OAuthAccessToken.client_id == client_id).first()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = _utcnow()
        db.commit()
    return JSONResponse(status_code=200, content={})

class SimulationRequest(BaseModel):
    task: str = Field(min_length=8, max_length=280)
    token_budget: int = Field(default=12, ge=1, le=1000)

class ActionApprovalCreate(BaseModel):
    action: Literal["start_negotiation", "submit_offer", "accept_negotiation", "reject_negotiation", "invoke_service", "submit_review"]
    payload: Dict[str, Any]

class ActionApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]


class AutonomousPolicyPatch(BaseModel):
    enabled: Optional[bool] = None
    max_task_budget: Optional[float] = Field(default=None, ge=0.01, le=1000)
    max_offer_price: Optional[float] = Field(default=None, ge=0.01, le=1000)
    max_daily_spend: Optional[float] = Field(default=None, ge=0.01, le=10000)
    allowed_categories: Optional[List[str]] = Field(default=None, max_length=30)
    allowed_listing_ids: Optional[List[int]] = Field(default=None, max_length=100)
    max_negotiation_attempts: Optional[int] = Field(default=None, ge=1, le=100)
    max_execution_retries: Optional[int] = Field(default=None, ge=0, le=3)
    auto_review: Optional[bool] = None

class NegotiationCreateRequest(BaseModel):
    agent_id: int
    buyer_budget: float = Field(gt=0, le=100000)
    initial_offer: float = Field(gt=0, le=100000)

class NegotiationOfferRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)

class ProviderCounterRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)

def has_live_ai_key() -> bool:
    return (
        settings.AI_MODE.strip().lower() == "live"
        and has_provider_credentials()
        and bool(selected_model().strip())
    )


def live_provider_is_misconfigured() -> bool:
    return settings.AI_MODE.strip().lower() == "live" and (
        not has_provider_credentials() or not selected_model().strip()
    )


def _gemini_summarizer_is_configured() -> bool:
    try:
        return (
            settings.AI_MODE.strip().lower() == "live"
            and selected_provider() == "gemini"
            and has_provider_credentials()
            and bool(selected_model().strip())
        )
    except ValueError:
        return False


def _agent_execution_available(agent: Agent) -> bool:
    key = _agent_implementation(agent)
    if key == "gemini_text_summarizer":
        return _gemini_summarizer_is_configured()
    if key == "gemini_marketplace_service":
        return _gemini_summarizer_is_configured() and _gemini_listing_config_valid(agent)
    return key is not None


def _gemini_listing_config_valid(agent: Agent) -> bool:
    instructions = (agent.execution_instructions or "").strip()
    expected_input = (agent.expected_input or "").strip()
    output_format = (agent.output_format or "").strip()
    if not instructions or len(instructions) > 8000 or not expected_input or len(expected_input) > 2000:
        return False
    if not output_format or len(output_format) > 1000:
        return False
    if agent.input_schema_json:
        try:
            schema = json.loads(agent.input_schema_json)
        except (TypeError, json.JSONDecodeError):
            return False
        if not isinstance(schema, dict) or schema.get("type", "object") != "object":
            return False
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        supported_types = {"string", "number", "integer", "boolean", "object", "array"}
        if (not isinstance(properties, dict) or not isinstance(required, list)
                or any(not isinstance(key, str) or key not in properties for key in required)):
            return False
        if any(not isinstance(definition, dict)
               or definition.get("type", "string") not in supported_types
               for definition in properties.values()):
            return False
    return True

@app.get("/system/status")
async def system_status():
    if settings.AI_MODE.strip().lower() == "live" and not has_provider_credentials():
        message = "AI_MODE=live but the selected provider API key is not configured."
    elif settings.AI_MODE.strip().lower() == "live" and not selected_model().strip():
        message = "AI_MODE=live requires AI_MODEL to name a model supported by the selected provider."
    else:
        message = None
    return {
        "ai_mode": "error" if live_provider_is_misconfigured() else "live" if has_live_ai_key() else "demo",
        "provider": selected_provider(),
        "model": selected_model(),
        "message": message,
        "gemini_summarizer_available": _gemini_summarizer_is_configured(),
    }

@app.post("/simulation/run")
async def simulate_marketplace_flow(request: SimulationRequest):
    """Run an isolated presentation scenario; never writes to account or trust tables."""
    return run_marketplace_simulation(request.task.strip(), request.token_budget)

# Dependency to get current user
async def get_current_user(
    request: Request,
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
        oauth_token = db.query(OAuthAccessToken).filter(OAuthAccessToken.token_hash == _token_hash(token)).first()
        if oauth_token is not None:
            token_scopes = set(oauth_token.scopes.split())
            if (oauth_token.revoked_at is not None or oauth_token.expires_at <= _utcnow()
                    or not token_scopes.issubset(OAUTH_SCOPES)
                    or oauth_token.audience != settings.AGENTMESH_MCP_RESOURCE_URL):
                raise credentials_exception
            read_route = request.method == "GET" and bool(
                re.fullmatch(r"/agents(?:/\d+(?:/(?:reputation|reviews))?)?|/negotiations/\d+|/users/me/(?:autonomous-policy|marketplace-balance|negotiations|invocations(?:/\d+)?)", request.url.path)
            )
            write_route = request.method == "POST" and bool(
                re.fullmatch(r"/negotiations(?:/\d+/(?:offers|accept|reject))?|/agents/invoke/\d+|/agents/\d+/reviews|/mcp/action-approvals", request.url.path)
            )
            required_scope = OAUTH_READ_SCOPE if read_route else OAUTH_WRITE_SCOPE if write_route else None
            if not required_scope:
                raise HTTPException(status_code=403, detail="This API operation is not available to MCP clients")
            if required_scope not in token_scopes:
                raise HTTPException(status_code=403, detail=f"OAuth token requires {required_scope}")
            user = db.query(User).filter(User.id == oauth_token.user_id, User.is_active.is_(True)).first()
            if user is None:
                raise credentials_exception
            request.state.oauth_user_id = user.id
            request.state.oauth_client_id = oauth_token.client_id
            return user
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
    request: Request, db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(request=request, db=db, token=token)
    except HTTPException:
        return None

# Compatibility name referenced by the project's existing test fixture.
get_current_active_user = get_current_user


def _approved_action_payload(db: Session, user: User, action: str, payload: dict) -> dict:
    """Validate and snapshot the exact operation so approval cannot be reused for changed terms."""
    def required_number(key: str) -> float:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise HTTPException(status_code=422, detail=f"{key} must be a finite number")
        return float(value)

    if action == "start_negotiation":
        agent_id = payload.get("agent_id")
        if not isinstance(agent_id, int) or isinstance(agent_id, bool) or agent_id <= 0:
            raise HTTPException(status_code=422, detail="agent_id must be positive")
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.is_active.is_(True)).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Service not found")
        if agent.developer_id == user.id:
            raise HTTPException(status_code=400, detail="You cannot negotiate with your own listing")
        budget, offer = required_number("buyer_budget"), required_number("initial_offer")
        if budget <= 0 or offer <= 0 or offer > budget or budget > 100000:
            raise HTTPException(status_code=422, detail="Offer and budget are invalid or exceed the allowed budget")
        if budget < floor_for(agent):
            raise HTTPException(status_code=422, detail="Your authorized budget is below this provider's minimum price")
        return {"agent_id": agent.id, "service_name": agent.name, "buyer_budget": budget,
                "initial_offer": offer, "listed_price": agent.price}

    if action == "submit_review":
        agent_id, invocation_id, rating = payload.get("agent_id"), payload.get("invocation_id"), payload.get("rating")
        review_text = payload.get("review_text") or ""
        if (not isinstance(agent_id, int) or isinstance(agent_id, bool)
                or not isinstance(invocation_id, int) or isinstance(invocation_id, bool)
                or not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5):
            raise HTTPException(status_code=422, detail="Review needs valid service and execution IDs and a rating from 1 to 5")
        if not isinstance(review_text, str) or len(review_text) > 1000:
            raise HTTPException(status_code=422, detail="Review text must be 1000 characters or fewer")
        invocation = db.query(AgentInvocation).filter(
            AgentInvocation.id == invocation_id,
            AgentInvocation.agent_id == agent_id,
            AgentInvocation.user_id == user.id,
            AgentInvocation.status == "succeeded",
        ).first()
        if not invocation:
            raise HTTPException(status_code=403, detail="A completed invocation by you is required to review this service")
        if invocation.agent.developer_id == user.id:
            raise HTTPException(status_code=403, detail="You cannot review your own service")
        if invocation.review:
            raise HTTPException(status_code=409, detail="This execution has already been reviewed")
        return {"agent_id": agent_id, "service_name": invocation.agent.name,
                "invocation_id": invocation_id, "rating": rating, "review_text": review_text.strip()}

    negotiation_id = payload.get("negotiation_id")
    if not isinstance(negotiation_id, int) or isinstance(negotiation_id, bool) or negotiation_id <= 0:
        raise HTTPException(status_code=422, detail="negotiation_id must be positive")
    negotiation = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if action in {"submit_offer", "accept_negotiation", "reject_negotiation"}:
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")
        if action != "reject_negotiation" and negotiation.buyer_id != user.id:
            raise HTTPException(status_code=403, detail="Only the buyer can request this action approval")
        if action == "reject_negotiation" and user.id not in (negotiation.buyer_id, negotiation.provider_id):
            raise HTTPException(status_code=403, detail="Only a negotiation participant can request rejection")
        if action == "submit_offer":
            amount = required_number("amount")
            if amount <= 0 or amount > negotiation.buyer_budget:
                raise HTTPException(status_code=422, detail="Offer must be positive and within your approved budget")
            return {"negotiation_id": negotiation.id, "service_name": negotiation.agent.name,
                    "buyer_budget": negotiation.buyer_budget, "amount": amount}
        if action == "accept_negotiation":
            counter = next((item for item in reversed(negotiation.offers)
                            if item.actor_role == "provider" and item.action == "counter"), None)
            if negotiation.status != "awaiting_buyer" or not counter or counter.amount is None:
                raise HTTPException(status_code=409, detail="There is no provider counter-offer to approve")
            if counter.amount > negotiation.buyer_budget:
                raise HTTPException(status_code=409, detail="Provider counter exceeds the approved budget")
            return {"negotiation_id": negotiation.id, "service_name": negotiation.agent.name,
                    "agreed_price": float(counter.amount)}
        if negotiation.status not in ("open", "awaiting_buyer"):
            raise HTTPException(status_code=409, detail="This negotiation is already closed")
        return {"negotiation_id": negotiation.id, "service_name": negotiation.agent.name,
                "current_status": negotiation.status,
                "actor_role": "buyer" if negotiation.buyer_id == user.id else "provider"}

    if action == "invoke_service":
        agent_id = payload.get("agent_id")
        input_data = payload.get("input_data")
        idempotency_key = payload.get("idempotency_key")
        if not isinstance(agent_id, int) or not isinstance(input_data, dict):
            raise HTTPException(status_code=422, detail="agent_id and input_data are required")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 255:
            raise HTTPException(status_code=422, detail="A valid idempotency key is required")
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.is_active.is_(True)).first()
        if (not negotiation or not agent or negotiation.agent_id != agent.id
                or negotiation.buyer_id != user.id or negotiation.status != "accepted"
                or negotiation.agreed_price is None):
            raise HTTPException(status_code=409, detail="An accepted negotiation for this service is required")
        if _agent_implementation(agent) is None:
            raise HTTPException(status_code=409, detail="This listing has no executable implementation. No tokens will be charged.")
        return {"agent_id": agent.id, "service_name": agent.name, "negotiation_id": negotiation.id,
                "agreed_price": float(negotiation.agreed_price), "input_data": input_data,
                "idempotency_key": idempotency_key.strip()}

    raise HTTPException(status_code=422, detail="Unsupported action approval")


def _autonomous_policy(db: Session, user_id: int) -> AutonomousExecutionPolicy | None:
    return db.query(AutonomousExecutionPolicy).filter(
        AutonomousExecutionPolicy.user_id == user_id,
    ).first()


def _utc_day_start() -> datetime:
    now = _utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _autonomous_spend_today(db: Session, user_id: int, include_reserved: bool = False) -> float:
    statuses = ("settled", "reserved") if include_reserved else ("settled",)
    amount = db.query(func.coalesce(func.sum(TokenTransaction.amount), 0.0)).filter(
        TokenTransaction.user_id == user_id,
        TokenTransaction.status.in_(statuses),
        func.coalesce(TokenTransaction.settled_at, TokenTransaction.created_at) >= _utc_day_start(),
    ).scalar()
    return float(amount or 0.0)


def _autonomous_policy_payload(db: Session, user: User) -> dict:
    policy = _autonomous_policy(db, user.id)
    spent = _autonomous_spend_today(db, user.id)
    if policy is None:
        values = {
            "enabled": False, "max_task_budget": 5.0, "max_offer_price": 5.0,
            "max_daily_spend": 10.0, "allowed_categories": [], "allowed_listing_ids": [],
            "max_negotiation_attempts": 1, "max_execution_retries": 0, "auto_review": False,
        }
    else:
        values = {
            "enabled": policy.enabled, "max_task_budget": policy.max_task_budget,
            "max_offer_price": policy.max_offer_price, "max_daily_spend": policy.max_daily_spend,
            "allowed_categories": json.loads(policy.allowed_categories_json or "[]"),
            "allowed_listing_ids": json.loads(policy.allowed_listing_ids_json or "[]"),
            "max_negotiation_attempts": policy.max_negotiation_attempts,
            "max_execution_retries": policy.max_execution_retries, "auto_review": policy.auto_review,
        }
    return {**values, "token_balance": float(user.token_balance or 0),
            "spent_today": spent, "remaining_daily_budget": max(0.0, values["max_daily_spend"] - spent)}


def _enforce_autonomous_policy(
    db: Session, user: User, action: str, canonical_payload: dict,
    policy: AutonomousExecutionPolicy,
) -> None:
    """One policy gate shared by every OAuth marketplace mutation."""
    if not policy.enabled:
        raise HTTPException(status_code=403, detail="Autonomous execution is not enabled for this account")
    agent_id = canonical_payload.get("agent_id")
    negotiation_id = canonical_payload.get("negotiation_id")
    if agent_id is None and negotiation_id is not None:
        negotiation = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if negotiation is not None:
            agent_id = negotiation.agent_id
    agent = db.query(Agent).filter(Agent.id == agent_id).first() if agent_id is not None else None
    if not agent or not agent.is_active:
        raise HTTPException(status_code=404, detail="The service is not active")

    categories = {str(item).strip().casefold() for item in json.loads(policy.allowed_categories_json or "[]") if str(item).strip()}
    listing_ids = {int(item) for item in json.loads(policy.allowed_listing_ids_json or "[]")}
    if agent.id not in listing_ids and agent.category.strip().casefold() not in categories:
        raise HTTPException(status_code=403, detail="This service is outside the account's autonomous allowlist")

    if action == "start_negotiation":
        today_count = db.query(func.count(Negotiation.id)).filter(
            Negotiation.buyer_id == user.id, Negotiation.created_at >= _utc_day_start(),
        ).scalar() or 0
        if today_count >= policy.max_negotiation_attempts:
            raise HTTPException(status_code=429, detail="The account's daily autonomous negotiation limit has been reached")
        budget = float(canonical_payload["buyer_budget"])
        offer = float(canonical_payload["initial_offer"])
        if max(budget, offer) > min(policy.max_task_budget, policy.max_offer_price):
            raise HTTPException(status_code=403, detail="The negotiation budget exceeds the account's per-task or offer limit")
        if float(user.token_balance or 0) < budget:
            raise HTTPException(status_code=402, detail="Insufficient token balance for the autonomous negotiation budget")
    elif action in {"submit_offer", "accept_negotiation"}:
        price = float(canonical_payload.get("amount", canonical_payload.get("agreed_price", 0)))
        negotiation = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not negotiation or negotiation.buyer_id != user.id:
            raise HTTPException(status_code=403, detail="Only the negotiation buyer may act under this autonomous policy")
        if price > min(policy.max_task_budget, policy.max_offer_price, negotiation.buyer_budget):
            raise HTTPException(status_code=403, detail="The offer exceeds the account's autonomous price limit")
        if float(user.token_balance or 0) < price:
            raise HTTPException(status_code=402, detail="Insufficient token balance for this offer")
    elif action == "invoke_service":
        negotiation = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not negotiation or negotiation.agent_id != agent.id or negotiation.buyer_id != user.id:
            raise HTTPException(status_code=403, detail="An accepted negotiation belonging to this account is required")
        if negotiation.status != "accepted" or negotiation.agreed_price is None:
            raise HTTPException(status_code=409, detail="The negotiation must be accepted before autonomous execution")
        price = float(negotiation.agreed_price)
        if price > min(policy.max_task_budget, policy.max_offer_price):
            raise HTTPException(status_code=403, detail="The agreed price exceeds the account's autonomous limit")
        spent = _autonomous_spend_today(db, user.id, include_reserved=True)
        if spent + price > policy.max_daily_spend:
            raise HTTPException(status_code=403, detail="The account's daily autonomous spending limit would be exceeded")
        if float(user.token_balance or 0) < price:
            raise HTTPException(status_code=402, detail="Insufficient marketplace token balance")
    elif action == "submit_review":
        if not policy.auto_review:
            raise HTTPException(status_code=403, detail="Automatic reviews are disabled by the account policy")
        if canonical_payload.get("rating") != 5:
            raise HTTPException(status_code=403, detail="Autonomous reviews are restricted to evidence-based completion reviews")


def _authorize_oauth_action(request: Request, db: Session, user: User, action: str, payload: dict) -> None:
    oauth_user_id = getattr(request.state, "oauth_user_id", None)
    if oauth_user_id is None:
        return
    if oauth_user_id != user.id:
        raise HTTPException(status_code=403, detail="OAuth identity does not match the authenticated account")
    policy = _autonomous_policy(db, user.id)
    if policy and policy.enabled:
        canonical = _approved_action_payload(db, user, action, payload)
        _enforce_autonomous_policy(db, user, action, canonical, policy)
        return
    _consume_oauth_action_approval(request, db, user, action, payload)


def _ensure_evidence_review(db: Session, user: User, invocation: AgentInvocation) -> dict | None:
    if invocation.status != "succeeded" or invocation.agent.developer_id == user.id:
        return None
    existing = db.query(AgentReview).filter(AgentReview.invocation_id == invocation.id).first()
    if existing:
        return {"id": existing.id, "rating": existing.rating, "invocation_id": existing.invocation_id}
    try:
        saved = json.loads(invocation.output_data or "{}")
        output_text = str(saved.get("output_text", "")).strip()
        if not output_text:
            return None
        review = create_verified_review(
            db, user, invocation.agent_id, invocation.id, 5,
            "Automated execution review: the service completed successfully and returned a non-empty result.",
        )
        return {"id": review.id, "rating": review.rating, "invocation_id": review.invocation_id}
    except (ValueError, PermissionError, FileExistsError, IntegrityError, TypeError, json.JSONDecodeError):
        db.rollback()
        return None


def _consume_oauth_action_approval(
    request: Request, db: Session, user: User, action: str, payload: dict,
) -> None:
    oauth_user_id = getattr(request.state, "oauth_user_id", None)
    if oauth_user_id is None:
        return
    if oauth_user_id != user.id:
        raise HTTPException(status_code=403, detail="OAuth identity does not match the authenticated account")
    approval_id = request.headers.get("X-User-Approval", "").strip()
    if not approval_id:
        raise HTTPException(status_code=403, detail="Approve this exact action in the AgentsLedge website first")
    approval = db.query(OAuthActionApproval).filter(
        OAuthActionApproval.id == approval_id,
        OAuthActionApproval.user_id == user.id,
    ).with_for_update().first()
    if not approval or approval.status != "approved" or approval.expires_at <= _utcnow():
        raise HTTPException(status_code=403, detail="This action approval is missing, expired, or already used")
    current_payload = _approved_action_payload(db, user, action, payload)
    if approval.action != action or approval.payload_json != _canonical_approval_json(current_payload):
        raise HTTPException(status_code=409, detail="The approved action details changed; request approval again")
    approval.status = "consumed"
    approval.consumed_at = _utcnow()
    db.commit()


def _canonical_approval_json(payload: dict) -> str:
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Approval details must contain valid JSON values") from error


@app.post("/mcp/action-approvals")
async def create_oauth_action_approval(
    request: Request, body: ActionApprovalCreate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if getattr(request.state, "oauth_user_id", None) != current_user.id:
        raise HTTPException(status_code=403, detail="Action approval requests are available only to AgentMesh OAuth clients")
    canonical = _approved_action_payload(db, current_user, body.action, body.payload)
    policy = _autonomous_policy(db, current_user.id)
    if policy and policy.enabled:
        _enforce_autonomous_policy(db, current_user, body.action, canonical, policy)
        return {"approval_required": False, "autonomous_authorized": True,
                "action": body.action, "policy": _autonomous_policy_payload(db, current_user)}
    approval = OAuthActionApproval(
        id=secrets.token_urlsafe(24), user_id=current_user.id, action=body.action,
        payload_json=_canonical_approval_json(canonical),
        status="pending", expires_at=_utcnow() + timedelta(minutes=10),
    )
    db.add(approval)
    db.commit()
    return {"approval_id": approval.id, "action": approval.action, "payload": canonical,
            "status": approval.status, "expires_at": approval.expires_at.isoformat(),
            "approval_path": "/approvals"}


@app.get("/users/me/action-approvals")
async def list_my_action_approvals(
    request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if getattr(request.state, "oauth_user_id", None) is not None:
        raise HTTPException(status_code=403, detail="Use your AgentsLedge website session to review approvals")
    rows = db.query(OAuthActionApproval).filter(
        OAuthActionApproval.user_id == current_user.id,
        OAuthActionApproval.status == "pending",
        OAuthActionApproval.expires_at > _utcnow(),
    ).order_by(OAuthActionApproval.created_at.asc()).all()
    return [{"approval_id": item.id, "action": item.action,
             "payload": json.loads(item.payload_json), "expires_at": item.expires_at.isoformat()}
            for item in rows]


@app.post("/users/me/action-approvals/{approval_id}")
async def decide_action_approval(
    approval_id: str, decision: ActionApprovalDecision, request: Request,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if getattr(request.state, "oauth_user_id", None) is not None:
        raise HTTPException(status_code=403, detail="Approvals must be decided in your signed-in website session")
    approval = db.query(OAuthActionApproval).filter(
        OAuthActionApproval.id == approval_id, OAuthActionApproval.user_id == current_user.id,
    ).with_for_update().first()
    if not approval or approval.status != "pending" or approval.expires_at <= _utcnow():
        raise HTTPException(status_code=404, detail="Pending approval not found or expired")
    approval.status = "approved" if decision.decision == "approve" else "rejected"
    approval.approved_at = _utcnow() if decision.decision == "approve" else None
    db.commit()
    return {"approval_id": approval.id, "status": approval.status}

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
    is_active: Optional[bool] = None
    implementation_key: Optional[str] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=80)
    capabilities: Optional[str] = Field(default=None, max_length=1000)
    price: Optional[float] = Field(default=None, ge=0)
    minimum_price: Optional[float] = Field(default=None, ge=0)
    execution_instructions: Optional[str] = Field(default=None, max_length=8000)
    expected_input: Optional[str] = Field(default=None, max_length=2000)
    input_schema_json: Optional[str] = Field(default=None, max_length=8000)
    output_format: Optional[str] = Field(default=None, max_length=1000)


class AdminAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="General", min_length=1, max_length=80)
    capabilities: str = Field(default="", max_length=1000)
    price: float = Field(ge=0)
    minimum_price: Optional[float] = Field(default=None, ge=0)

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
        "description": agent.description, "capabilities": agent.capabilities,
        "price": agent.price, "minimum_price": agent.minimum_price,
        "developer_id": agent.developer_id, "is_active": agent.is_active,
        "implementation_key": agent.implementation_key,
        "execution_instructions": agent.execution_instructions,
        "expected_input": agent.expected_input,
        "input_schema_json": agent.input_schema_json,
        "output_format": agent.output_format,
        "execution_available": _agent_execution_available(agent),
        "gemini_execution_enabled": agent.implementation_key in {"gemini_text_summarizer", "gemini_marketplace_service"}
            and _agent_execution_available(agent),
    } for agent in db.query(Agent).order_by(Agent.created_at.desc()).all()]


@app.post("/admin/agents")
async def admin_create_agent(
    payload: AdminAgentCreate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db),
):
    if payload.minimum_price is not None and payload.minimum_price > payload.price:
        raise HTTPException(status_code=422, detail="Minimum acceptable price cannot exceed the listed price")
    agent = Agent(
        name=payload.name.strip(), description=payload.description.strip(),
        category=payload.category.strip(), capabilities=payload.capabilities.strip(),
        price=payload.price, minimum_price=payload.minimum_price,
        developer_id=admin.id, is_active=True, implementation_key=None,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"id": agent.id, "name": agent.name, "category": agent.category,
            "developer_id": agent.developer_id, "is_active": agent.is_active,
            "implementation_key": None, "execution_instructions": None,
            "expected_input": None, "input_schema_json": None, "output_format": None,
            "execution_available": False, "gemini_execution_enabled": False}

@app.patch("/admin/agents/{agent_id}")
async def admin_update_agent(
    agent_id: int, update: AgentAdminUpdate, admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    fields = update.model_fields_set
    if not fields:
        raise HTTPException(status_code=422, detail="Provide at least one listing field to update")
    if "implementation_key" in fields and update.implementation_key not in (None, "gemini_text_summarizer", "gemini_marketplace_service"):
        raise HTTPException(status_code=422, detail="Only supported Gemini implementations can be assigned here")
    for field in ("is_active", "implementation_key", "name", "description", "category", "capabilities", "price", "minimum_price",
                  "execution_instructions", "expected_input", "input_schema_json", "output_format"):
        if field in fields:
            setattr(agent, field, getattr(update, field))
    if agent.minimum_price is not None and agent.price is not None and agent.minimum_price > agent.price:
        db.rollback()
        raise HTTPException(status_code=422, detail="Minimum acceptable price cannot exceed the listed price")
    if agent.implementation_key == "gemini_marketplace_service" and not _gemini_listing_config_valid(agent):
        db.rollback()
        raise HTTPException(status_code=422, detail="Gemini execution requires valid instructions, expected input, output format, and an optional JSON object schema")
    db.commit()
    return {
        "id": agent.id, "name": agent.name, "is_active": agent.is_active,
        "implementation_key": agent.implementation_key,
        "execution_instructions": agent.execution_instructions,
        "expected_input": agent.expected_input,
        "input_schema_json": agent.input_schema_json,
        "output_format": agent.output_format,
        "execution_available": _agent_execution_available(agent),
        "gemini_execution_enabled": agent.implementation_key in {"gemini_text_summarizer", "gemini_marketplace_service"}
            and _agent_execution_available(agent),
    }

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
    return AgentResponse.model_validate(db_agent).model_copy(update={"execution_available": _agent_execution_available(db_agent)})

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
    return AgentResponse.model_validate(agent).model_copy(update={"execution_available": _agent_execution_available(agent)})

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
    response: Response,
    query: str = Query(default="", max_length=120),
    category: str = Query(default="", max_length=80),
    sort: str = Query(default="relevance", pattern="^(relevance|rating|success_rate|price|price_asc|price_desc)$"),
    max_price: float = Query(default=None, ge=0, le=100000),
    minimum_rating: float = Query(default=None, ge=0, le=5),
    minimum_success_rate: float = Query(default=None, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Search active services with real reputation filters and offset pagination."""
    agents = discover_agents(db, query=query, category=category, sort=sort,
                             max_price=max_price, minimum_rating=minimum_rating,
                             minimum_success_rate=minimum_success_rate)
    response.headers["X-Total-Count"] = str(len(agents))
    response.headers["X-Results-Complete"] = str(offset + limit >= len(agents)).lower()
    
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
            execution_available=_agent_execution_available(agent),
            created_at=agent.created_at,
            category=agent.category,
            capabilities=agent.capabilities,
            average_rating=agent.average_rating,
            review_count=agent.review_count,
            success_rate=agent.success_rate,
            completed_invocations=agent.completed_invocations,
        )
        for agent in agents[offset:offset + limit]
    ]


@app.get("/marketplace/categories")
async def list_agent_categories(db: Session = Depends(get_db)):
    """Return categories that currently have active listings."""
    values = db.query(Agent.category).filter(Agent.is_active.is_(True)).distinct().all()
    return sorted({value[0].strip() for value in values if value[0] and value[0].strip()}, key=str.casefold)

@app.get("/users/me/agents", response_model=List[AgentResponse])
async def list_my_agents(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Return all listings owned by the signed-in service provider, including drafts."""
    agents = db.query(Agent).filter(Agent.developer_id == current_user.id).order_by(Agent.created_at.desc()).all()
    return [AgentResponse.model_validate(agent).model_copy(update={
        "minimum_price": floor_for(agent), **(reputation_for_agent(db, agent.id) or {}),
            "execution_available": _agent_execution_available(agent),
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
        execution_available=_agent_execution_available(agent),
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
    http_request: Request,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Service not found")
    if agent.minimum_price is not None and (agent.minimum_price < 0 or agent.minimum_price > agent.price):
        raise HTTPException(status_code=409, detail="This listing has an invalid provider minimum price")
    if getattr(http_request.state, "oauth_user_id", None) == current_user.id:
        existing_policy = _autonomous_policy(db, current_user.id)
        if existing_policy and existing_policy.enabled:
            existing = db.query(Negotiation).filter(
                Negotiation.buyer_id == current_user.id, Negotiation.agent_id == agent.id,
                Negotiation.status == "accepted",
            ).order_by(Negotiation.created_at.desc()).first()
            if existing:
                return negotiation_payload(existing)
    _authorize_oauth_action(http_request, db, current_user, "start_negotiation", request.model_dump())
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
    http_request: Request,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    _authorize_oauth_action(http_request, db, current_user, "submit_offer",
                                   {"negotiation_id": negotiation_id, "amount": request.amount})
    return negotiation_payload(buyer_offer(db, item, current_user, request.amount))

@app.post("/negotiations/{negotiation_id}/accept")
async def accept_negotiation_counter(
    negotiation_id: int, http_request: Request,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    _authorize_oauth_action(http_request, db, current_user, "accept_negotiation", {"negotiation_id": negotiation_id})
    return negotiation_payload(accept_counter(db, item, current_user))

@app.post("/negotiations/{negotiation_id}/reject")
async def reject_negotiation_endpoint(
    negotiation_id: int, http_request: Request,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    item = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    _authorize_oauth_action(http_request, db, current_user, "reject_negotiation", {"negotiation_id": negotiation_id})
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
        "gemini_text_summarizer": "gemini_text_summarizer",
        "gemini_marketplace_service": "gemini_marketplace_service",
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
    if agent_key == "gemini_text_summarizer":
        return await agent_instance.process_request(input_text=payload.get("input_text", generic_text))
    if agent_key == "gemini_marketplace_service":
        return await agent_instance.process_request(
            instructions=payload["_service_instructions"],
            expected_input=payload["_expected_input"],
            input_schema=payload["_input_schema"],
            output_format=payload["_output_format"],
            input_data=payload["_user_input"],
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
    http_request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.implementation_key == "gemini_text_summarizer" and not _gemini_summarizer_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini summarization is not configured for live execution. Set AI_PROVIDER=gemini, AI_MODE=live, GEMINI_API_KEY, and a supported AI_MODEL. No tokens were charged.",
        )
    agent_key = _agent_implementation(agent)
    if not agent_key:
        raise HTTPException(status_code=409, detail="This listing is discoverable but has no executable implementation. No tokens were charged.")
    agent_instance = AVAILABLE_AGENTS.get(agent_key)
    if not agent_instance:
        raise HTTPException(status_code=409, detail="This listing's supported implementation is unavailable. No tokens were charged.")
    if agent_key == "gemini_marketplace_service":
        if not _gemini_listing_config_valid(agent):
            raise HTTPException(status_code=409, detail="Gemini execution is disabled or its listing configuration is invalid. No tokens were charged.")
        if not _gemini_summarizer_is_configured():
            raise HTTPException(status_code=503, detail="Gemini is not configured for live execution. No tokens were charged.")

    # Paid marketplace use is authorized by a persisted agreement. The agreed
    # backend price, never a client-supplied amount, governs settlement.
    negotiation_id = input_data.pop("negotiation_id", None)
    body_idempotency_key = input_data.pop("idempotency_key", None)
    client_supplied_key = bool(idempotency_key or body_idempotency_key)
    request_key = (idempotency_key or body_idempotency_key or str(uuid4())).strip()
    if not request_key:
        raise HTTPException(status_code=422, detail="Idempotency-Key cannot be empty")
    persisted_input = json.dumps(input_data, sort_keys=True, separators=(",", ":"))
    execution_data = input_data
    if len(request_key) > 255:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be at most 255 characters")
    if agent_key == "gemini_text_summarizer":
        summary_text = input_data.get("input_text")
        if not isinstance(summary_text, str) or not summary_text.strip():
            raise HTTPException(status_code=422, detail="input_text must contain non-whitespace text")
        if len(summary_text) > 20000:
            raise HTTPException(status_code=422, detail="input_text must be at most 20000 characters")
    elif agent_key == "gemini_marketplace_service":
        if not input_data or not isinstance(input_data, dict):
            raise HTTPException(status_code=422, detail="Provide a non-empty JSON object as service input")
        if len(persisted_input) > 30000:
            raise HTTPException(status_code=422, detail="Service input must be at most 30000 characters")
        config_data = input_data
        if agent.input_schema_json:
            schema = json.loads(agent.input_schema_json)
            required = schema.get("required", [])
            if not isinstance(required, list) or any(key not in config_data for key in required):
                raise HTTPException(status_code=422, detail="Input is missing fields required by this service")
            properties = schema.get("properties", {})
            type_checks = {
                "string": lambda value: isinstance(value, str),
                "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
                "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
                "boolean": lambda value: isinstance(value, bool),
                "object": lambda value: isinstance(value, dict),
                "array": lambda value: isinstance(value, list),
            }
            for key, value in config_data.items():
                definition = properties.get(key)
                if definition is None and schema.get("additionalProperties") is False:
                    raise HTTPException(status_code=422, detail=f"Input contains unsupported field: {key}")
                if definition is not None and not type_checks[definition.get("type", "string")](value):
                    raise HTTPException(status_code=422, detail=f"Input field '{key}' has the wrong type")
        execution_data = {
            "_service_instructions": agent.execution_instructions,
            "_expected_input": agent.expected_input,
            "_input_schema": json.loads(agent.input_schema_json) if agent.input_schema_json else None,
            "_output_format": agent.output_format,
            "_user_input": config_data,
        }
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
            autonomous = _autonomous_policy(db, current_user.id) if getattr(http_request.state, "oauth_user_id", None) == current_user.id else None
            automatic_review = _ensure_evidence_review(db, current_user, existing) if autonomous and autonomous.enabled and autonomous.auto_review and existing.status == "succeeded" else None
            return {
                **stored, "output_text": stored.get("output_text", ""),
                "invocation_id": existing.id, "demo_mode": existing.status == "demo",
                "idempotency_key": request_key, "settlement_status": existing.token_transaction.status if existing.token_transaction else "not_charged",
                "charged_tokens": existing.token_transaction.amount if existing.token_transaction and existing.token_transaction.status == "settled" else 0,
                "agreed_price": existing.negotiation.agreed_price if existing.negotiation else 0,
                "remaining_balance": current_user.token_balance,
                "automatic_review": automatic_review,
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
    
    if live_provider_is_misconfigured():
        raise HTTPException(status_code=503, detail=f"AI_MODE=live but the {selected_provider()} API key is not configured. No demo response was substituted and no tokens were charged.")

    _authorize_oauth_action(http_request, db, current_user, "invoke_service", {
        "agent_id": agent_id, "negotiation_id": negotiation_id,
        "input_data": input_data, "idempotency_key": request_key,
    })
    
    auto_policy = None
    if getattr(http_request.state, "oauth_user_id", None) == current_user.id:
        auto_policy = _autonomous_policy(db, current_user.id)
        if not auto_policy or not auto_policy.enabled:
            auto_policy = None
    reserved_invocation = None
    reserved_transaction = None
    charge = float(negotiation.agreed_price) if negotiation else 0.0
    will_execute_live = has_live_ai_key()
    if will_execute_live and charge > 0:
        if auto_policy:
            locked_policy = db.query(AutonomousExecutionPolicy).filter(
                AutonomousExecutionPolicy.user_id == current_user.id,
            ).with_for_update().first()
            spent_or_reserved = _autonomous_spend_today(db, current_user.id, include_reserved=True)
            if not locked_policy or not locked_policy.enabled or spent_or_reserved + charge > locked_policy.max_daily_spend:
                db.rollback()
                raise HTTPException(status_code=403, detail="The account's daily autonomous spending limit would be exceeded")
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
            retries = auto_policy.max_execution_retries if auto_policy else 0
            for attempt in range(retries + 1):
                try:
                    result = await call_builtin_agent(agent_key, agent_instance, execution_data)
                    if result.get("status") == "error" or result.get("error"):
                        raise RuntimeError("Agent returned an unsuccessful result")
                    break
                except Exception:
                    if attempt >= retries:
                        raise
                    await asyncio.sleep(0.1 * (attempt + 1))

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
        response_result = {
            **result,
            "output_text": output_text,
            "execution_mode": "demo" if demo_mode else "live",
            "provider": None if demo_mode else selected_provider(),
            "model": None if demo_mode else selected_model(),
            "demo_mode": demo_mode,
            "demo_notice": "Sample response only; no AI model processed this request." if demo_mode else None,
        }
        
        # Record the invocation
        if reserved_invocation:
            db_invocation = reserved_invocation
            db_invocation.output_data = json.dumps(response_result, ensure_ascii=False)
            db_invocation.tokens_used = tokens_used
            db_invocation.status = "demo" if demo_mode else "succeeded"
            if reserved_transaction:
                if demo_mode:
                    db.execute(update(User).where(User.id == current_user.id).values(token_balance=User.token_balance + charge))
                    reserved_transaction.status = "released"
                    reserved_transaction.settled_at = _utcnow()
                else:
                    db.execute(update(User).where(User.id == agent.developer_id).values(token_balance=User.token_balance + charge))
                    reserved_transaction.status = "settled"
                    reserved_transaction.settled_at = _utcnow()
        else:
            db_invocation = AgentInvocation(
                user_id=current_user.id, agent_id=agent_id,
                negotiation_id=negotiation.id if negotiation else None,
                idempotency_key=request_key,
                input_data=persisted_input, output_data=json.dumps(response_result, ensure_ascii=False),
                tokens_used=tokens_used, status="demo" if demo_mode else "succeeded",
            )
            db.add(db_invocation)
        db.commit()
        db.refresh(db_invocation)
        db.refresh(current_user)
        automatic_review = _ensure_evidence_review(db, current_user, db_invocation) if (
            auto_policy and auto_policy.auto_review and not demo_mode and db_invocation.status == "succeeded"
        ) else None
        return {
            **response_result,
            "output_text": output_text,
            "output_data": output_text,
            "tokens_used": tokens_used,
            "invocation_id": db_invocation.id,
            "agreed_price": charge if negotiation else 0,
            "charged_tokens": charge if (reserved_transaction and not demo_mode) else 0,
            "settlement_status": reserved_transaction.status if reserved_transaction else "not_charged",
            "remaining_balance": current_user.token_balance,
            "idempotency_key": request_key,
            "automatic_review": automatic_review,
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
            reserved_transaction.settled_at = _utcnow()
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"The configured {selected_provider()} provider could not complete this request. Verify its API key, AI_MODE=live, and AI_MODEL. No demo response was substituted.",
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


@app.get("/users/me/autonomous-policy")
async def get_my_autonomous_policy(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _autonomous_policy_payload(db, current_user)


@app.patch("/users/me/autonomous-policy")
async def update_my_autonomous_policy(
    body: AutonomousPolicyPatch, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    changes = body.model_dump(exclude_unset=True)
    policy = _autonomous_policy(db, current_user.id)
    if policy is None:
        policy = AutonomousExecutionPolicy(user_id=current_user.id)
        db.add(policy)
        db.flush()
    if "allowed_categories" in changes:
        categories = changes.pop("allowed_categories")
        if categories is not None:
            cleaned = sorted({item.strip() for item in categories if item.strip()})
            if any(len(item) > 80 for item in cleaned):
                raise HTTPException(status_code=422, detail="Allowed categories must be 80 characters or fewer")
            policy.allowed_categories_json = json.dumps(cleaned)
    if "allowed_listing_ids" in changes:
        listing_ids = changes.pop("allowed_listing_ids")
        if listing_ids is not None:
            if any(item <= 0 for item in listing_ids):
                raise HTTPException(status_code=422, detail="Allowed listing IDs must be positive")
            policy.allowed_listing_ids_json = json.dumps(sorted(set(listing_ids)))
    for key, value in changes.items():
        setattr(policy, key, value)
    if policy.enabled and not json.loads(policy.allowed_categories_json or "[]") and not json.loads(policy.allowed_listing_ids_json or "[]"):
        db.rollback()
        raise HTTPException(status_code=422, detail="Enable at least one allowed category or listing before turning on autonomous mode")
    if policy.enabled:
        # Older manual-mode requests must not keep prompting after the owner
        # explicitly switches this account to policy-based authorization.
        db.query(OAuthActionApproval).filter(
            OAuthActionApproval.user_id == current_user.id,
            OAuthActionApproval.status == "pending",
        ).update({OAuthActionApproval.status: "cancelled"}, synchronize_session=False)
    policy.updated_at = _utcnow()
    db.commit()
    return _autonomous_policy_payload(db, current_user)


@app.get("/users/me/marketplace-balance")
async def get_my_marketplace_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    policy = _autonomous_policy(db, current_user.id)
    daily_limit = policy.max_daily_spend if policy else 10.0
    spent = _autonomous_spend_today(db, current_user.id)
    return {"token_balance": float(current_user.token_balance or 0), "spent_today": spent,
            "daily_limit": daily_limit, "remaining_daily_budget": max(0.0, daily_limit - spent)}

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


@app.get("/users/me/invocations/{invocation_id}")
async def get_user_invocation_result(
    invocation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return one invocation only when it belongs to the authenticated user."""
    invocation = db.query(AgentInvocation).filter(
        AgentInvocation.id == invocation_id,
        AgentInvocation.user_id == current_user.id,
    ).first()
    if invocation is None:
        raise HTTPException(status_code=404, detail="Invocation not found")
    try:
        result = json.loads(invocation.output_data or "{}")
    except (TypeError, json.JSONDecodeError):
        result = {}
    transaction = invocation.token_transaction
    return {
        "invocation_id": invocation.id,
        "agent_id": invocation.agent_id,
        "agent_name": invocation.agent.name,
        "negotiation_id": invocation.negotiation_id,
        "status": invocation.status,
        "execution_mode": result.get("execution_mode", "demo" if invocation.status == "demo" else "live" if invocation.status == "succeeded" else "failed"),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "result": result,
        "tokens_used": invocation.tokens_used,
        "settlement_status": transaction.status if transaction else "not_charged",
        "amount_charged": transaction.amount if transaction and transaction.status == "settled" else 0,
        "created_at": invocation.created_at.isoformat() if invocation.created_at else None,
    }

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
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _authorize_oauth_action(http_request, db, current_user, "submit_review", {
        "agent_id": agent_id, **review.model_dump(),
    })
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
    "technical_troubleshooter": TechnicalTroubleshooterAgent(),
    "gemini_text_summarizer": GeminiTextSummarizerAgent(),
    "gemini_marketplace_service": GeminiMarketplaceAgent(),
}

# Map agent display names to implementation keys
AGENT_NAME_TO_KEY = {
    "Interview Prep Assistant": "interview_prep",
    "Code Reviewer": "code_reviewer",
    "Resume Reviewer": "resume_reviewer",
    "Technical Troubleshooter": "technical_troubleshooter",
    "Writing Assistant": "writing_assistant"
}


def _agent_implementation(agent: Agent) -> Optional[str]:
    key = agent.implementation_key
    return key if key and key in AVAILABLE_AGENTS else None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
