# FlowZone Backend v0.2.0 — Migration Guide

## What Changed

### 🔴 Critical Fixes

#### 1. Authentication (NEW)
- **File:** `app/core/security.py`
- **What:** JWT token auth + demo mode bypass
- **Impact:** All routes now require auth. For pilot testing, set `APP_DEMO_MODE=true` and pass `X-User-ID` header.
- **Frontend change:** Send `Authorization: Bearer <token>` header, or `X-User-ID: <uuid>` in demo mode.

#### 2. Trust Score Math (FIXED)
- **File:** `app/services/trust_engine/calculator.py`
- **What:** Removed `T` (days_active) from the daily contribution denominator. The old formula `((C × W) + H + R + M - P) / T` incorrectly penalized long-tenure users.
- **New formula:** `daily_contribution = (C × W) + H + R + M - P` (cumulative, no division)
- **Display:** A soft cosmetic normalization is available: `display_score = raw_score / (1 + 0.002 * days_active)`
- **Impact:** Existing users' scores will recalculate correctly on next session.

#### 3. Background Tasks (FIXED)
- **File:** `app/api/routes/chat.py`
- **What:** Mask detection, session extraction, trust recalc, and summarization now run in `BackgroundTasks`.
- **Impact:** Chat response latency drops by 500ms–2s. The AI response returns immediately; analytics fire after.

#### 4. Database Transactions (FIXED)
- **File:** `app/database.py`
- **What:** `get_db()` no longer auto-commits. Routes must call `await db.commit()` explicitly.
- **Impact:** Prevents partial commits when background tasks fail. Chat messages are committed before analytics run.

#### 5. Streaming Fallback (FIXED)
- **File:** `app/api/routes/chat.py`
- **What:** SSE streaming now has error handling. If the stream fails, the client gets `[ERROR]` instead of a hung connection.
- **Impact:** Frontend should handle `data: [ERROR]` events gracefully.

### 🟡 Important Additions

#### 6. WebSocket Endpoint (NEW)
- **File:** `app/api/routes/ws.py`
- **What:** Real-time bidirectional chat at `/ws/{session_id}?token=JWT`
- **Protocol:**
  - Client sends: `{"type": "message", "content": "...", "vibe": "solid"}`
  - Server sends: `{"type": "chunk", "content": "..."}` → `{"type": "done", ...}`
- **Impact:** Frontend can now use WebSockets for chat instead of REST polling.

#### 7. Request ID Tracing (NEW)
- **File:** `app/middleware/request_id.py`
- **What:** Every request gets a `X-Request-ID` header. Logs include it.
- **Impact:** Essential for debugging youth safety issues. Mentors can ask "What did the AI say at 3:15 PM?" and you can grep by request_id.

#### 8. Input Sanitization (NEW)
- **File:** `app/core/sanitize.py`
- **What:** PII detection, prompt injection scanning, extreme language flagging.
- **Impact:** Messages are scanned before storage. Flags are logged for mentor review.

#### 9. Session Summarization (NEW)
- **File:** `app/services/session_summarizer.py`
- **What:** Background task summarizes conversation every 10 messages to keep token window efficient.
- **Impact:** Long conversations stay within context limits without losing history.

#### 10. Pagination (NEW)
- **Files:** `app/api/routes/users.py`, `sessions.py`
- **What:** `limit` and `offset` query params on list endpoints.
- **Impact:** Frontend must update list calls to use pagination.

#### 11. Structured Logging (NEW)
- **File:** `app/core/logging_config.py`
- **What:** JSON-formatted logs with timestamps, levels, request_id, user_id.
- **Impact:** Railway/Datadog can parse logs automatically.

#### 12. CORS Configuration (FIXED)
- **File:** `app/core/config.py`
- **What:** `CORS_ORIGINS` env var replaces hardcoded `https://your-frontend-domain.com`.
- **Impact:** Set `CORS_ORIGINS=https://your-domain.com` in production.

### 🟢 Minor Fixes

#### 13. Detailed Health Check (FIXED)
- **File:** `app/api/routes/health.py`
- **What:** `/health/detailed` now shows real budget data, ChromaDB status, and provider health.

#### 14. Auth on All Routes (FIXED)
- **Files:** All route files
- **What:** Every endpoint now uses `get_current_user`. Users can only access their own data.
- **Impact:** No more spoofing `X-User-ID` in production.

---

## Upgrade Steps

### Step 1: Backup
```bash
cp -r flowzone flowzone-backup-v0.1.0
```

### Step 2: Copy New Files
Copy all files from this zip into your repo, overwriting existing ones:
```bash
# From the extracted zip
cp -r app/ your-repo/app/
cp .env.example your-repo/.env.example
```

### Step 3: Update .env
Add the new variables to your `.env`:
```bash
APP_DEMO_MODE=false
APP_FRONTEND_URL=https://your-frontend-domain.com
CORS_ORIGINS=https://your-frontend-domain.com
```

For **pilot testing** without auth:
```bash
APP_DEMO_MODE=true
CORS_ORIGINS=*
```

### Step 4: Regenerate Secret Key
```bash
openssl rand -hex 32
# Paste into .env as APP_SECRET_KEY
```

### Step 5: Database
No schema changes required for v0.2.0. The existing tables work as-is.

### Step 6: Restart
```bash
docker compose down
docker compose up --build
```

### Step 7: Verify
```bash
# Health check
curl http://localhost:8000/health

# Auth check (should 401 without token)
curl http://localhost:8000/api/v1/users

# Demo mode check
curl -H "X-User-ID: <marcus-uuid>" http://localhost:8000/api/v1/users
```

---

## Frontend Changes Required

### Authentication
**Before:** No auth headers.
**After (Demo):** `X-User-ID: <user-uuid>`
**After (Production):** `Authorization: Bearer <jwt-token>`

### WebSocket (Optional)
```javascript
const ws = new WebSocket(
  `wss://api.flowzone.org/ws/${sessionId}?token=${jwtToken}`
);
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === "chunk") appendText(data.content);
  if (data.type === "done") finalizeMessage(data);
};
```

### Pagination
```javascript
// Users list
fetch(`/api/v1/users?limit=20&offset=0`)

// Sessions list
fetch(`/api/v1/sessions/${userId}?limit=10&offset=0`)
```

---

## API Contract Changes

| Endpoint | Change |
|----------|--------|
| `POST /api/v1/users` | Now requires auth |
| `GET /api/v1/users` | Added `limit`, `offset` params |
| `POST /api/v1/chat/{id}` | Returns faster (background analytics) |
| `GET /api/v1/chat/{id}/stream` | Now requires auth |
| `WS /ws/{session_id}` | **NEW** — WebSocket chat |
| `GET /health/detailed` | Now shows real budget + ChromaDB status |
| All routes | Require `Authorization` or `X-User-ID` (demo) |

---

## Rollback Plan

If something breaks:
1. `git checkout v0.1.0` (or restore backup)
2. `docker compose down && docker compose up`
3. The database schema is unchanged, so data is safe.

---

## Questions?

Check the logs with:
```bash
docker compose logs -f app | jq .
```
(Logs are JSON, so `jq` formats them beautifully.)
