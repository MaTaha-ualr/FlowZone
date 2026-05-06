# FlowZone Backend

FlowZone is a FastAPI backend for the Trust Engine and gamified youth support workflow. It provides username/password auth, JWT-protected chat sessions, adaptive character routing, vibe checks, voice endpoints, RAG/document support, trust scoring, rewards, and mentor/admin views.

Current API version: `0.2.1`

Canonical production branch: `master`

`main` is kept in sync for visibility, but GitHub reports `master` as the repository HEAD/default branch.

## Production Status

The current production-ready commit includes:

- Real username/password auth with bearer JWTs.
- `role` support for `youth` and `mentor`.
- Dashboard profile endpoints for streak, score, tier, character, and Safe Harbor status.
- Rainbow Circle and rewards endpoints for the menu drawer.
- Vibe check endpoint that updates session vibe, character, and Safe Harbor level.
- WebSocket chat endpoint at `/ws/{session_id}?token=JWT`.
- Request ID logging, rate limiting, and demo-mode bypass for controlled pilot testing.
- Alembic migration for the new auth/profile user fields.

The Docker and Procfile startup commands run `alembic upgrade head` before starting Uvicorn. The migration is idempotent so it is safe for both fresh databases and existing Railway databases.

## Quick Start

### Prerequisites

- Python 3.12 or Docker
- PostgreSQL for normal local development
- At least one model provider key. `GROQ_API_KEY` is the easiest free-tier starting point.

### Local With Docker

```bash
git clone https://github.com/MaTaha-ualr/FlowZone.git
cd FlowZone
cp .env.example .env
docker compose up --build
```

Open:

- Health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### Local Python

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Required Environment

Minimum production variables:

```bash
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<32+ random chars>
APP_DEMO_MODE=false
CORS_ORIGINS=https://your-frontend-domain.com
DATABASE_URL=<Railway/Postgres URL>
GROQ_API_KEY=<optional but recommended>
```

Important notes:

- `DATABASE_URL` may be `postgres://`, `postgresql://`, or `postgresql+asyncpg://`; the app normalizes it.
- `APP_DEMO_MODE=false` is the correct production setting.
- Use `APP_DEMO_MODE=true` only for controlled pilots where `X-User-ID` bypass auth is acceptable.
- `CORS_ORIGINS=*` is for development only.

## Railway Deployment

This repository includes:

- `Dockerfile`
- `railway.json`
- `Procfile`

Railway should deploy from `master`.

Startup runs:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

Railway health check:

```text
/health
```

Recommended Railway variables:

```bash
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<generated secret>
APP_DEMO_MODE=false
APP_FRONTEND_URL=https://your-frontend-domain.com
CORS_ORIGINS=https://your-frontend-domain.com
GROQ_API_KEY=<key>
DATABASE_URL=<set by Railway PostgreSQL plugin>
```

## Auth Flow

Register:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marcus Johnson",
    "username": "marcus_j",
    "password": "secure123",
    "email": "marcus@example.com",
    "phone": "501-555-0100",
    "age": 17,
    "role": "youth",
    "school_name": "Central High",
    "city": "Little Rock",
    "state": "AR",
    "has_probation": false,
    "has_case_worker": true
  }'
```

Login:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "marcus_j", "password": "secure123"}'
```

Use the returned token:

```bash
curl http://localhost:8000/api/v1/profile/me \
  -H "Authorization: Bearer <token>"
```

## Frontend Endpoints

Public:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Basic health check |
| `GET` | `/health/detailed` | Subsystem health |
| `POST` | `/api/v1/auth/register` | Create account and return JWT |
| `POST` | `/api/v1/auth/login` | Login and return JWT |

Protected:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/profile/me` | Dashboard/profile data |
| `GET` | `/api/v1/profile/rainbow-circle` | Tier visualization data |
| `GET` | `/api/v1/profile/rewards` | Reward/vouch store data |
| `POST` | `/api/v1/vibe/check` | Set vibe and character state |
| `POST` | `/api/v1/sessions/{user_id}` | Start or resume a session |
| `GET` | `/api/v1/sessions/{user_id}/current` | Get active session |
| `POST` | `/api/v1/chat/{session_id}` | Send chat message |
| `GET` | `/api/v1/chat/{session_id}/history` | Read chat history |
| `GET` | `/api/v1/chat/{session_id}/stream` | SSE chat stream |
| `WS` | `/ws/{session_id}?token=JWT` | WebSocket chat |
| `POST` | `/api/v1/voice/transcribe` | Speech to text |
| `POST` | `/api/v1/voice/synthesize` | Text to speech |
| `GET` | `/api/v1/trust/{user_id}` | Trust score detail |
| `POST` | `/api/v1/trust/{user_id}/vouch` | Redeem a reward |
| `GET` | `/api/v1/mentors/dashboard/{user_id}` | Mentor dashboard |

## Vibe Check Example

```bash
curl -X POST http://localhost:8000/api/v1/vibe/check \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_uuid>",
    "vibe": "angry",
    "notes": "Got in a fight at school"
  }'
```

Response includes:

```json
{
  "vibe": "angry",
  "character_assigned": "challenger",
  "character_name": "Vex",
  "safe_harbor_level": "yellow"
}
```

## Trust Tiers

The backend currently has three canonical trust tiers:

| Key | Display Name | Threshold |
| --- | --- | --- |
| `the_watch` | The Watch | `0` |
| `the_flex` | The Flex | `200` |
| `the_vetted` | The Vetted | `500` |

The frontend plan referenced five display tiers. This backend intentionally preserves the existing trust engine thresholds and exposes display metadata for the three canonical tiers.

## Tests

Run the full suite:

```bash
.\.venv\Scripts\python.exe -m pytest
```

Current verified result on the production commit:

```text
130 passed
```

## Project Layout

```text
app/
  api/routes/       FastAPI routers
  core/             config, security, constants, safety
  middleware/       request IDs, rate limiting
  models/           SQLAlchemy models
  schemas/          Pydantic request/response models
  services/         model routing, trust engine, RAG, voice
alembic/            database migrations
scripts/            seed and ingestion helpers
tests/              pytest suite
```
