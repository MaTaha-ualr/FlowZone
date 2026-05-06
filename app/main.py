"""
FlowZone — Main Application (FIXED)
====================================
Changes from original:
  - Structured JSON logging on startup
  - RequestIDMiddleware added
  - CORS uses configurable origins (not hardcoded placeholder)
  - WebSocket router registered
  - Auth dependencies wired to all routes
  - Demo mode support
  - Graceful shutdown with connection cleanup
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database import init_db, close_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.services.model_router import model_router

# Import all routers
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.chat import router as chat_router
from app.api.routes.voice import router as voice_router
from app.api.routes.mentors import router as mentors_router
from app.api.routes.documents import router as documents_router
from app.api.routes.trust import router as trust_router
from app.api.routes.profile import router as profile_router
from app.api.routes.vibe import router as vibe_router
from app.api.routes.admin import router as admin_router
from app.api.routes.ws import router as ws_router

# Setup structured logging immediately
setup_logging(level=logging.DEBUG if settings.app_debug else logging.INFO)
logger = logging.getLogger(__name__)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
RESERVED_FRONTEND_PREFIXES = (
    "api/",
    "docs",
    "redoc",
    "openapi.json",
    "health",
    "ws/",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # ---- Startup ----
    logger.info("FlowZone starting up", extra={
        "environment": settings.app_env.value,
        "demo_mode": settings.app_demo_mode,
        "frontend_url": settings.app_frontend_url,
    })

    # Import all models so Base.metadata knows about them
    import app.models  # noqa: F401

    await init_db()
    logger.info("Database tables created/verified")

    # Check LLM providers
    try:
        provider_status = await model_router.check_all_providers()
        for provider, status in provider_status.items():
            icon = "✓" if status == "available" else "✗" if status == "no_api_key" else "⚠"
            logger.info(f"Provider {provider}: {status}")
    except Exception as e:
        logger.warning(f"Provider health check skipped: {e}")

    logger.info("FlowZone is ready")
    yield

    # ---- Shutdown ----
    logger.info("FlowZone shutting down...")
    await model_router.close_all()
    await close_db()
    logger.info("All connections closed. Goodbye.")

# ---- Create App ----
app = FastAPI(
    title="FlowZone API",
    description=(
        "The Trust Engine & Gamification Framework. "
        "Multi-model AI chatbot for high-risk youth with adaptive characters, "
        "voice input, RAG, and gamified trust scoring."
    ),
    version="0.2.1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---- Middleware (ORDER MATTERS) ----
# 1. Request ID first (so all downstream logs have request_id)
app.add_middleware(RequestIDMiddleware)

# 2. CORS
origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate limiting
app.add_middleware(RateLimitMiddleware)

# ---- Register Routers ----
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(mentors_router)
app.include_router(documents_router)
app.include_router(trust_router)
app.include_router(profile_router)
app.include_router(vibe_router)
app.include_router(admin_router)
app.include_router(ws_router)  # NEW: WebSocket

# ---- Frontend static app ----
if (FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="frontend-assets",
    )

@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend when built; otherwise expose API metadata."""
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX)
    return {
        "service": "FlowZone API",
        "version": "0.2.1",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/{session_id}?token=JWT",
    }

@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_spa(full_path: str):
    """Serve Vite files and SPA fallback without masking backend routes."""
    if full_path.startswith(RESERVED_FRONTEND_PREFIXES):
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_INDEX.is_file():
        candidate = (FRONTEND_DIST / full_path).resolve()
        dist_root = FRONTEND_DIST.resolve()
        if str(candidate).startswith(str(dist_root)) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX)

    raise HTTPException(status_code=404, detail="Frontend build not found")
