from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime

# Token schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_developer: bool = False
    is_admin: bool = False

class UserCreate(UserBase):
    password: str
    # Provider status may be self-selected; admin status is always ignored by
    # the registration route and must be granted through trusted setup.
    is_developer: bool = False
    is_admin: bool = False

class UserResponse(UserBase):
    id: int
    token_balance: float
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Agent schemas
class AgentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    price: float = Field(ge=0)
    minimum_price: Optional[float] = Field(default=None, ge=0)
    category: str = Field(default="General", min_length=1, max_length=80)
    capabilities: str = Field(default="", max_length=1000)

    @field_validator("name", "description", "category", "capabilities")
    @classmethod
    def trim_text_fields(cls, value: str, info) -> str:
        cleaned = value.strip()
        if not cleaned and info.field_name != "capabilities":
            raise ValueError(f"{info.field_name} cannot be blank")
        return cleaned

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: int
    developer_id: int
    is_active: bool
    is_purchased: bool = False
    execution_available: bool = False
    average_rating: Optional[float] = None
    review_count: int = 0
    success_rate: Optional[float] = None
    completed_invocations: int = 0

    class Config:
        from_attributes = True

# Purchase schemas
class PurchaseBase(BaseModel):
    agent_id: int
    purchase_price: float

class PurchaseCreate(BaseModel):
    agent_id: int

class AgentPurchaseResponse(PurchaseBase):
    purchase_id: int
    remaining_balance: float

    class Config:
        from_attributes = True

# Invocation schemas
class CodeReviewInvocation(BaseModel):
    code: str
    language: str = "python"
    context: Optional[str] = None

class ResumeReviewInvocation(BaseModel):
    resume_text: str
    context: Optional[str] = None

class InterviewPrepInvocation(BaseModel):
    topic: str
    experience_level: str = "entry"
    context: Optional[str] = None

class WritingAssistantInvocation(BaseModel):
    text: str
    style: Optional[str] = None
    context: Optional[str] = None

class TechnicalTroubleshootingInvocation(BaseModel):
    problem: str
    system_info: Optional[str] = None
    context: Optional[str] = None

class InvocationBase(BaseModel):
    agent_type: str
    code_review: Optional[CodeReviewInvocation] = None
    resume_review: Optional[ResumeReviewInvocation] = None
    interview_prep: Optional[InterviewPrepInvocation] = None
    writing_assistant: Optional[WritingAssistantInvocation] = None
    technical_troubleshooting: Optional[TechnicalTroubleshootingInvocation] = None

class InvocationCreate(InvocationBase):
    pass

class InvocationResponse(BaseModel):
    id: int
    purchase_id: int
    input_text: str
    output_text: Optional[str] = None
    tokens_used: int
    created_at: datetime

    class Config:
        from_attributes = True

# Marketplace schemas
class TokenPurchase(BaseModel):
    amount: int
    currency: str = "usd"

class TokenBalance(BaseModel):
    balance: float
    transaction_id: str

class DeveloperEarnings(BaseModel):
    earnings: float
