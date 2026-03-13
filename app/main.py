"""
FlowZone — Main Application
==============================
The Trust Engine & Gamification Framework for High-Risk Youth.

This is the entry point. It:
    1. Creates the FastAPI app with metadata
    2. Registers all routers (health, users, sessions, chat, admin)
    3. Adds middleware (CORS, rate limiting)
    4. Sets up startup/shutdown hooks (DB init, connection cleanup)

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Run in Docker:
    docker compose up
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import init_db, close_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.model_router import model_router

# Import all routers
from app.api.routes.health import router as health_router
from app.api.routes.users import router as users_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.chat import router as chat_router
from app.api.routes.admin import router as admin_router
from app.api.routes.voice import router as voice_router
from app.api.routes.mentors import router as mentors_router
from app.api.routes.trust import router as trust_router
from app.api.routes.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic.
    - On startup: create database tables (MVP approach — Alembic for production)
    - On shutdown: close database connections gracefully
    """
    # ---- Startup ----
    print("=" * 60)
    print(f"  FlowZone starting up ({settings.app_env.value})")
    print(f"  Database: {settings.database_url[:30]}...")
    print("=" * 60)

    # Import all models so Base.metadata knows about them
    import app.models  # noqa: F401

    await init_db()
    print("  Database tables created/verified.")

    # Check which LLM providers are configured
    try:
        provider_status = await model_router.check_all_providers()
        for provider, status in provider_status.items():
            icon = "✓" if status == "available" else "✗" if status == "no_api_key" else "⚠"
            print(f"  {icon} {provider}: {status}")
    except Exception as e:
        print(f"  ⚠ Provider health check skipped: {e}")

    print("  FlowZone is ready.")
    print("=" * 60)

    yield

    # ---- Shutdown ----
    print("FlowZone shutting down...")
    await model_router.close_all()
    await close_db()
    print("All connections closed. Goodbye.")


# ---- Create App ----
app = FastAPI(
    title="FlowZone API",
    description=(
        "The Trust Engine & Gamification Framework. "
        "Multi-model AI chatbot for high-risk youth with adaptive characters, "
        "voice input, RAG, and gamified trust scoring."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
    openapi_url="/openapi.json",
)


# ---- Middleware ----

# CORS — allow frontend to connect from any origin in dev
# Lock this down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_debug else ["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting on chat endpoints
app.add_middleware(RateLimitMiddleware)


# ---- Register Routers ----
app.include_router(health_router)
app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(mentors_router)
app.include_router(documents_router)
app.include_router(trust_router)
app.include_router(admin_router)


# ---- Root Redirect ----
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return {
        "service": "FlowZone API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
