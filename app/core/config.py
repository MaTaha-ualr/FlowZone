"""
FlowZone Application Configuration (UPDATED)
============================================
Changes from original:
  - Added APP_DEMO_MODE for pilot testing without auth
  - Added CORS_ORIGINS (comma-separated) for production safety
  - Added APP_FRONTEND_URL for redirects
"""

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from typing import Optional, List
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class STTProvider(str, Enum):
    BROWSER = "browser"
    GROQ_WHISPER = "groq_whisper"
    DEEPGRAM = "deepgram"

class TTSProvider(str, Enum):
    EDGE_TTS = "edge_tts"
    NONE = "none"

class Settings(BaseSettings):
    # ---- Application Core ----
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_demo_mode: bool = False  # NEW: bypass auth for pilot testing
    app_frontend_url: str = "http://localhost:3000"  # NEW: for CORS + redirects

    # ---- CORS ----
    # Comma-separated list of allowed origins, e.g.:
    # CORS_ORIGINS=https://app.flowzone.org,https://admin.flowzone.org
    cors_origins: str = "*"  # NEW

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://flowzone:flowzone_dev@db:5432/flowzone"
    )

    # ---- LLM API Keys ----
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # ---- Model Router (Credit Management) ----
    daily_budget_cap_usd: float = 3.00
    budget_tier_green: float = 0.60
    budget_tier_yellow: float = 0.85

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
    google_redirect_uri: str = "http://localhost:8000/api/v1/documents/google-drive/callback"
    google_oauth_scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ]
    )

    # ---- Session Management ----
    session_history_window: int = 8
    session_timeout_hours: int = 8
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
        url = self.database_url
        if url.startswith("postgres://"):
            self.database_url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            self.database_url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS env var into a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

# Singleton
settings = Settings()
