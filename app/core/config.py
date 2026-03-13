"""
FlowZone Application Configuration
====================================
Uses pydantic-settings to load and validate all environment variables.
Every configurable aspect of the system is centralized here.

Architecture Note:
    This is the SINGLE SOURCE OF TRUTH for all configuration.
    No other file should read environment variables directly.
    Import `settings` from this module everywhere.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class STTProvider(str, Enum):
    BROWSER = "browser"         # Web Speech API — zero backend cost
    GROQ_WHISPER = "groq_whisper"  # Groq-hosted Whisper — free tier, fast
    DEEPGRAM = "deepgram"       # Deepgram — paid, production quality


class TTSProvider(str, Enum):
    EDGE_TTS = "edge_tts"  # Microsoft Edge TTS — free, good quality
    NONE = "none"           # Text-only responses


class Settings(BaseSettings):
    """
    All FlowZone settings. Loaded from environment variables / .env file.
    Grouped by subsystem for clarity.
    """

    # ---- Application Core ----
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ---- Database ----
    # Use Field so env var DATABASE_URL cleanly overrides the default.
    database_url: str = Field(
        default="postgresql+asyncpg://flowzone:flowzone_dev@db:5432/flowzone"
    )

    # ---- LLM API Keys ----
    # Paid providers (used strategically by the Model Router)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    # Free-tier providers
    google_ai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # ---- Model Router (Credit Management) ----
    daily_budget_cap_usd: float = 3.00
    budget_tier_green: float = 0.60    # Under 60% = all models available
    budget_tier_yellow: float = 0.85   # 60-85% = downgrade Strategist to free
    # Above 85% = everything on free models

    # ---- Voice Pipeline ----
    stt_provider: STTProvider = STTProvider.GROQ_WHISPER
    tts_provider: TTSProvider = TTSProvider.EDGE_TTS

    # ---- RAG ----
    chroma_persist_dir: str = "/app/data/chromadb"
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_enabled: bool = True

    # ---- Google Drive OAuth ----
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    google_oauth_scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ]
    )

    # ---- Session Management ----
    session_history_window: int = 8      # Last N messages kept in full
    session_timeout_hours: int = 8       # Inactivity before new session
    max_concurrent_users: int = 5

    # ---- Safe Harbor ----
    safe_harbor_trauma_floor: str = "yellow"

    # ---- Rate Limiting ----
    user_rate_limit_per_minute: int = 10

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @model_validator(mode="after")
    def fix_database_url(self) -> "Settings":
        """
        Railway sets DATABASE_URL as postgresql:// but asyncpg needs
        postgresql+asyncpg://. Auto-convert at startup.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            self.database_url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            self.database_url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


# Singleton instance — import this everywhere
settings = Settings()
