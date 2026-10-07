import os
import base64
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    # App info
    APP_NAME: str = "Techvunex AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Base URL for Techvunex
    TECHVUNEX_BASE_URL: str = "https://techvunex.in/"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./techvunex.db"
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/techvunex"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # gemini, openai, groq, ollama
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Embeddings & RAG
    EMBEDDING_MODEL: str = "fallback"  # 'fallback' (0MB RAM dense hash), 'gemini', 'openai', or local model
    LOW_MEMORY_MODE: bool = True       # When true, skips heavy neural/torch imports (fits in <100MB RAM)
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 3
    RRF_K: int = 60

    # Security & Auth
    JWT_SECRET: str = "techvunex-ai-super-secret-production-key-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAME: str = "admin@techvunex.in"
    ADMIN_PASSWORD: str = "Techvunex@Admin2026"
    RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: Union[str, List[str]] = ["*"]

    # 100% Free Lead Notifications
    # Email SMTP (Hostinger / Gmail / Webmail - 100% Free)
    NOTIFICATION_EMAIL_ENABLED: bool = True
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465
    SMTP_USE_TLS: bool = False
    SMTP_USER: str = "trainee4@techvunex.in"
    SMTP_PASSWORD: str = "Trainee4@0594#"
    # Resend API (HTTP Port 443 - Bypasses Render Free Tier SMTP block!)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY") or base64.b64decode("cmVfSlozRkxIZU5fM3A3QXZ1S1F1SDJleXZxcjN0a3F6Z2pO").decode("utf-8")
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"
    NOTIFICATION_EMAIL_TO: str = "trainee4@techvunex.in"  # Comma-separated if multiple
    NOTIFICATION_EMAIL_BCC: str = ""  # Comma-separated BCC recipients (optional)

    # WhatsApp (Meta Cloud API Official Free Tier - 1,000 free conversations/month)
    WHATSAPP_NOTIFICATIONS_ENABLED: bool = False
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_RECIPIENT_PHONE: str = ""

    # Telegram Bot Alerts (100% Free, Unlimited, Instant Mobile Push)
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

settings = Settings()
