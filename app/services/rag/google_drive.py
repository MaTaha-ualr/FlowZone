"""
Google Drive Integration Helpers
================================

Thin abstraction around Google Drive OAuth + file fetching.
For MVP, this exposes function signatures used by the documents routes.
If Google credentials are not configured, functions raise descriptive errors.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings


class GoogleDriveNotConfigured(Exception):
    pass


def _ensure_configured() -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleDriveNotConfigured(
            "Google Drive OAuth is not configured. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        )


def get_oauth_authorization_url(state: str) -> str:
    """
    Build an authorization URL for the user to connect Google Drive.
    In a full implementation, this would use google_auth_oauthlib.flow.
    """
    _ensure_configured()
    # For now, return a placeholder URL so the endpoint can respond gracefully.
    return settings.google_redirect_uri + f"?state={state}"


def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """
    Exchange an OAuth code for access/refresh tokens.
    This is intentionally left as a stub — production deployment should
    implement the full OAuth flow using google-auth-oauthlib.
    """
    _ensure_configured()
    # Placeholder: in real code, perform token exchange.
    return {"access_token": "dummy", "refresh_token": "dummy", "expires_in": 3600}


def list_drive_files_for_user(user_tokens: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    List candidate files from a user's Drive that FlowZone can ingest.
    """
    _ensure_configured()
    # Placeholder implementation; real version would call Drive API.
    return []


def fetch_file_bytes(user_tokens: Dict[str, Any], file_id: str) -> bytes:
    """
    Fetch raw bytes for a given file ID from Google Drive.
    """
    _ensure_configured()
    # Placeholder implementation; real version would download from Drive.
    raise GoogleDriveNotConfigured(
        "Google Drive download is not implemented in this environment."
    )

