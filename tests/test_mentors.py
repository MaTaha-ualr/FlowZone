"""Tests for mentor note submission and dashboard."""
import pytest
from unittest.mock import patch, AsyncMock
from app.middleware.rate_limit import concurrency_guard


@pytest.fixture(autouse=True)
async def reset():
    concurrency_guard._active_users.clear()
    yield
    concurrency_guard._active_users.clear()


async def _make_user(client):
    c = await client.post("/api/v1/users", json={"name": "Mentor Test", "age": 15, "user_type": "juvenile_justice"})
    return c.json()["id"]


@pytest.mark.asyncio
async def test_submit_note(client):
    uid = await _make_user(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Sanitized content."
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach Ray",
            "note_type": "observation", "content": "Raw note content.",
        })
        assert r.status_code == 201
        assert r.json()["mentor_name"] == "Coach Ray"
        m.assert_called_once()


@pytest.mark.asyncio
async def test_submit_vouch(client):
    uid = await _make_user(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Vouch."
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "vouch", "content": "Showed up.", "vouch_points": 15,
        })
        assert r.status_code == 201
        assert r.json()["vouch_points"] == 15


@pytest.mark.asyncio
async def test_get_notes(client):
    uid = await _make_user(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Clean."
        await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "observation", "content": "Raw.",
        })
    r = await client.get(f"/api/v1/mentors/notes/{uid}")
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_dashboard(client):
    uid = await _make_user(client)
    r = await client.get(f"/api/v1/mentors/dashboard/{uid}")
    assert r.status_code == 200
    assert "user" in r.json()
    assert "trust_score_trend" in r.json()


@pytest.mark.asyncio
async def test_note_nonexistent_user(client):
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock):
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "observation", "content": "Test.",
        })
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_risk_flag_red(client):
    uid = await _make_user(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Flagged."
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "risk_flag", "content": "Concerning.",
            "risk_flag_level": "red",
        })
        assert r.status_code == 201
        assert r.json()["risk_flag_level"] == "red"
