from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")

class Settings(BaseSettings):
    # API Keys and Secrets
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    AI_PROVIDER: str = "openai"
    AI_MODEL: str = ""
    # Fast, capable general-purpose default for the marketplace's task agents.
    OPENAI_MODEL: str = "gpt-4.1-mini"
    # Local demo mode is the safe default for a new checkout without API billing.
    AI_MODE: str = "demo"
    # Comma-separated browser origins; include the deployed frontend explicitly.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    SECRET_KEY: str
    DATABASE_URL: str
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str = "whsec_test"  # Default test webhook secret
    
    # Application Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    ALGORITHM: str = "HS256"
    # Canonical public API origin used in OAuth metadata after HTTPS hosting.
    OAUTH_ISSUER: str = "http://127.0.0.1:8000"
    AGENTMESH_MCP_RESOURCE_URL: str = "http://127.0.0.1:8011/mcp"
    OAUTH_RATE_LIMIT_PER_MINUTE: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()
