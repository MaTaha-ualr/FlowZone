# FlowZone Backend v0.2.1 Migration Guide

This guide covers the current production version on `master`.

## What Changed

### Critical Fixes

1. JWT auth and demo mode

- All protected routes use bearer JWT auth in production.
- Demo mode is still available with `APP_DEMO_MODE=true` and `X-User-ID`, but production should keep `APP_DEMO_MODE=false`.

2. Request ID logging

- Request IDs are stored with `contextvars`, avoiding global logging factory races under concurrent load.
- Logs include `request_id`.

3. First-user bootstrap

- `POST /api/v1/users` can create the first user in non-demo mode.
- The frontend should normally use `POST /api/v1/auth/register`.

4. Database timezone compatibility

- Database timestamps stay asyncpg-safe with naive UTC storage where needed.

### Frontend Backend APIs Added

Public:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

Protected:

- `GET /api/v1/profile/me`
- `GET /api/v1/profile/rainbow-circle`
- `GET /api/v1/profile/rewards`
- `POST /api/v1/vibe/check`
- `WS /ws/{session_id}?token=JWT`

### Database Schema Changes

The `users` table now includes:

- `username`
- `password_hash`
- `email`
- `phone`
- `role`

Migration file:

```text
alembic/versions/20260506a001_add_auth_profile_fields.py
```

The migration is idempotent. It can run safely on a fresh database or an existing Railway database.

### Production Startup

The Dockerfile and Procfile now run:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

This keeps existing production databases aligned before the app starts serving traffic.

## Upgrade Steps

1. Back up the current deployment/database.

2. Pull the current production branch:

```bash
git fetch origin
git checkout master
git pull origin master
```

3. Set production environment variables:

```bash
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<32+ random chars>
APP_DEMO_MODE=false
APP_FRONTEND_URL=https://your-frontend-domain.com
CORS_ORIGINS=https://your-frontend-domain.com
DATABASE_URL=<production postgres url>
```

4. Run the database migration if deploying manually:

```bash
alembic upgrade head
```

Railway/Docker deploys run this automatically.

5. Restart the app.

6. Verify:

```bash
curl https://your-api-domain.com/health
curl https://your-api-domain.com/api/v1/profile/me
```

The second command should return `401` without a bearer token.

## Frontend Auth Contract

Register:

```bash
curl -X POST https://your-api-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Marcus","username":"marcus","password":"secure123","age":17,"role":"youth"}'
```

Login:

```bash
curl -X POST https://your-api-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marcus","password":"secure123"}'
```

Authenticated request:

```bash
curl https://your-api-domain.com/api/v1/profile/me \
  -H "Authorization: Bearer <token>"
```

## Rollback

If deployment fails before the migration completes, redeploy the previous commit.

If the migration completed, do not blindly drop the new columns unless you are sure no newly registered accounts depend on them. The added columns are backward-compatible with older rows because `username`, `password_hash`, `email`, and `phone` are nullable, and `role` defaults to `youth`.
