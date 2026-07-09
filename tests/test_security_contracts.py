"""Security and production-gate contract tests."""

import pytest

from app.core.config import Environment, settings, validate_runtime_security_settings


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(real_auth_client, username: str, role: str = "youth") -> dict:
    response = await real_auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": f"{role.title()} User",
            "username": username,
            "password": "secure123",
            "age": 17 if role == "youth" else 32,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_admin_routes_require_admin_role(real_auth_client):
    youth = await _register(real_auth_client, "not_admin", "youth")
    admin = await _register(real_auth_client, "real_admin", "admin")

    youth_response = await real_auth_client.get(
        "/api/v1/admin/models",
        headers=_auth_headers(youth["access_token"]),
    )
    assert youth_response.status_code == 403

    admin_response = await real_auth_client.get(
        "/api/v1/admin/models",
        headers=_auth_headers(admin["access_token"]),
    )
    assert admin_response.status_code == 200, admin_response.text


def test_production_demo_mode_fails_runtime_validation():
    original_env = settings.app_env
    original_demo = settings.app_demo_mode
    original_secret = settings.app_secret_key
    original_cors = settings.cors_origins
    try:
        settings.app_env = Environment.PRODUCTION
        settings.app_demo_mode = True
        settings.app_secret_key = "change-me-in-production"
        settings.cors_origins = "*"
        with pytest.raises(RuntimeError) as exc:
            validate_runtime_security_settings()
        message = str(exc.value)
        assert "APP_DEMO_MODE" in message
        assert "APP_SECRET_KEY" in message
        assert "CORS_ORIGINS" in message
    finally:
        settings.app_env = original_env
        settings.app_demo_mode = original_demo
        settings.app_secret_key = original_secret
        settings.cors_origins = original_cors


@pytest.mark.asyncio
async def test_document_upload_rejects_unsupported_extension(real_auth_client):
    registered = await _register(real_auth_client, "upload_user", "youth")
    user_id = registered["user"]["id"]
    response = await real_auth_client.post(
        f"/api/v1/documents/upload?user_id={user_id}&document_type=uploaded",
        headers=_auth_headers(registered["access_token"]),
        files={"file": ("malware.exe", b"nope", "application/octet-stream")},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_document_upload_rejects_oversized_file(real_auth_client):
    registered = await _register(real_auth_client, "big_upload_user", "youth")
    user_id = registered["user"]["id"]
    original_limit = settings.document_max_upload_bytes
    settings.document_max_upload_bytes = 4
    try:
        response = await real_auth_client.post(
            f"/api/v1/documents/upload?user_id={user_id}&document_type=uploaded",
            headers=_auth_headers(registered["access_token"]),
            files={"file": ("note.txt", b"too large", "text/plain")},
        )
    finally:
        settings.document_max_upload_bytes = original_limit
    assert response.status_code == 413
