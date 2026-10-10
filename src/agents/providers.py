"""Credential-safe factory for OpenAI-compatible model providers.

Marketplace, negotiation, persistence, and settlement code never depends on
the provider SDK or provider-specific credentials.
"""
from openai import AsyncOpenAI

from src.config import get_settings

GEMINI_OPENAI_COMPATIBLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def selected_provider() -> str:
    name = get_settings().AI_PROVIDER.strip().lower()
    if name not in {"openai", "gemini"}:
        raise ValueError("AI_PROVIDER must be 'openai' or 'gemini'")
    return name


def selected_api_key() -> str:
    settings = get_settings()
    return (settings.GEMINI_API_KEY if selected_provider() == "gemini" else settings.OPENAI_API_KEY).strip()


def has_provider_credentials() -> bool:
    key = selected_api_key()
    return bool(key) and key.lower() not in {
        "your-openai-api-key-here", "your-gemini-api-key-here", "sk-your-api-key", "replace-me", "none"
    }


def create_model_client() -> AsyncOpenAI:
    provider = selected_provider()
    key = selected_api_key()
    if provider == "gemini":
        return AsyncOpenAI(api_key=key or "demo-mode-no-key", base_url=GEMINI_OPENAI_COMPATIBLE_BASE_URL)
    return AsyncOpenAI(api_key=key or "demo-mode-no-key")


def selected_model() -> str:
    settings = get_settings()
    return settings.AI_MODEL.strip() or settings.OPENAI_MODEL
