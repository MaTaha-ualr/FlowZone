# FlowZone — The Trust Engine & Gamification Framework

Multi-model AI chatbot for high-risk youth with adaptive characters, voice input, RAG, and gamified trust scoring.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Web App)                    │
│            Voice Input │ Text Chat │ Vibe Selector        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐             │
│  │ Session   │  │ Rate     │  │ Concurrency│             │
│  │ Manager   │  │ Limiter  │  │ Guard (5)  │             │
│  └─────┬────┘  └──────────┘  └───────────┘             │
│        │                                                 │
│        ▼                                                 │
│  ┌─────────────────────────────────────┐                │
│  │          Model Router               │                │
│  │  ┌───────┐ ┌────────┐ ┌──────┐    │                │
│  │  │Budget │ │Provider│ │Fallback│    │                │
│  │  │Check  │ │Select  │ │Chain  │    │                │
│  │  └───────┘ └────────┘ └──────┘    │                │
│  └──────────────┬──────────────────────┘                │
│                 │                                        │
│     ┌───────┬──┴──┬────────┬────────┐                  │
│     ▼       ▼     ▼        ▼        ▼                  │
│  Claude  GPT-4o  Gemini   Llama   Whisper              │
│  (Paid)  (Cheap) (Free)   (Free)  (STT)               │
│                                                          │
│  ┌──────────────┐  ┌────────────┐  ┌──────────┐       │
│  │ RAG Pipeline  │  │Trust Engine│  │ Safe     │       │
│  │ ChromaDB +    │  │ Shield     │  │ Harbor   │       │
│  │ Google Drive  │  │ Formula    │  │ Protocol │       │
│  └──────────────┘  └────────────┘  └──────────┘       │
│                                                          │
│                  ┌──────────┐                            │
│                  │PostgreSQL│                            │
│                  └──────────┘                            │
└─────────────────────────────────────────────────────────┘
```

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone and configure
```bash
git clone <your-repo-url>
cd flowzone
cp .env.example .env
# Edit .env — add your API keys (at minimum, GROQ_API_KEY for free-tier models)
```

### 2. Start the stack
```bash
docker compose up
```

This starts:
- **PostgreSQL** on port 5432
- **FlowZone API** on port 8000

### 3. Verify it works
```bash
# Health check
curl http://localhost:8000/health

# Swagger docs
open http://localhost:8000/docs
```

### 4. Seed test data (Marcus Cole)
```bash
docker compose exec app python -m scripts.seed_data
```

### 5. Test the API flow
```bash
# List users
curl http://localhost:8000/api/v1/users

# Start a session for Marcus
curl -X POST http://localhost:8000/api/v1/sessions/<marcus_user_id>

# Send a message
curl -X POST http://localhost:8000/api/v1/chat/<session_id> \
  -H "Content-Type: application/json" \
  -d '{"content": "Yeah I'\''m good. School was whatever.", "vibe": "solid"}'

# Check budget
curl http://localhost:8000/api/v1/admin/budget
```

## Deploy to Railway

### 1. Create Railway project
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init
railway login
railway init
```

### 2. Add PostgreSQL
```bash
railway add --plugin postgresql
```

### 3. Set environment variables
```bash
railway variables set APP_ENV=production
railway variables set APP_DEBUG=false
railway variables set APP_SECRET_KEY=$(openssl rand -hex 32)
# Add your API keys
railway variables set GROQ_API_KEY=gsk_...
```

### 4. Deploy
```bash
railway up
```

Railway auto-detects the Dockerfile, builds, and deploys. The DATABASE_URL is automatically set by the PostgreSQL plugin.

## Project Structure

```
flowzone/
├── app/
│   ├── api/routes/          # API endpoints
│   │   ├── health.py        # GET /health
│   │   ├── users.py         # CRUD + intake
│   │   ├── sessions.py      # Session management
│   │   ├── chat.py          # Core chat endpoint
│   │   └── admin.py         # Budget monitoring
│   ├── core/
│   │   ├── config.py        # All settings (pydantic-settings)
│   │   ├── constants.py     # Characters, models, scoring rules
│   │   └── safe_harbor.py   # Safety protocol logic
│   ├── middleware/
│   │   └── rate_limit.py    # Rate limiting + concurrency guard
│   ├── models/              # SQLAlchemy database models
│   │   ├── user.py          # Youth profiles
│   │   ├── session.py       # FlowQuest sessions
│   │   ├── message.py       # Chat messages
│   │   ├── trust_score.py   # Shield Formula scores
│   │   ├── mentor_note.py   # Mentor observations
│   │   ├── school_data.py   # Academic data
│   │   ├── document_ref.py  # Google Drive doc references
│   │   ├── api_usage.py     # Credit tracking
│   │   ├── vouch.py         # Gamification vouches
│   │   └── pattern.py       # Cross-user patterns
│   ├── schemas/
│   │   └── api.py           # Pydantic request/response models
│   ├── services/            # Business logic (next phase)
│   │   ├── model_router/    # LLM routing + fallbacks
│   │   ├── characters/      # Character system prompts
│   │   ├── voice/           # STT + TTS pipelines
│   │   ├── rag/             # RAG pipeline + ChromaDB
│   │   └── trust_engine/    # Score calculation + Truth Engine
│   ├── database.py          # Async SQLAlchemy setup
│   └── main.py              # FastAPI app entry point
├── scripts/
│   └── seed_data.py         # Load test data
├── tests/
├── docker-compose.yml       # Local dev stack
├── Dockerfile               # Production container
├── railway.json             # Railway deployment config
├── requirements.txt
└── .env.example
```

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | FastAPI | Async-native, auto-docs, Python ecosystem |
| Database | PostgreSQL (async) | RLS for privacy, JSON columns, production-ready |
| ORM | SQLAlchemy 2.0 async | Type-safe, migration support via Alembic |
| Vector DB | ChromaDB (embedded) | No separate server, Python-native, perfect for <10K vectors |
| Model Router | Custom (in-app) | Tight budget control, character-specific routing, fallback chains |
| Session Management | DB-backed | Resumable across days, no Redis dependency for MVP |
| Auth | Placeholder | JWT planned for production, skipped for MVP speed |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Full subsystem status |
| POST | `/api/v1/users` | Create user |
| GET | `/api/v1/users` | List users |
| GET | `/api/v1/users/{id}` | Get user |
| POST | `/api/v1/users/{id}/intake` | Submit Strategic Intake |
| POST | `/api/v1/sessions/{user_id}` | Start/resume session |
| GET | `/api/v1/sessions/{user_id}/current` | Get active session |
| POST | `/api/v1/chat/{session_id}` | Send message |
| GET | `/api/v1/chat/{session_id}/history` | Get chat history |
| GET | `/api/v1/admin/budget` | Budget status |
| GET | `/api/v1/admin/models` | Model availability |

## Next Steps (Build Order)

1. **Model Router** — Connect actual LLM APIs with fallback chains
2. **Character System Prompts** — Craft prompts for Challenger, Navigator, Straight Shooter, Strategist
3. **Voice Pipeline** — Groq Whisper STT + Edge TTS
4. **RAG Pipeline** — ChromaDB + document ingestion + Google Drive OAuth
5. **Trust Engine** — Live score calculation + mask detection
6. **Mentor Dashboard** — Note submission + sanitization
7. **Gamification** — Vouches, tiers, decay
